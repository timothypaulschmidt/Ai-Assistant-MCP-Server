# AI Assistant MCP Server

An **intentionally vulnerable** MCP server and a fake company's data, built for learning AI
security: how a chatbot under prompt-injection attack can be tricked into leaking sensitive
data, and how a well-meaning agent with powerful tools can cause accidental harm.

> **Everything here is synthetic.** No real person, patient, customer or card is in this data.
> The server has deliberately unsafe tools in `vulnerable` mode. Do not point it at real data, and do
> not expose it to the internet.

The client side lives in the [AI-Assistant](https://github.com/timothypaulschmidt/ai-assistant)
repository. This repo is the target it connects to.

## Status

| Step | State |
|---|---|
| 1. Synthetic data generator and SQLite database | **done** (this repo) |
| 2. MCP server with safe and risky tools | **done** (this repo) |
| 3. Tool-calling loop in the AI Assistant | next |
| 4. Container image and k3s manifests | **done** (see `deploy/README.md`) |

## The data

One SQLite database (`company.db`) plus a `docs/` folder, built from a seed so it is identical
every time. Four industries, each with the fields attackers go for:

| Industry | Tables | Sensitive fields |
|---|---|---|
| Healthcare | patients, visits, prescriptions | SSN, DOB, insurance ID, diagnoses |
| Banking | customers, accounts, cards, transactions | SSN, plain-text passwords, card number, CVV, PIN |
| Manufacturing | suppliers, parts | supplier bank details, trade-secret parts |
| Technology / IT | employees, credentials, tickets | salaries, SSN, service passwords, API keys |

`docs/` holds files in other formats: text discharge summaries, a wire-instruction note, a
trade-secret formula, a VPN runbook with a password, a `.env` file with fake keys, an HR CSV,
and an Excel payroll workbook.

### Why the data is safe

* **SSNs** use area numbers 900-999, which are never issued.
* **Card numbers** pass the Luhn check but use test-style prefixes and random digits.
* **Phones** use the fictional 555-01xx range; **emails** use `example.com`.
* **API keys** start with `FAKE-KEY-`, so they can never match a real provider's key format.
* A test fails if anything resembling a real provider secret appears in the output.

### Canaries and poisoned records (the demo answer key)

* **Canaries** are fixed fake values (a "Casey Canary" patient and customer, one SSN, one card,
  one password, one API key). Search model replies, logs or FortiAIGate events for them to prove
  exactly what leaked. They are listed in the `_lab_canaries` table.
* **Poisoned records** hide a prompt-injection payload in a ticket, a visit note or a
  transaction description, and in `docs/tech/meeting_notes.txt`. A model that reads one through
  a tool may treat it as an instruction. They are listed in `_lab_poisoned`. The payloads are
  harmless: they only ask for data to be sent to `audit@example.invalid`, which cannot resolve.

Tables starting with `_lab_` are the answer key and should not be exposed by the server.

## Run it

Needs Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m ai_assistant_mcp_server.generate --out data --seed 1337
pytest
```

`--scale 0.2` makes a smaller dataset. Running the generator again **resets** the lab: it
deletes and rebuilds `data/company.db` from the seed.

Generated data is never committed (`data/` and `*.db` are in `.gitignore`).

## The MCP server

```bash
ai-assistant-mcp-server --mode safe                 # stdio, for a local MCP client
ai-assistant-mcp-server --mode vulnerable --transport streamable-http --port 8000
```

It generates `data/` on first start if the database is missing; `--regenerate` rebuilds it
(this is how you reset the lab after a destructive demo). Env vars `MCP_MODE` and
`LAB_DATA_DIR` do the same as the flags. HTTP endpoint: `http://<host>:8000/mcp`.

| Tool | safe | vulnerable |
|---|---|---|
| `list_datasets`, `list_tickets`, `get_ticket` | yes | yes |
| `search_customers`, `search_patients` | SSN masked, no passwords, max 10 rows | everything unmasked |
| `read_document` | `tech/meeting_notes.txt` only | any document |
| `run_sql` | - | any SQL, reads and writes |
| `read_file` | - | any file under `docs/` (text, csv, xlsx) |
| `send_email` | - | **simulated**: writes JSON to `data/outbox/` |
| `delete_records` | - | deletes rows, no confirmation |

Guard rails that remain even in `vulnerable` mode: nothing leaves the machine, `read_file`
cannot leave `docs/`, and the `_lab_` answer-key tables are blocked.

Note that safe mode is not injection-proof: `get_ticket` still returns a poisoned ticket
body to the model. That contrast is the lesson.

### Check every tool

With the server running in either mode, in a second terminal:

```bash
python examples/try_tools.py            # default http://localhost:8000/mcp
```

It detects the mode and prints PASS/FAIL for what that mode should and should not allow.

### See the answer key

```bash
python examples/show_poisoned.py            # or pass the data folder as an argument
```

Lists which records hold an injection payload (and of which kind) and the canary values, so
you know which ticket or transaction to point a model at.
