import json
import sys
from datetime import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BERLIN = "Europe/Berlin"


def main(readings_csv: Path, tariff_json: Path) -> None:
    tariff = json.loads(tariff_json.read_text())
    day_ct = tariff["day"]["ct_per_kwh"]
    night_ct = tariff["night"]["ct_per_kwh"]
    fee = tariff["monthly_fee_eur"]
    day_from = time.fromisoformat(tariff["day"]["from"])
    day_to = time.fromisoformat(tariff["day"]["to"])

    rows = pd.read_csv(readings_csv, parse_dates=["timestamp"])
    first_of_its_local_time = ~rows.duplicated("timestamp", keep="first")
    rows["start"] = (
        rows["timestamp"]
        .dt.tz_localize(BERLIN, ambiguous=first_of_its_local_time.to_numpy())
        .dt.tz_convert("UTC")
    )
    measured_wh = rows.drop_duplicates("start", keep="last").set_index("start")["energy_wh"]

    month_start = pd.DatetimeIndex(measured_wh.index).tz_convert(BERLIN)[0].normalize()
    month_end = month_start + pd.offsets.MonthBegin(1)
    month_grid = pd.date_range(month_start, month_end, freq="15min", inclusive="left")
    grid_wh = measured_wh.reindex(month_grid.tz_convert("UTC"))
    missing = grid_wh.isna()
    gap_length = pd.Series(missing.groupby((~missing).cumsum()).transform("sum"))
    month_wh = (
        grid_wh.interpolate(limit_area="inside")
        .where(~missing | (gap_length <= 4))
        .add(0.5)
        .floordiv(1)
    )

    local_times = pd.DatetimeIndex(month_wh.index).tz_convert(BERLIN).time
    is_day = (local_times >= day_from) & (local_times < day_to)
    day_kwh = month_wh[is_day].sum() / 1000
    night_kwh = month_wh[~is_day].sum() / 1000
    day_eur = day_kwh * day_ct / 100
    night_eur = night_kwh * night_ct / 100

    print(f"intervals     {len(month_wh)}")
    print(f"measured      {measured_wh.index.isin(month_wh.index).sum()}")
    print(f"day kWh       {day_kwh:.3f}")
    print(f"night kWh     {night_kwh:.3f}")
    print(f"day EUR       {day_eur:.4f}")
    print(f"night EUR     {night_eur:.4f}")
    print(f"fee EUR       {fee:.2f}")
    print(f"total EUR     {day_eur + night_eur + fee:.2f}")


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]] or [ROOT / "readings.csv", ROOT / "tariff.json"]
    main(*args)
