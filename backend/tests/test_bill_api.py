import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import CustomerRecord, MeterRecord
from app.main import app


def test_october_bill_matches_the_independent_cross_check(client):
    bill = client.get("/api/bill/2026-10").json()

    # make crosscheck: day 4562.796 kWh / 1453.1136, night 4279.988 kWh / 829.9753, total 2295.99
    assert [
        (line["kind"], line["quantity"], line["unit_price"], line["amount_eur"])
        for line in bill["lines"]
    ] == [
        ("day", "4562.796", "31.847", "1453.11"),
        ("night", "4279.988", "19.392", "829.98"),
        ("fee", "1", "12.90", "12.90"),
    ]
    assert bill["total_eur"] == "2295.99"
    assert bill["vat"] == {"rate": "0.19", "net_eur": "1929.40", "vat_eur": "366.59"}


def test_october_bill_names_customer_meter_and_period(client):
    bill = client.get("/api/bill/2026-10").json()

    assert bill["customer_name"] == "Bäckerei Sonnenschein"
    assert bill["meter_number"] == "1EBZ0100123456"
    assert bill["period"] == {
        "month": "2026-10",
        "start": "2026-10-01T00:00:00+02:00",
        "end": "2026-11-01T00:00:00+01:00",
    }


def test_october_bill_explains_the_three_data_traps(client):
    notices = client.get("/api/bill/2026-10").json()["notices"]

    assert notices == [
        {
            "kind": "corrected",
            "interval_start": "2026-10-08T10:15:00+02:00",
            "energy_wh": 3200,
            "previous_energy_wh": 2419,
            "amount_eur": None,
        },
        {
            "kind": "estimated",
            "interval_start": "2026-10-13T14:30:00+02:00",
            "energy_wh": 2288,
            "previous_energy_wh": None,
            "amount_eur": "0.73",
        },
        {
            "kind": "dst",
            "interval_start": "2026-10-25T02:00:00+01:00",
            "energy_wh": None,
            "previous_energy_wh": None,
            "amount_eur": None,
        },
    ]


def test_month_without_readings_bills_only_the_monthly_fee(client):
    bill = client.get("/api/bill/2026-11").json()

    assert [(line["kind"], line["amount_eur"]) for line in bill["lines"]] == [
        ("day", "0.00"),
        ("night", "0.00"),
        ("fee", "12.90"),
    ]
    assert bill["total_eur"] == "12.90"
    assert bill["notices"] == []


def test_customer_with_a_second_meter_gets_a_clear_error(client):
    with client.app.state.sessions() as session:
        customer = session.scalar(select(CustomerRecord))
        customer.meters.append(MeterRecord(public_id=uuid.uuid4(), meter_number="1EBZ0100999999"))
        session.commit()

    response = client.get("/api/bill/2026-10")

    assert response.status_code == 409


def test_malformed_month_is_rejected(client):
    assert client.get("/api/bill/2026-13").status_code == 422


def test_october_bill_carries_the_why_figures_and_daily_usage(client):
    bill = client.get("/api/bill/2026-10").json()

    assert bill["night_share_percent"] == "48"
    assert bill["night_saving_eur"] == "533.07"
    assert len(bill["daily"]) == 31
    assert bill["daily"][0]["date"] == "2026-10-01"


def test_restart_does_not_seed_twice(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'restart.db'}")
    for _ in range(2):
        with TestClient(app) as client:
            bill = client.get("/api/bill/2026-10").json()
    assert bill["total_eur"] == "2295.99"
    assert [n["kind"] for n in bill["notices"]] == ["corrected", "estimated", "dst"]
