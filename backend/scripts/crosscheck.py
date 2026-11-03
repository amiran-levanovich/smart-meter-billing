import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main(readings_csv: Path, tariff_json: Path) -> None:
    tariff = json.loads(tariff_json.read_text())
    day_ct = tariff["day"]["ct_per_kwh"]
    night_ct = tariff["night"]["ct_per_kwh"]
    fee = tariff["monthly_fee_eur"]
    day_from, day_to = (int(tariff["day"][k][:2]) for k in ("from", "to"))

    df = pd.read_csv(readings_csv, parse_dates=["timestamp"])
    first_of_its_local_time = ~df.duplicated("timestamp", keep="first")
    df["start"] = (
        df["timestamp"]
        .dt.tz_localize("Europe/Berlin", ambiguous=first_of_its_local_time.to_numpy())
        .dt.tz_convert("UTC")
    )
    energy = df.drop_duplicates("start", keep="last").set_index("start")["energy_wh"]

    local = energy.index.tz_convert("Europe/Berlin")
    month_start = local[0].normalize()
    month_end = month_start + pd.offsets.MonthBegin(1)
    full = pd.date_range(month_start, month_end, freq="15min", inclusive="left", tz="Europe/Berlin")
    energy = energy.reindex(full.tz_convert("UTC")).interpolate().pipe(lambda s: np.floor(s + 0.5))

    hours = energy.index.tz_convert("Europe/Berlin").hour
    is_day = (hours >= day_from) & (hours < day_to)
    day_kwh = energy[is_day].sum() / 1000
    night_kwh = energy[~is_day].sum() / 1000
    day_eur = day_kwh * day_ct / 100
    night_eur = night_kwh * night_ct / 100

    print(f"intervals     {len(energy)}")
    print(f"day kWh       {day_kwh:.3f}")
    print(f"night kWh     {night_kwh:.3f}")
    print(f"day EUR       {day_eur:.4f}")
    print(f"night EUR     {night_eur:.4f}")
    print(f"fee EUR       {fee:.2f}")
    print(f"total EUR     {day_eur + night_eur + fee:.2f}")


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]] or [ROOT / "readings.csv", ROOT / "tariff.json"]
    main(*args)
