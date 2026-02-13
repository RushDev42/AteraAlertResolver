from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from .api import AteraClient
from .extract import (
    extract_alert_severity,
    detect_ticket_source,
    extract_alert_status,
    extract_ticket_id_from_alert,
    extract_ticket_status,
)

LOGGER = logging.getLogger("atera_sync")
AUTO_CLOSE_COMMENT = "alert resolved, closing ticket by automation"


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


def _is_actionable_alert_severity(severity_value: Optional[str]) -> bool:
    if not severity_value:
        return False
    return severity_value.lower() in {"warning", "critical"}


def _parse_alert_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _extract_alert_datetime(alert_json: dict[str, Any]) -> Optional[datetime]:
    date_keys = [
        "Created",
        "CreatedOn",
        "CreatedDate",
        "CreatedAt",
        "AlertDate",
        "Date",
        "OpenedOn",
        "OpenDate",
        "LastModified",
        "UpdatedAt",
    ]
    for key in date_keys:
        value = alert_json.get(key)
        parsed = _parse_alert_datetime(value)
        if parsed:
            return parsed
    return None


def run_sync(
    client: AteraClient,
    alert_status_filter: str = "Resolved",
    max_alerts: Optional[int] = 50,
    days_back: Optional[int] = 3,
) -> int:
    total_alerts_reviewed = 0
    total_checked = 0
    total_updated = 0
    total_missing_ticket_id = 0
    total_duplicate_ticket = 0
    updated_ticket_ids: list[int] = []
    seen_ticket_ids: set[int] = set()

    _log("sync_start", alertStatus=alert_status_filter)
    alerts = client.list_alerts(alert_status_filter, max_items=max_alerts)

    original_count = len(alerts)
    if days_back is not None:
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        date_filtered: list[dict[str, Any]] = []
        unknown_date_count = 0
        for alert in alerts:
            alert_dt = _extract_alert_datetime(alert)
            if alert_dt is None:
                unknown_date_count += 1
                date_filtered.append(alert)
                continue
            if alert_dt >= cutoff:
                date_filtered.append(alert)
        alerts = date_filtered
        _log(
            "alerts_days_filter_applied",
            daysBack=days_back,
            beforeCount=original_count,
            afterCount=len(alerts),
            unknownDateCount=unknown_date_count,
        )

    if max_alerts is not None:
        _log("alerts_max_limit_applied", maxAlerts=max_alerts, resultingCount=len(alerts))

    _log("alerts_listed", alertStatus=alert_status_filter, count=len(alerts))

    for alert in alerts:
        total_alerts_reviewed += 1
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
        if alert_status.lower() != "resolved":
            continue
        alert_severity = extract_alert_severity(alert_detail) or extract_alert_severity(alert)
        if not _is_actionable_alert_severity(alert_severity):
            _log("alert_skip", alertId=alert_id, severity=alert_severity, reason="severity_not_actionable")
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

        comment_response = client.add_ticket_comment(int(ticket_id), AUTO_CLOSE_COMMENT)
        if comment_response.status_code not in (200, 201):
            _log(
                "ticket_comment_failed",
                ticketId=ticket_id,
                statusCode=comment_response.status_code,
                responseBody=comment_response.text,
            )
            return 1
        _log("ticket_comment_added", ticketId=ticket_id)

        update_response = client.update_ticket_status(int(ticket_id), "Resolved")
        if update_response.status_code not in (200, 201):
            _log(
                "ticket_update_failed",
                ticketId=ticket_id,
                statusCode=update_response.status_code,
            )
            return 1

        total_updated += 1
        updated_ticket_ids.append(int(ticket_id))
        _log(
            "ticket_updated",
            ticketId=ticket_id,
            prevStatus=ticket_status,
            newStatus="Resolved",
            alertId=alert_id,
            alertStatus=alert_status,
            alertSeverity=alert_severity,
        )

    _log(
        "sync_summary",
        alertsReviewed=total_alerts_reviewed,
        ticketsActioned=total_updated,
        updatedTickets=updated_ticket_ids,
    )
    _log(
        "sync_complete",
        alertsReviewed=total_alerts_reviewed,
        checked=total_checked,
        updated=total_updated,
        missingTicketId=total_missing_ticket_id,
        duplicateTicket=total_duplicate_ticket,
        updatedTickets=updated_ticket_ids,
    )
    return 0
