from __future__ import annotations

import logging
from typing import Any, Dict, Optional

LOGGER = logging.getLogger("atera_sync")


def _get_value_case_insensitive(data: Dict[str, Any], target_key: str) -> Optional[Any]:
    for key, value in data.items():
        if isinstance(key, str) and key.lower() == target_key.lower():
            return value
    return None


def _extract_from_keys(data: Dict[str, Any], keys: list[str]) -> Optional[Any]:
    for key in keys:
        value = _get_value_case_insensitive(data, key)
        if value is not None:
            return value
    return None


def detect_ticket_source(ticket_json: Dict[str, Any]) -> Optional[str]:
    if not isinstance(ticket_json, dict):
        return None

    candidate_keys = ["source", "TicketSource", "Source", "SourceType", "TicketSourceType"]
    value = _extract_from_keys(ticket_json, candidate_keys)
    if isinstance(value, dict):
        value = value.get("Name") or value.get("Value")
    if isinstance(value, str):
        return value

    for key, nested in ticket_json.items():
        if isinstance(key, str) and "source" in key.lower():
            if isinstance(nested, str):
                return nested
            if isinstance(nested, dict):
                nested_value = nested.get("Name") or nested.get("Value")
                if isinstance(nested_value, str):
                    return nested_value

    return None


def extract_alert_id(ticket_json: Dict[str, Any]) -> Optional[int]:
    if not isinstance(ticket_json, dict):
        return None

    candidate_keys = [
        "AlertId",
        "AlertID",
        "AlertIdentifier",
        "RelatedAlertId",
        "RelatedAlertID",
        "alertId",
        "alertID",
        "relatedAlertId",
    ]

    value = _extract_from_keys(ticket_json, candidate_keys)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)

    for key, nested in ticket_json.items():
        if isinstance(key, str) and key.lower().endswith("alertid"):
            if isinstance(nested, int):
                return nested
            if isinstance(nested, str) and nested.isdigit():
                return int(nested)

    alert_obj = _get_value_case_insensitive(ticket_json, "alert")
    if isinstance(alert_obj, dict):
        for key in ("Id", "ID", "id"):
            nested_value = alert_obj.get(key)
            if isinstance(nested_value, int):
                return nested_value
            if isinstance(nested_value, str) and nested_value.isdigit():
                return int(nested_value)

    return None


def extract_alert_status(alert_json: Dict[str, Any]) -> Optional[str]:
    if not isinstance(alert_json, dict):
        return None

    candidate_keys = ["Status", "AlertStatus", "status", "alertStatus"]
    value = _extract_from_keys(alert_json, candidate_keys)
    if isinstance(value, dict):
        value = value.get("Name") or value.get("Value")
    if isinstance(value, str):
        return value

    for key, nested in alert_json.items():
        if isinstance(key, str) and "status" in key.lower():
            if isinstance(nested, str):
                return nested
            if isinstance(nested, dict):
                nested_value = nested.get("Name") or nested.get("Value")
                if isinstance(nested_value, str):
                    return nested_value

    return None


def extract_ticket_status(ticket_json: Dict[str, Any]) -> Optional[str]:
    if not isinstance(ticket_json, dict):
        return None

    candidate_keys = ["TicketStatus", "Status", "ticketStatus", "status"]
    value = _extract_from_keys(ticket_json, candidate_keys)
    if isinstance(value, dict):
        value = value.get("Name") or value.get("Value")
    if isinstance(value, str):
        return value

    return None


def extract_ticket_id_from_alert(alert_json: Dict[str, Any]) -> Optional[int]:
    if not isinstance(alert_json, dict):
        return None

    candidate_keys = [
        "TicketId",
        "TicketID",
        "RelatedTicketId",
        "RelatedTicketID",
        "ticketId",
        "ticketID",
        "relatedTicketId",
    ]
    value = _extract_from_keys(alert_json, candidate_keys)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)

    for key, nested in alert_json.items():
        if isinstance(key, str) and key.lower().endswith("ticketid"):
            if isinstance(nested, int):
                return nested
            if isinstance(nested, str) and nested.isdigit():
                return int(nested)

    ticket_obj = _get_value_case_insensitive(alert_json, "ticket")
    if isinstance(ticket_obj, dict):
        for key in ("Id", "ID", "id"):
            nested_value = ticket_obj.get(key)
            if isinstance(nested_value, int):
                return nested_value
            if isinstance(nested_value, str) and nested_value.isdigit():
                return int(nested_value)

    return None
