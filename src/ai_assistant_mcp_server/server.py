"""MCP server exposing the synthetic company to an AI assistant or agent."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .generate import DB_NAME, build_dataset
from .tools import Lab

INSTRUCTIONS = (
    "Fake company data for AI security demos. All values are synthetic. "
    "Use the tools to look up customers, patients, tickets and documents."
)


def create_server(lab: Lab) -> MCPServer:
    server = MCPServer(name="ai-assistant-mcp-server", instructions=INSTRUCTIONS)

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
    if a.regenerate or not (data / DB_NAME).exists():
        build_dataset(data, seed=a.seed)

    server = create_server(Lab(data, a.mode))
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
