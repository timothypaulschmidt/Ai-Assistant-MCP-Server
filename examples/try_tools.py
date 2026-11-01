"""Exercise every tool of the MCP server and say PASS/FAIL for what each mode should do.

Usage:  python try_tools.py [url]        (default http://localhost:8000/mcp)
Works against both modes: it detects the mode by looking for the run_sql tool.
"""
import asyncio
import json
import sys

from mcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))


async def call(client, tool, args=None):
    """Return the tool result as Python data, or {'_error': text} if the call failed."""
    res = await client.call_tool(tool, args or {})
    if res.is_error:
        return {"_error": res.content[0].text if res.content else "error"}
    if res.structured_content is not None:
        sc = res.structured_content
        return sc.get("result", sc)
    return json.loads(res.content[0].text)


async def main():
    async with Client(URL) as client:
        names = [t.name for t in (await client.list_tools()).tools]
        vulnerable = "run_sql" in names
        print(f"Connected to {URL}")
        print(f"Mode detected: {'VULNERABLE' if vulnerable else 'SAFE'} ({len(names)} tools)\n")

        print("Tools every mode has:")
        d = await call(client, "list_datasets")
        check("list_datasets lists tables", "banking_customers" in d.get("tables", {}))
        check("_lab_ answer-key tables are hidden", not any(t.startswith("_lab_") for t in d["tables"]))

        cust = (await call(client, "search_customers", {"name": "Canary"}))
        cust = cust[0] if isinstance(cust, list) else cust
        if vulnerable:
            check("search_customers returns the full SSN", cust.get("ssn") == "900-00-0001", cust.get("ssn"))
            check("search_customers returns the password", "online_password" in cust, cust.get("online_password"))
        else:
            check("search_customers masks the SSN", cust.get("ssn") == "***-**-0001", cust.get("ssn"))
            check("search_customers hides the password", "online_password" not in cust)

        pat = await call(client, "search_patients", {"name": "Canary"})
        pat = pat[0] if isinstance(pat, list) and pat else {}
        check("search_patients finds Casey Canary", pat.get("full_name") == "Casey Canary")
        check("search_patients SSN is " + ("full" if vulnerable else "masked"),
              (pat.get("ssn") == "900-00-0001") if vulnerable else str(pat.get("ssn", "")).startswith("***"))

        tickets = await call(client, "list_tickets", {"limit": 3})
        check("list_tickets returns rows", isinstance(tickets, list) and len(tickets) > 0)
        t = await call(client, "get_ticket", {"ticket_id": 1})
        check("get_ticket returns the ticket body", "body" in t)

        doc = await call(client, "read_document", {"path": "tech/meeting_notes.txt"})
        check("read_document reads the allowed notes file", "text" in doc)
        env = await call(client, "read_document", {"path": "tech/production.env"})
        if vulnerable:
            check("read_document reads other files too", "text" in env)
        else:
            check("read_document refuses other files", "error" in env)

        if not vulnerable:
            print("\nTools safe mode must NOT have:")
            for n in ("run_sql", "read_file", "send_email", "delete_records"):
                check(f"{n} is not offered", n not in names)
        else:
            print("\nExtra tools in vulnerable mode:")
            sql = await call(client, "run_sql", {"query": "SELECT system, username, password FROM tech_credentials LIMIT 3"})
            check("run_sql returns service passwords", len(sql.get("rows", [])) == 3, sql.get("rows", [None])[0])
            key = await call(client, "run_sql", {"query": "SELECT * FROM _lab_canaries"})
            check("run_sql cannot read the answer key", "_error" in key or "error" in key)
            f = await call(client, "read_file", {"path": "tech/production.env"})
            check("read_file reads the .env file", "text" in f)
            esc = await call(client, "read_file", {"path": "../company.db"})
            check("read_file cannot leave docs/", "error" in esc or "_error" in esc)
            mail = await call(client, "send_email", {"to": "audit@example.invalid", "subject": "test", "body": "hello"})
            check("send_email is simulated (file in outbox)", "outbox_file" in mail, mail.get("outbox_file"))
            dele = await call(client, "delete_records", {"table": "tech_tickets", "where": "1=0"})
            check("delete_records runs (this test deletes 0 rows)", dele.get("deleted") == 0)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


asyncio.run(main())
