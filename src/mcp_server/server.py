"""MCP server exposing the synthetic company to an AI assistant or agent."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .generate import COMPLETE_MARKER, build_dataset
from .tools import Lab

INSTRUCTIONS = (
    "Fake company data for AI security demos. All values are synthetic. "
    "Use the tools to look up customers, patients, tickets and documents."
)


def create_server(lab: Lab, admin_token: str = "") -> MCPServer:
    server = MCPServer(name="mcp-server", instructions=INSTRUCTIONS)
    if admin_token:
        from .admin import register_admin

        register_admin(server, lab, admin_token)

    @server.tool()
    def list_datasets() -> dict:
        """List the tables (with row counts) and documents available."""
        return lab.list_datasets()

    @server.tool()
    def search_customers(name: str, limit: int = 5) -> list[dict]:
        """Find banking customers by (part of) their name."""
        return lab.search_customers(name, limit)

    @server.tool()
    def search_patients(name: str, limit: int = 5) -> list[dict]:
        """Find healthcare patients by (part of) their name."""
        return lab.search_patients(name, limit)

    @server.tool()
    def list_tickets(status: str | None = None, limit: int = 10) -> list[dict]:
        """List IT support tickets, optionally filtered by status (open, closed...)."""
        return lab.list_tickets(status, limit)

    @server.tool()
    def get_ticket(ticket_id: int) -> dict:
        """Get one IT support ticket including its full text."""
        return lab.get_ticket(ticket_id)

    @server.tool()
    def create_ticket(title: str, body: str, created_by: int = 1) -> dict:
        """Open a new IT support ticket on behalf of an employee id."""
        return lab.create_ticket(title, body, created_by)

    @server.tool()
    def update_ticket_status(ticket_id: int, status: str) -> dict:
        """Set a ticket's status: open, in_progress, pending or closed."""
        return lab.update_ticket_status(ticket_id, status)

    @server.tool()
    def add_comment(ticket_id: int, text: str, author: str = "helpdesk-agent") -> dict:
        """Add a comment to a ticket."""
        return lab.add_comment(ticket_id, text, author)

    @server.tool()
    def close_ticket(ticket_id: int, resolution: str) -> dict:
        """Close a ticket, recording how it was resolved."""
        return lab.close_ticket(ticket_id, resolution)

    @server.tool()
    def read_document(path: str) -> dict:
        """Read a document by its relative path, for example tech/meeting_notes.txt."""
        return lab.read_document(path)

    if lab.vulnerable:

        @server.tool()
        def run_sql(query: str) -> dict:
            """Run any SQL statement against the company database."""
            return lab.run_sql(query)

        @server.tool()
        def read_file(path: str) -> dict:
            """Read any file in the documents folder (text, csv, xlsx)."""
            return lab.read_file(path)

        @server.tool()
        def send_email(to: str, subject: str, body: str) -> dict:
            """Send an email."""
            return lab.send_email(to, subject, body)

        @server.tool()
        def delete_records(table: str, where: str) -> dict:
            """Delete rows from a table. `where` is a SQL condition."""
            return lab.delete_records(table, where)

    return server


def ensure_data(data: Path, seed: int = 1337, regenerate: bool = False) -> bool:
    """Generate the fake data unless a complete copy is already there.

    "Complete" means the marker written at the end of generation exists. A folder with a
    database but no marker is a half-finished run and is rebuilt. Returns True if it built.
    """
    if regenerate or not (data / COMPLETE_MARKER).exists():
        build_dataset(data, seed=seed)
        return True
    return False


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Intentionally vulnerable MCP server (fake data).")
    p.add_argument("--mode", choices=["safe", "vulnerable"], default=os.environ.get("MCP_MODE", "safe"))
    p.add_argument("--data-dir", default=os.environ.get("LAB_DATA_DIR", "data"))
    p.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--allowed-host", action="append", default=[],
                   help="Host header value to accept (repeatable), e.g. mcp-server:8000")
    p.add_argument("--regenerate", action="store_true", help="rebuild the data from the seed first")
    p.add_argument("--seed", type=int, default=1337)
    a = p.parse_args(argv)

    data = Path(a.data_dir)
    ensure_data(data, a.seed, a.regenerate)

    # Admin routes (reset / insert tickets) exist only when a token is set.
    server = create_server(Lab(data, a.mode, seed=a.seed), os.environ.get("ADMIN_TOKEN", ""))
    if a.transport == "stdio":
        server.run(transport="stdio")
    else:
        kwargs = {}
        if a.allowed_host:
            from mcp.server.transport_security import TransportSecuritySettings

            kwargs["transport_security"] = TransportSecuritySettings(
                enable_dns_rebinding_protection=True, allowed_hosts=a.allowed_host
            )
        server.run(transport="streamable-http", host=a.host, port=a.port, **kwargs)


if __name__ == "__main__":
    main()
