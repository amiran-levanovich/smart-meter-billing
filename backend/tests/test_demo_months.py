from datetime import UTC, datetime

from app import config
from app.demo import seed_demo
from app.seed import SEED_METER_PUBLIC_ID

NOW = datetime(2026, 11, 3, 9, 7, tzinfo=UTC)


def test_months_span_the_first_to_the_last_reading(client):
    assert client.get("/api/months").json() == {"first": "2026-10", "last": "2026-10"}

    client.post(
        f"/api/meters/{SEED_METER_PUBLIC_ID}/readings",
        json=[{"timestamp": "2026-11-03T08:00:00+01:00", "energy_wh": 500}],
    )

    assert client.get("/api/months").json() == {"first": "2026-10", "last": "2026-11"}


def test_demo_fills_five_months_back_leaves_july_empty_and_runs_november_up_to_now(
    client, monkeypatch
):
    monkeypatch.setattr(config, "now", lambda: NOW)
    with client.app.state.sessions() as session:
        seed_demo(session, NOW)

    for month in ["2026-05", "2026-06", "2026-08", "2026-09"]:
        bill = client.get(f"/api/bill/{month}").json()
        assert (bill["unbilled_intervals"], bill["in_progress"]) == (0, False), month
        assert [n for n in bill["notices"] if n["kind"] == "estimated"] == [], month
    july = client.get("/api/bill/2026-07").json()
    assert (july["total_eur"], july["measured_intervals"]) == ("12.90", 0)
    november = client.get("/api/bill/2026-11").json()
    assert (november["unbilled_intervals"], november["in_progress"]) == (0, True)
    assert november["period"]["end"] == "2026-11-03T10:00:00+01:00"
    assert client.get("/api/months").json() == {"first": "2026-05", "last": "2026-11"}
    assert client.get("/api/bill/2026-10").json()["total_eur"] == "2295.99"


def test_demo_seed_is_repeatable(client):
    with client.app.state.sessions() as session:
        seed_demo(session, NOW)
        assert seed_demo(session, NOW).inserted == 0
