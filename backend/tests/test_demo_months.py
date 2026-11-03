from app.demo import DEMO_MONTHS, seed_demo
from app.seed import SEED_METER_PUBLIC_ID


def test_latest_month_is_the_last_month_with_readings(client):
    assert client.get("/api/months/latest").json() == {"month": "2026-10"}

    client.post(
        f"/api/meters/{SEED_METER_PUBLIC_ID}/readings",
        json=[{"timestamp": "2026-11-03T08:00:00+01:00", "energy_wh": 500}],
    )

    assert client.get("/api/months/latest").json() == {"month": "2026-11"}


def test_demo_months_are_fully_measured_and_leave_december_empty(client):
    with client.app.state.sessions() as session:
        seed_demo(session)

    for year, month in DEMO_MONTHS:
        bill = client.get(f"/api/bill/{year}-{month:02d}").json()
        assert [n for n in bill["notices"] if n["kind"] == "estimated"] == []
        assert bill["lines"][0]["quantity"] != "0.000"
    assert client.get("/api/months/latest").json() == {"month": "2027-01"}
    assert client.get("/api/bill/2026-10").json()["total_eur"] == "2295.99"


def test_demo_seed_is_repeatable(client):
    with client.app.state.sessions() as session:
        seed_demo(session)
        assert seed_demo(session).inserted == 0
