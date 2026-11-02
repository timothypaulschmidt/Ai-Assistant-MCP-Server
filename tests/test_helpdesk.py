import json
import sqlite3

import pytest
from starlette.testclient import TestClient

from ai_assistant_mcp_server import helpdesk
from ai_assistant_mcp_server.generate import build_dataset
from ai_assistant_mcp_server.server import create_server
from ai_assistant_mcp_server.tools import Lab

from test_server import call, payload  # same helpers as the other server tests


@pytest.fixture()
def lab(tmp_path):
    build_dataset(tmp_path, seed=7, scale=0.3)
    return Lab(tmp_path, "safe", seed=7, scale=0.3)


def test_ticket_tools_exist_in_both_modes(lab):
    for mode in ("safe", "vulnerable"):
        names = call(Lab(lab.data_dir, mode), "__list__")
        assert {"create_ticket", "update_ticket_status", "add_comment", "close_ticket"} <= set(names)


def test_ticket_lifecycle(lab):
    new = payload(call(lab, "create_ticket", {"title": "Printer jam", "body": "Floor 2", "created_by": 1}))
    assert new["status"] == "open"
    tid = new["id"]
    assert payload(call(lab, "update_ticket_status", {"ticket_id": tid, "status": "in_progress"}))["status"] == "in_progress"
    payload(call(lab, "add_comment", {"ticket_id": tid, "text": "Looking into it"}))
    payload(call(lab, "close_ticket", {"ticket_id": tid, "resolution": "Cleared the jam"}))
    ticket = payload(call(lab, "get_ticket", {"ticket_id": tid}))
    assert ticket["status"] == "closed"
    assert [c["author"] for c in ticket["comments"]] == ["helpdesk-agent", "helpdesk-agent"]
    assert ticket["comments"][1]["body"].startswith("Resolution:")


def test_ticket_tools_validate_input(lab):
    assert "error" in payload(call(lab, "update_ticket_status", {"ticket_id": 1, "status": "exploded"}))
    assert "error" in payload(call(lab, "update_ticket_status", {"ticket_id": 99999, "status": "open"}))
    assert "error" in payload(call(lab, "add_comment", {"ticket_id": 99999, "text": "x"}))
    assert "error" in payload(call(lab, "create_ticket", {"title": " ", "body": "x"}))
    assert "error" in payload(call(lab, "create_ticket", {"title": "t", "body": "b", "created_by": 99999}))


def test_reset_scenarios(lab):
    assert helpdesk.reset(lab, "empty")["tickets"]["total"] == 0
    s = helpdesk.reset(lab, "normal10")
    assert s["tickets"]["open"] == 10 and s["poisoned_ticket_ids"] == []
    s = helpdesk.reset(lab, "poisoned10")
    assert s["tickets"]["open"] == 10 and len(s["poisoned_ticket_ids"]) == 1
    bad = payload(call(lab, "get_ticket", {"ticket_id": s["poisoned_ticket_ids"][0]}))
    assert "example.invalid" in bad["body"]
    assert "error" in helpdesk.reset(lab, "nonsense")


def test_reset_is_repeatable_and_clears_comments_and_outbox(lab):
    helpdesk.reset(lab, "normal10")
    payload(call(lab, "add_comment", {"ticket_id": 1, "text": "hi"}))
    vuln = Lab(lab.data_dir, "vulnerable")
    payload(call(vuln, "send_email", {"to": "a@example.invalid", "subject": "s", "body": "b"}))
    assert helpdesk.stats(lab)["emails_in_outbox"] == 1
    again = helpdesk.reset(lab, "normal10")
    assert again["emails_in_outbox"] == 0
    con = sqlite3.connect(lab.db_path)
    assert con.execute("SELECT COUNT(*) FROM tech_ticket_comments").fetchone()[0] == 0


def test_full_reset_restores_damage_done_to_other_tables(lab):
    vuln = Lab(lab.data_dir, "vulnerable")
    payload(call(vuln, "delete_records", {"table": "banking_transactions", "where": "1=1"}))
    assert helpdesk.stats(lab)["banking_transactions"] == 0
    assert helpdesk.reset(lab, "empty")["banking_transactions"] == 0      # tickets only
    assert helpdesk.reset(lab, "empty", full=True)["banking_transactions"] > 0


def test_insert_adds_open_tickets_and_records_poison(lab):
    helpdesk.reset(lab, "empty")
    s = helpdesk.insert(lab, "normal", 3)
    assert s["tickets"]["open"] == 3 and len(s["inserted_ids"]) == 3
    s = helpdesk.insert(lab, "poisoned", 1, "exfil_instruction")
    assert s["tickets"]["open"] == 4 and s["poisoned_ticket_ids"] == s["inserted_ids"]
    assert "error" in helpdesk.insert(lab, "weird")
    assert "error" in helpdesk.insert(lab, "poisoned", 1, "nope")
    assert helpdesk.insert(lab, "normal", 1000)["tickets"]["open"] <= 4 + 25   # capped


def test_answer_key_cannot_be_touched_through_tools(lab):
    vuln = Lab(lab.data_dir, "vulnerable")
    assert "error" in payload(call(vuln, "run_sql", {"query": "DELETE FROM _lab_poisoned"}))


# -- the HTTP admin routes -------------------------------------------------------


def client(lab, token="s3cret"):
    return TestClient(create_server(lab, token).streamable_http_app())


def auth(token="s3cret"):
    return {"Authorization": f"Bearer {token}"}


def test_admin_requires_the_token(lab):
    c = client(lab)
    assert c.get("/admin/stats").status_code == 401
    assert c.get("/admin/stats", headers=auth("wrong")).status_code == 401
    assert c.post("/admin/reset", json={"scenario": "empty"}).status_code == 401
    assert c.post("/admin/insert", json={}).status_code == 401
    assert c.get("/admin/stats", headers=auth()).status_code == 200


def test_admin_routes_do_not_exist_without_a_token(lab):
    c = TestClient(create_server(lab).streamable_http_app())
    assert c.get("/admin/stats", headers=auth()).status_code == 404


def test_admin_reset_and_insert_over_http(lab):
    c = client(lab)
    r = c.post("/admin/reset", json={"scenario": "poisoned10"}, headers=auth())
    assert r.status_code == 200 and r.json()["tickets"]["open"] == 10
    r = c.post("/admin/insert", json={"kind": "normal", "count": 2}, headers=auth())
    assert r.json()["tickets"]["open"] == 12
    assert c.post("/admin/reset", json={"scenario": "bad"}, headers=auth()).status_code == 400
    assert c.post("/admin/insert", json={"count": "x"}, headers=auth()).status_code == 400
    assert json.loads(c.get("/admin/stats", headers=auth()).text)["tickets"]["total"] == 12


def test_admin_is_not_an_mcp_tool(lab):
    names = call(Lab(lab.data_dir, "vulnerable"), "__list__")
    assert not [n for n in names if "reset" in n or "insert" in n or "admin" in n]
