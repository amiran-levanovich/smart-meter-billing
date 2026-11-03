from app.demo import DEMO_MONTHS, seed_demo
from app.seed import SEED_METER_PUBLIC_ID


def test_months_span_the_first_to_the_last_reading(client):
    assert client.get("/api/months").json() == {"first": "2026-10", "last": "2026-10"}

    client.post(
        f"/api/meters/{SEED_METER_PUBLIC_ID}/readings",
        json=[{"timestamp": "2026-11-03T08:00:00+01:00", "energy_wh": 500}],
    )

    assert client.get("/api/months").json() == {"first": "2026-10", "last": "2026-11"}


def test_demo_months_are_fully_measured_and_leave_december_empty(client):
    with client.app.state.sessions() as session:
        seed_demo(session)

    for year, month in DEMO_MONTHS:
        bill = client.get(f"/api/bill/{year}-{month:02d}").json()
        assert [n for n in bill["notices"] if n["kind"] == "estimated"] == []
        assert bill["lines"][0]["quantity"] != "0.000"
    december = client.get("/api/bill/2026-12").json()
    assert (december["total_eur"], december["notices"]) == ("12.90", [])
    assert client.get("/api/months").json() == {"first": "2026-08", "last": "2027-01"}
    assert client.get("/api/bill/2026-10").json()["total_eur"] == "2295.99"


def test_demo_seed_is_repeatable(client):
    with client.app.state.sessions() as session:
        seed_demo(session)
        assert seed_demo(session).inserted == 0
