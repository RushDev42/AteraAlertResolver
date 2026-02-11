from __future__ import annotations

import logging
from typing import Optional

from .api import AteraClient
from .extract import (
    detect_ticket_source,
    extract_alert_status,
    extract_ticket_id_from_alert,
    extract_ticket_status,
)

LOGGER = logging.getLogger("atera_sync")


def _log(event: str, **fields: object) -> None:
    parts = [f"event={event}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    LOGGER.info(" ".join(parts))


def _is_alert_source(source_value: Optional[str]) -> bool:
    return bool(source_value and "alert" in source_value.lower())


def _is_terminal_ticket_status(status_value: Optional[str]) -> bool:
    if not status_value:
        return False
    return status_value.lower() in {"resolved", "closed", "merged", "deleted"}


def run_sync(client: AteraClient, alert_status_filter: str = "Open") -> int:
    total_checked = 0
    total_updated = 0
    total_missing_ticket_id = 0
    total_duplicate_ticket = 0
    seen_ticket_ids: set[int] = set()

    alerts = client.list_alerts(alert_status_filter)
    _log("alerts_listed", alertStatus=alert_status_filter, count=len(alerts))

    for alert in alerts:
        alert_id = alert.get("AlertID") or alert.get("AlertId") or alert.get("Id") or alert.get("ID") or alert.get("id")
        if not alert_id:
            _log("alert_skip", reason="missing_alert_id")
            continue

        alert_response = client.get_alert(int(alert_id))
        if alert_response.status_code != 200:
            _log("alert_fetch_failed", alertId=alert_id, statusCode=alert_response.status_code)
            return 1

        alert_detail = alert_response.json_data or {}
        alert_status = extract_alert_status(alert_detail) or extract_alert_status(alert) or alert_status_filter
        if alert_status.lower() != "open":
            continue

        ticket_id = extract_ticket_id_from_alert(alert_detail) or extract_ticket_id_from_alert(alert)
        if not ticket_id:
            total_missing_ticket_id += 1
            _log("alert_skip", alertId=alert_id, reason="missing_ticket_id")
            continue
        if int(ticket_id) in seen_ticket_ids:
            total_duplicate_ticket += 1
            _log("alert_skip", alertId=alert_id, ticketId=ticket_id, reason="duplicate_ticket_in_run")
            continue
        seen_ticket_ids.add(int(ticket_id))

        ticket_response = client.get_ticket(int(ticket_id))
        if ticket_response.status_code != 200:
            _log(
                "ticket_fetch_failed",
                ticketId=ticket_id,
                alertId=alert_id,
                statusCode=ticket_response.status_code,
            )
            return 1

        ticket = ticket_response.json_data or {}
        ticket_status = extract_ticket_status(ticket)

        source_value = detect_ticket_source(ticket)
        if not _is_alert_source(source_value):
            continue

        total_checked += 1

        if _is_terminal_ticket_status(ticket_status):
            _log("ticket_terminal_status", ticketId=ticket_id, status=ticket_status)
            continue

        update_response = client.update_ticket_status(int(ticket_id), "Resolved")
        if update_response.status_code not in (200, 201):
            _log(
                "ticket_update_failed",
                ticketId=ticket_id,
                statusCode=update_response.status_code,
            )
            return 1

        total_updated += 1
        _log(
            "ticket_updated",
            ticketId=ticket_id,
            prevStatus=ticket_status,
            newStatus="Resolved",
            alertId=alert_id,
            alertStatus=alert_status,
        )

    _log(
        "sync_complete",
        checked=total_checked,
        updated=total_updated,
        missingTicketId=total_missing_ticket_id,
        duplicateTicket=total_duplicate_ticket,
    )
    return 0
