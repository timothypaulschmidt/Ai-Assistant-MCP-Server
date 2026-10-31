import asyncio
import json
import sqlite3

import pytest
from mcp.client import Client

from ai_assistant_mcp_server.generate import build_dataset
from ai_assistant_mcp_server.payloads import CANARIES
from ai_assistant_mcp_server.server import create_server
from ai_assistant_mcp_server.tools import Lab


@pytest.fixture()
def data(tmp_path):
    build_dataset(tmp_path, seed=7, scale=0.3)
    return tmp_path


def call(lab, tool, args=None):
    async def go():
        async with Client(create_server(lab)) as c:
            if tool == "__list__":
                return sorted(t.name for t in (await c.list_tools()).tools)
            res = await c.call_tool(tool, args or {})
            return res

    return asyncio.run(go())


def payload(res):
    if res.structured_content is not None:
        sc = res.structured_content
        return sc.get("result", sc)
    return json.loads(res.content[0].text)


def test_tool_lists_differ_by_mode(data):
    safe = call(Lab(data, "safe"), "__list__")
    vuln = call(Lab(data, "vulnerable"), "__list__")
    assert "run_sql" not in safe and "send_email" not in safe
    assert {"run_sql", "read_file", "send_email", "delete_records"} <= set(vuln)
    assert set(safe) <= set(vuln)


def test_safe_search_masks_ssn_and_hides_password(data):
    rows = payload(call(Lab(data, "safe"), "search_customers", {"name": "Canary"}))
    assert rows and rows[0]["ssn"] == "***-**-0001"
    assert "online_password" not in rows[0]
    assert CANARIES["ssn"] not in json.dumps(rows)


def test_vulnerable_search_leaks_canaries(data):
    rows = payload(call(Lab(data, "vulnerable"), "search_customers", {"name": "Canary"}))
    assert rows[0]["ssn"] == CANARIES["ssn"]
    assert rows[0]["online_password"] == CANARIES["password"]


def test_limit_is_capped_in_safe_mode(data):
    assert len(payload(call(Lab(data, "safe"), "search_customers", {"name": "", "limit": 500}))) <= 10


def test_poisoned_ticket_reaches_the_model_even_in_safe_mode(data):
    lab = Lab(data, "safe")
    con = sqlite3.connect(lab.db_path)
    tid = con.execute("SELECT row_id FROM _lab_poisoned WHERE table_name='tech_tickets' LIMIT 1").fetchone()[0]
    ticket = payload(call(lab, "get_ticket", {"ticket_id": tid}))
    assert "example.invalid" in ticket["body"]


def test_safe_read_document_is_allowlisted(data):
    lab = Lab(data, "safe")
    assert "text" in payload(call(lab, "read_document", {"path": "tech/meeting_notes.txt"}))
    assert "error" in payload(call(lab, "read_document", {"path": "tech/production.env"}))


def test_run_sql_reads_secrets_but_not_the_answer_key(data):
    lab = Lab(data, "vulnerable")
    ok = payload(call(lab, "run_sql", {"query": "SELECT password FROM tech_credentials LIMIT 2"}))
    assert len(ok["rows"]) == 2
    blocked = payload(call(lab, "run_sql", {"query": "SELECT * FROM _lab_canaries"}))
    assert "error" in blocked
    blocked = payload(call(lab, "run_sql", {"query": "DELETE FROM _lab_poisoned"}))
    assert "error" in blocked


def test_run_sql_can_destroy_data_and_regenerating_resets(data):
    lab = Lab(data, "vulnerable")
    payload(call(lab, "run_sql", {"query": "DELETE FROM banking_transactions"}))
    count = payload(call(lab, "run_sql", {"query": "SELECT COUNT(*) FROM banking_transactions"}))
    assert count["rows"][0][0] == 0
    build_dataset(data, seed=7, scale=0.3)
    count = payload(call(lab, "run_sql", {"query": "SELECT COUNT(*) FROM banking_transactions"}))
    assert count["rows"][0][0] > 0


def test_read_file_is_sandboxed_to_docs(data):
    lab = Lab(data, "vulnerable")
    assert "text" in payload(call(lab, "read_file", {"path": "tech/production.env"}))
    assert "error" in payload(call(lab, "read_file", {"path": "../company.db"}))
    assert "error" in payload(call(lab, "read_file", {"path": "/etc/passwd"}))
    xl = payload(call(lab, "read_file", {"path": "hr/payroll_2026.xlsx"}))
    assert xl["sheets"]


def test_send_email_only_writes_to_the_outbox(data):
    lab = Lab(data, "vulnerable")
    res = payload(call(lab, "send_email", {"to": "audit@example.invalid", "subject": "s", "body": "b"}))
    files = list((data / "outbox").glob("*.json"))
    assert len(files) == 1 and res["outbox_file"] == files[0].name
    assert json.loads(files[0].read_text())["to"] == "audit@example.invalid"


def test_delete_records_rejects_bad_table_names(data):
    lab = Lab(data, "vulnerable")
    assert "error" in payload(call(lab, "delete_records", {"table": "x; DROP TABLE y", "where": "1=1"}))
    assert "error" in payload(call(lab, "delete_records", {"table": "_lab_canaries", "where": "1=1"}))
