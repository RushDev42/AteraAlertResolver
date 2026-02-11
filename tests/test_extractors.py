import json
from pathlib import Path

import pytest

from atera_sync.extract import (
    detect_ticket_source,
    extract_alert_id,
    extract_alert_status,
    extract_ticket_id_from_alert,
    extract_ticket_status,
)

FIXTURES_DIR = Path("fixtures")


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {path} not found. Run: atera-sync test")
    return json.loads(path.read_text())


def test_extract_ticket_fields_from_fixture_9981():
    ticket = _load_fixture("ticket_9981.json")
    assert isinstance(detect_ticket_source(ticket), (str, type(None)))
    assert isinstance(extract_alert_id(ticket), (int, type(None)))
    assert isinstance(extract_ticket_status(ticket), (str, type(None)))


def test_extract_ticket_fields_from_fixture_9956():
    ticket = _load_fixture("ticket_9956.json")
    assert isinstance(detect_ticket_source(ticket), (str, type(None)))
    assert isinstance(extract_alert_id(ticket), (int, type(None)))
    assert isinstance(extract_ticket_status(ticket), (str, type(None)))


def test_extract_alert_status_from_fixture_if_present():
    alert_fixture = FIXTURES_DIR / "alert_sample.json"
    if not alert_fixture.exists():
        pytest.skip("Fixture fixtures/alert_sample.json not found. Optional.")
    alert = json.loads(alert_fixture.read_text())
    assert isinstance(extract_alert_status(alert), (str, type(None)))


def test_extract_ticket_id_from_alert_fixture_if_present():
    alert_fixture = FIXTURES_DIR / "alert_sample.json"
    if not alert_fixture.exists():
        pytest.skip("Fixture fixtures/alert_sample.json not found. Optional.")
    alert = json.loads(alert_fixture.read_text())
    assert isinstance(extract_ticket_id_from_alert(alert), (int, type(None)))
