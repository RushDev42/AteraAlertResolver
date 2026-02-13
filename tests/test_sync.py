from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atera_sync.sync import run_sync


@dataclass
class _Response:
    status_code: int
    json_data: Any
    text: str = ""


class _FakeClient:
    def __init__(self) -> None:
        self.updated: list[tuple[int, str]] = []
        self.commented: list[tuple[int, str]] = []

    def list_alerts(self, status: str, max_items: int | None = None):  # noqa: ANN201 - mirrors production client
        assert status == "Resolved"
        assert max_items == 50
        return [
            {"AlertID": 1, "status": "Open", "severity": "Warning"},
            {"AlertID": 2, "status": "Resolved", "severity": "Critical"},
            {"AlertID": 3, "status": "Resolved", "severity": "Information"},
        ]

    def get_alert(self, alert_id: int) -> _Response:
        if alert_id == 1:
            return _Response(200, {"AlertID": 1, "status": "Open", "severity": "Warning", "ticketId": 10031})
        if alert_id == 2:
            return _Response(200, {"AlertID": 2, "status": "Resolved", "severity": "Critical", "ticketId": 10032})
        if alert_id == 3:
            return _Response(200, {"AlertID": 3, "status": "Resolved", "severity": "Information", "ticketId": 10033})
        return _Response(404, {})

    def get_ticket(self, ticket_id: int) -> _Response:
        return _Response(
            200,
            {
                "TicketID": ticket_id,
                "status": "Open",
                "source": "Alert",
            },
        )

    def update_ticket_status(self, ticket_id: int, new_status: str) -> _Response:
        self.updated.append((ticket_id, new_status))
        return _Response(200, {})

    def add_ticket_comment(self, ticket_id: int, comment_text: str) -> _Response:
        self.commented.append((ticket_id, comment_text))
        return _Response(201, {})


def test_run_sync_only_resolves_tickets_for_resolved_alerts() -> None:
    client = _FakeClient()

    exit_code = run_sync(client, "Resolved")

    assert exit_code == 0
    assert client.commented == [(10032, "alert resolved, closing ticket by automation")]
    assert client.updated == [(10032, "Resolved")]
