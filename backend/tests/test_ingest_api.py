import pytest

from app.main import MAX_READINGS
from app.seed import SEED_METER_PUBLIC_ID

URL = f"/api/meters/{SEED_METER_PUBLIC_ID}/readings"


def notices_of_kind(client, kind):
    notices = client.get("/api/bill/2026-10").json()["notices"]
    return [notice for notice in notices if notice["kind"] == kind]


def test_unknown_meter_is_not_found(client):
    response = client.post(
        "/api/meters/00000000-0000-0000-0000-000000000000/readings",
        json=[{"timestamp": "2026-10-02T10:00:00+02:00", "energy_wh": 100}],
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "reading",
    [
        {"timestamp": "2026-10-02T10:00:00", "energy_wh": 100},
        {"timestamp": "2026-10-02T10:07:00+02:00", "energy_wh": 100},
        {"timestamp": "2026-10-02T10:00:30+02:00", "energy_wh": 100},
        {"timestamp": "2026-10-02T10:00:00+02:00", "energy_wh": -1},
        {"timestamp": "2026-10-02T10:00:00+02:00", "energy_wh": 1.5},
        {"timestamp": "2026-10-02T10:00:00+02:00", "energy_wh": "100"},
        {"timestamp": "2026-10-02T10:00:00+02:00", "energy_wh": 10**20},
    ],
    ids=["naive", "not-15-minutes", "seconds", "negative", "fraction", "string", "absurd"],
)
def test_invalid_reading_is_rejected(client, reading):
    response = client.post(URL, json=[reading])

    assert response.status_code == 422


def test_a_full_month_with_the_autumn_clock_change_fits_in_one_batch(client):
    # 31 days x 96 intervals + 4 for the repeated hour on 25 Oct
    readings = [{"timestamp": "2026-10-08T10:15:00+02:00", "energy_wh": 3200}] * 2980

    assert client.post(URL, json=readings).status_code == 200


def test_more_readings_than_a_month_holds_are_too_large(client):
    readings = [{"timestamp": "2026-10-02T10:00:00+02:00", "energy_wh": 1}] * (MAX_READINGS + 1)

    assert client.post(URL, json=readings).status_code == 413


def test_oversized_body_is_rejected_before_parsing(client):
    body = b"[" + b" " * 2_000_000 + b"]"

    response = client.post(URL, content=body, headers={"content-type": "application/json"})

    assert response.status_code == 413


def test_oversized_chunked_body_without_length_is_rejected(client):
    def chunks():
        yield b"["
        for _ in range(2_000):
            yield b" " * 1_000
        yield b"]"

    response = client.post(URL, content=chunks(), headers={"content-type": "application/json"})

    assert response.status_code == 413


def test_resending_the_same_value_changes_nothing(client):
    before = client.get("/api/bill/2026-10").json()

    response = client.post(
        URL, json=[{"timestamp": "2026-10-08T10:15:00+02:00", "energy_wh": 3200}]
    )

    assert response.json() == {"inserted": 0, "corrected": 0, "unchanged": 1}
    assert client.get("/api/bill/2026-10").json() == before


def test_changed_value_shows_as_a_correction_on_the_bill(client):
    response = client.post(
        URL, json=[{"timestamp": "2026-10-08T10:15:00+02:00", "energy_wh": 3500}]
    )

    assert response.json() == {"inserted": 0, "corrected": 1, "unchanged": 0}
    [correction] = notices_of_kind(client, "corrected")
    assert (correction["energy_wh"], correction["previous_energy_wh"]) == (3500, 3200)


def test_two_values_in_one_batch_report_the_one_directly_before(client):
    response = client.post(
        URL,
        json=[
            {"timestamp": "2026-10-08T10:15:00+02:00", "energy_wh": 4000},
            {"timestamp": "2026-10-08T10:15:00+02:00", "energy_wh": 4100},
        ],
    )

    assert response.json() == {"inserted": 0, "corrected": 2, "unchanged": 0}
    [correction] = notices_of_kind(client, "corrected")
    assert (correction["energy_wh"], correction["previous_energy_wh"]) == (4100, 4000)


def test_real_value_replaces_the_estimate_and_changes_the_total(client):
    response = client.post(URL, json=[{"timestamp": "2026-10-13T12:30:00Z", "energy_wh": 2300}])

    assert response.json() == {"inserted": 1, "corrected": 0, "unchanged": 0}
    bill = client.get("/api/bill/2026-10").json()
    assert notices_of_kind(client, "estimated") == []
    # day 4562.796 + 0.012 kWh = 4562.808 kWh x 31.847 ct = 1453.1174 -> 1453.12
    assert bill["lines"][0]["amount_eur"] == "1453.12"
    assert bill["total_eur"] == "2296.00"
