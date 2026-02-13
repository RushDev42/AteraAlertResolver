import json
import logging
from pathlib import Path

import typer

from .api import AteraClient
from .extract import detect_ticket_source, extract_alert_id, extract_ticket_status, extract_alert_status, extract_ticket_id_from_alert
from .sync import run_sync

app = typer.Typer(add_completion=False)

FIXTURES_DIR = Path("fixtures")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _summarize_ticket(ticket_json: dict) -> dict:
    ticket_id = ticket_json.get("TicketID") or ticket_json.get("Id") or ticket_json.get("ID") or ticket_json.get("id")
    return {
        "ticketId": ticket_id,
        "ticketStatus": extract_ticket_status(ticket_json),
        "source": detect_ticket_source(ticket_json),
        "alertId": extract_alert_id(ticket_json),
    }


@app.command("test")
def test_command() -> None:
    """Fetch known tickets and save fixtures."""
    _configure_logging()
    client = AteraClient()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for ticket_id in [9981, 9956]:
        response = client.get_ticket(ticket_id)
        if response.status_code != 200:
            typer.echo(
                json.dumps(
                    {
                        "error": "ticket_fetch_failed",
                        "ticketId": ticket_id,
                        "statusCode": response.status_code,
                        "responseBody": response.text,
                    },
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

        ticket_json = response.json_data or {}
        summary = _summarize_ticket(ticket_json)
        typer.echo(json.dumps(summary, indent=2))

        fixture_path = FIXTURES_DIR / f"ticket_{ticket_id}.json"
        fixture_path.write_text(json.dumps(ticket_json, indent=2))

    typer.echo(
        "Note: ticket fixtures did not include an alert id. "
        "Provide an alert id to test alert->ticket correlation."
    )


@app.command("alert-sample")
def alert_sample_command(alert_id: int) -> None:
    """Fetch an alert by id and save a fixture (manual)."""
    _configure_logging()
    client = AteraClient()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    response = client.get_alert(alert_id)
    if response.status_code != 200:
        typer.echo(
            json.dumps(
                {
                    "error": "alert_fetch_failed",
                    "alertId": alert_id,
                    "statusCode": response.status_code,
                    "responseBody": response.text,
                },
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    alert_json = response.json_data or {}
    summary = {
        "alertId": alert_id,
        "alertStatus": extract_alert_status(alert_json),
        "ticketId": extract_ticket_id_from_alert(alert_json),
    }
    typer.echo(json.dumps(summary, indent=2))

    fixture_path = FIXTURES_DIR / "alert_sample.json"
    fixture_path.write_text(json.dumps(alert_json, indent=2))


@app.command("alerts-dump")
def alerts_dump_command() -> None:
    """Dump a few alert list items to fixtures for inspection."""
    _configure_logging()
    client = AteraClient()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    alerts = client.list_alerts("Open")
    sample = alerts[:5]
    typer.echo(json.dumps({"count": len(alerts), "sample": sample}, indent=2))

    fixture_path = FIXTURES_DIR / "alerts_list_sample.json"
    fixture_path.write_text(json.dumps(sample, indent=2))


@app.command("alerts-export")
def alerts_export_command() -> None:
    """Export full alert list to a JSON file for inspection."""
    _configure_logging()
    client = AteraClient()
    output = "fixtures/alerts_open_full.json"
    alerts = client.list_alerts("Open")
    Path(output).write_text(json.dumps(alerts, indent=2))
    typer.echo(json.dumps({"count": len(alerts), "output": output}, indent=2))


@app.command("run")
def run_command(
    max_alerts: int = typer.Argument(50, min=1),
    days_back: int = typer.Argument(3, min=1),
) -> None:
    """Run alert-ticket sync for current tickets."""
    _configure_logging()
    client = AteraClient()
    exit_code = run_sync(client, "Resolved", max_alerts=max_alerts, days_back=days_back)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
