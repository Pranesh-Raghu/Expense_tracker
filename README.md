# Expense Tracker

A FastAPI expense tracker with a full OAuth 2.1 authorization server (Dynamic
Client Registration + Client ID Metadata Documents), static API keys, an MCP
server exposing the same expense data as tools for AI agents, and RBAC +
fine-grained authorization (OpenFGA) governing who can see, edit, delete, or
share which expenses.

## Contents

- [Project overview](#project-overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quickstart (Docker)](#quickstart-docker)
- [Configuration](#configuration)
- [Running without Docker](#running-without-docker)
- [Exposing it publicly with ngrok](#exposing-it-publicly-with-ngrok)
- [Authentication](#authentication)
  - [REST API auth](#rest-api-auth)
  - [OAuth 2.1 authorization server](#oauth-21-authorization-server)
  - [Dynamic Client Registration (DCR)](#dynamic-client-registration-dcr)
  - [Client ID Metadata Documents (CIMD)](#client-id-metadata-documents-cimd)
  - [API keys](#api-keys)
- [Authorization: RBAC + fine-grained access (OpenFGA)](#authorization-rbac--fine-grained-access-openfga)
- [MCP server](#mcp-server)
- [REST API reference](#rest-api-reference)
- [Database schema](#database-schema)
- [Testing the OAuth + MCP flow end to end](#testing-the-oauth--mcp-flow-end-to-end)
- [Testing RBAC + sharing end to end](#testing-rbac--sharing-end-to-end)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)

## Project overview

This project tracks personal expenses (create/read/update/delete, category
and transaction-type breakdowns, monthly/yearly/daily/weekly reports) behind
a small FastAPI REST API. On top of that base, it implements:

- **An OAuth 2.1 authorization server** (`oauth/`) - authorization code flow
  with mandatory PKCE, refresh token rotation, revocation, introspection,
  and RFC 8414 / RFC 9728 metadata.
- **Dynamic Client Registration** (RFC 7591) so MCP clients can register
  themselves at runtime instead of being hard-coded into the server.
- **Client ID Metadata Documents (CIMD)** - a zero-registration alternative
  where a client's `client_id` is itself an HTTPS URL serving a JSON
  document that describes the client.
- **Static API keys** as a second credential type for scripts/automation
  where an interactive OAuth redirect isn't practical.
- **An MCP server** (`mcp_server.py`, built on [FastMCP](https://gofastmcp.com))
  exposing the expense data as tools, protected by either credential type.
- **RBAC + fine-grained authorization** (`authz/`, backed by
  [OpenFGA](https://openfga.dev)) - an org-wide `admin` role (RBAC) plus
  per-expense `viewer`/`editor` sharing (FGA), enforced identically whether
  the request comes through the REST API or an MCP tool call.

## Architecture

```
                 ┌───────────────────────────────────────────────┐
                 │                  FastAPI app                  │
                 │                   (main.py)                  │
                 │                                                │
  Browser  ────▶ │  /users, /expenses   REST API (auth.py JWT)   │
                 │  /auth/token         REST login (HS256 JWT)   │
                 │  /auth/api-keys      API key issue/list/revoke│
                 │                                                │
  MCP/OAuth ───▶ │  /oauth/register     DCR            (RFC 7591)│
  client         │  /oauth/authorize    login + consent          │
                 │  /oauth/token        code/refresh exchange    │
                 │  /oauth/revoke       token revocation         │
                 │  /oauth/introspect   token introspection      │
                 │  /.well-known/oauth-authorization-server      │
                 │  /.well-known/jwks.json                       │
                 │                                                │
                 │  /mcp                FastMCP (RS256 JWT or    │
                 │  /.well-known/oauth-protected-resource/mcp    │
                 │                       API key, RFC 9728)      │
                 └──────┬─────────────────────────┬──────────────┘
                        │                         │
                  SQLAlchemy ORM             authz/ (sync httpx)
                        │                         │
                   ┌────▼────┐              ┌─────▼──────┐
                   │  MySQL  │◀─────────────│  OpenFGA   │
                   └─────────┘  (its own db) └────────────┘
```

Two separate token systems exist side by side:

| | REST API session token | OAuth access token |
|---|---|---|
| Issued by | `POST /auth/token` | `POST /oauth/token` |
| Algorithm | HS256 (shared secret) | RS256 (asymmetric, published via JWKS) |
| Audience | implicit (this API) | `resource` (RFC 8707), checked against `aud` |
| Used for | `/users`, `/expenses` | `/mcp` |

Both the REST API and the MCP server also accept a **static API key**
(`eak_...`) as an alternative to either token type.

Authentication (who are you?) and authorization (what can you do?) are
deliberately separate concerns here: whichever of the three credential types
above gets you in the door, every actual permission decision - view, edit,
delete, share an expense - goes through the same `authz/` module, backed by
OpenFGA, regardless of REST or MCP.

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose (bundled with Docker
  Desktop)
- [ngrok](https://ngrok.com/) if you want a public HTTPS URL for testing
  real MCP clients (Claude, etc.) against this server
- Python 3.11+ only if you want to run without Docker

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up -d --build
```

This starts four containers:

- `db` - MySQL 8, with a persisted volume (`db_data`). Also hosts a second
  database (`openfga`), auto-created on first boot via `mysql-init/`.
- `openfga-migrate` - runs once, sets up OpenFGA's schema in that `openfga`
  database, then exits (this is expected - `docker compose ps` will show it
  as `Exited`, not a failure).
- `openfga` - the OpenFGA server (`localhost:8081`), storing the
  authorization model and every RBAC/sharing relationship.
- `app` - the FastAPI app on `http://localhost:8000`, with a persisted
  volume (`oauth_keys`) for the RSA signing key so tokens survive restarts.
  On startup it idempotently bootstraps the OpenFGA store + authorization
  model (safe to restart repeatedly).

Check it's up:

```bash
curl http://localhost:8000/.well-known/oauth-authorization-server
```

Tear down:

```bash
docker compose down          # keep volumes (DB data + signing key)
docker compose down -v       # also delete volumes
```

## Configuration

All configuration is via environment variables, read from `.env` by Docker
Compose (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://root:root@localhost/expensetracker` | SQLAlchemy connection string |
| `MYSQL_ROOT_PASSWORD` | `expensetracker` | MySQL container root password |
| `MYSQL_DATABASE` | `expensetracker` | MySQL container database name |
| `OAUTH_ISSUER` | `http://localhost:8000` | **Must match the public URL clients use to reach this server.** Embedded in every JWT's `iss`/`aud` and in all OAuth metadata documents. |
| `MCP_RESOURCE_URL` | `${OAUTH_ISSUER}/mcp` | The MCP resource identifier (RFC 8707 `resource` / JWT `aud`). Leave blank unless you need to override it. |
| `CIMD_ALLOW_INSECURE_HTTP` | `false` | Allows `http://` (instead of `https://`) Client ID Metadata Document URLs. **Local testing only - never enable in a real deployment.** |
| `REST_JWT_SECRET_KEY` | dev placeholder | HMAC secret for the REST API's own login tokens (`/auth/token`). Set a real secret outside local dev. |
| `SQL_ECHO` | `false` | Set `true` to log all SQL statements. |
| `OPENFGA_API_URL` | `http://openfga:8080` | Where the app reaches OpenFGA. Set by `docker-compose.yml` directly (internal Docker network address) - not normally something you need to change. |
| `INITIAL_ADMIN_USERNAMES` | *(empty)* | Comma-separated usernames to grant the `admin` role on startup. **The only way to create the first admin** - granting admin via `POST /auth/admin/{id}` requires already being one. No-op for usernames that don't exist yet; safe to leave set across restarts. |

`OAUTH_ISSUER` matters more than it looks: every access token's audience
check, every metadata document's URLs, and every CIMD self-certification
check are all derived from it. If you change how the server is reached
(e.g. start an ngrok tunnel), update `OAUTH_ISSUER` and restart the `app`
container - old tokens issued under the previous issuer will stop
validating.

## Running without Docker

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi[standard] sqlalchemy sqlmodel pymysql \
  "python-jose[cryptography]" "passlib[bcrypt]" bcrypt==4.0.1 \
  cryptography httpx python-multipart fastmcp jinja2 uvicorn

export DATABASE_URL="mysql+pymysql://root:yourpassword@localhost/expensetracker"
export OAUTH_ISSUER="http://localhost:8000"

uvicorn main:app --reload
```

You need a MySQL instance reachable at `DATABASE_URL` yourself (Docker
Compose provides one automatically; without Docker, run one locally or
point at any MySQL-compatible server). You also need an OpenFGA instance
reachable at `OPENFGA_API_URL` (defaults to `http://localhost:8081` outside
Docker) - the quickest way is still via Docker even if the app itself runs
bare:

```bash
docker run -p 8081:8080 -p 8082:8081 openfga/openfga run --datastore-engine memory
```

(`memory` here means the authorization model/tuples don't survive a
restart - fine for local dev without Docker Compose, not for anything you
want to persist.)

`bcrypt==4.0.1` is pinned deliberately - `passlib` 1.7.4's internal bcrypt
self-test breaks against `bcrypt`'s 4.1+ API changes and raises `ValueError:
password cannot be longer than 72 bytes` on every hash/verify call. See
[Troubleshooting](#troubleshooting).

## Exposing it publicly with ngrok

MCP clients (Claude, other agents) need a real HTTPS URL to discover and
authenticate against this server - `localhost` won't work for them.

```bash
ngrok http 8000
```

Copy the `https://...ngrok-free.app` URL ngrok prints, then:

```bash
# .env
OAUTH_ISSUER=https://your-subdomain.ngrok-free.app
```

```bash
docker compose up -d   # restart app with the new issuer
```

Every endpoint - metadata documents, JWKS, the `/mcp` resource identifier -
now reflects the public URL. Point an MCP client at
`https://your-subdomain.ngrok-free.app/mcp` and it will discover the
authorization server automatically via the `WWW-Authenticate` header /
protected resource metadata.

## Authentication

### REST API auth

`POST /auth/token` (OAuth2 password grant shape, but not part of the OAuth
2.1 authorization server below - this is a simple login endpoint) issues an
HS256 JWT for use against `/users` and `/expenses`:

```bash
curl -X POST http://localhost:8000/auth/token \
  -d username=alice -d password=yourpassword
# {"access_token": "...", "token_type": "bearer"}

curl http://localhost:8000/expenses/ \
  -H "Authorization: Bearer <access_token>"
```

It also accepts an [API key](#api-keys) in place of the JWT.

### OAuth 2.1 authorization server

Implements the authorization code flow with PKCE (S256 only - OAuth 2.1
drops support for the implicit grant and plain-text PKCE), refresh token
rotation, revocation, and introspection.

| Endpoint | Purpose |
|---|---|
| `GET /.well-known/oauth-authorization-server` | RFC 8414 metadata |
| `GET /.well-known/jwks.json` | Public key(s) for verifying access tokens |
| `POST /oauth/register` | Dynamic Client Registration (RFC 7591) |
| `GET /oauth/authorize` | Login + consent screen |
| `POST /oauth/authorize` | Submits login/consent, redirects with a code |
| `POST /oauth/token` | Exchanges a code or refresh token for an access token |
| `POST /oauth/revoke` | Revokes an access or refresh token |
| `POST /oauth/introspect` | RFC 7662 token introspection |

Access tokens are RS256-signed JWTs, 15 minutes TTL, with claims:

```json
{
  "iss": "<OAUTH_ISSUER>",
  "sub": "<user id>",
  "username": "<username>",
  "aud": "<resource, defaults to MCP_RESOURCE_URL>",
  "client_id": "<the client's client_id>",
  "scope": "<requested scope, if any>",
  "iat": 0, "exp": 0, "jti": "<unique token id>"
}
```

Refresh tokens (30 day TTL) rotate on every use: the old one is revoked as
soon as a new pair is issued, so a captured-and-replayed refresh token stops
working the moment the legitimate client refreshes.

### Dynamic Client Registration (DCR)

```bash
curl -X POST http://localhost:8000/oauth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "redirect_uris": ["http://localhost:9000/callback"],
    "client_name": "my-mcp-client"
  }'
```

Returns a `client_id` (and a `client_secret` only if you request
`"token_endpoint_auth_method": "client_secret_basic"` - the default,
`"none"`, is for public/PKCE-only clients, which covers essentially all MCP
clients).

### Client ID Metadata Documents (CIMD)

CIMD is the zero-registration alternative: instead of calling
`/oauth/register`, a client's `client_id` **is** an HTTPS URL. That URL must
serve a JSON document, in the same shape as a DCR response, that
self-certifies by naming itself:

```json
{
  "client_id": "https://myapp.example.com/oauth-client.json",
  "redirect_uris": ["https://myapp.example.com/callback"],
  "client_name": "My App"
}
```

When this server sees a `client_id` that looks like a URL, it fetches that
URL and checks the document's own `client_id` field matches exactly - this
self-referential binding is what stops one client from impersonating
another: anyone can publish a document claiming any `redirect_uris` they
want, but only the actual owner of that URL can make it serve a document
that points back at itself. Documents are cached for 10 minutes
(`oauth/cimd.py`).

CIMD client_ids must be `https://` in a real deployment. For local testing
without TLS, set `CIMD_ALLOW_INSECURE_HTTP=true` - never enable this outside
local development.

### API keys

A second, static, long-lived credential type for scripts and automation
where an interactive `/oauth/authorize` redirect isn't practical. Accepted
anywhere a Bearer token is (`/users`, `/expenses`, `/auth/*`, and `/mcp`).

```bash
# get a REST session token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d username=alice -d password=yourpassword | jq -r .access_token)

# create an API key
curl -X POST http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name": "my automation script"}'
# {"api_key": "eak_...", "name": "my automation script"}

# list keys (only shows id prefix + metadata, never the raw key again)
curl http://localhost:8000/auth/api-keys -H "Authorization: Bearer $TOKEN"

# revoke one
curl -X DELETE http://localhost:8000/auth/api-keys/<key_id> \
  -H "Authorization: Bearer $TOKEN"
```

The raw key (`eak_...`) is shown exactly once, at creation time - only its
hash is stored. Use it directly as a Bearer token:

```bash
curl http://localhost:8000/expenses/ -H "Authorization: Bearer eak_..."
```

## Authorization: RBAC + fine-grained access (OpenFGA)

Authentication (the sections above) answers "who are you?" Authorization -
"what can you actually do?" - is a completely separate layer, backed by
[OpenFGA](https://openfga.dev), a Zanzibar-style relationship-based
authorization system. All logic lives in `authz/`; nothing else in the app
talks to OpenFGA directly.

**Two kinds of access, on top of each other:**

- **RBAC (a role):** every user is a member of one fixed organization
  (`organization:main` - this app has no multi-tenancy concept, so a single
  org is enough to get a real admin role). An **admin** can view, edit,
  delete, and share *any* expense, without owning it or being shared on it.
- **FGA (a per-resource grant):** independent of role, the owner of a
  specific expense can share that one expense with one other specific user,
  as a **viewer** (read-only) or **editor** (can also update it).

Every permission check resolves to one of four **computed relations** on an
expense - `can_view`, `can_edit`, `can_delete`, `can_share` - each a union of
"you own it," "you were granted this relation," or "you're an org admin."
`authz/model.py` has the full model; the shape is:

```
organization:main
  admin:  [user, user, ...]           <- the RBAC role
  member: admin ∪ (direct members)

expense:<id>
  parent_org: organization:main
  owner:      [user]                  <- set once, at creation
  viewer:     [user, user, ...]       <- set via sharing
  editor:     [user, user, ...]       <- set via sharing
  can_view:   viewer ∪ owner ∪ editor ∪ (admin of parent_org)
  can_edit:   owner ∪ editor ∪ (admin of parent_org)
  can_delete: owner ∪ (admin of parent_org)
  can_share:  owner ∪ (admin of parent_org)
```

**Enforcement points** (`services/expense_services.py`): every expense
operation calls the matching `authz.can_*` check and raises `403` if it
fails, before touching the database. Creating an expense writes an `owner` +
`parent_org` tuple; deleting one removes every tuple referencing it (no
orphaned permissions left behind). Listing expenses (`GET /expenses/`) uses
OpenFGA's `ListObjects` to compute the exact set of visible expense ids -
own, shared, or admin-visible - then fetches only those rows.

This is enforced identically for MCP tool calls (`mcp_server.py`) - they
call the exact same `expense_services.*` functions, so an agent acting via
MCP is bound by the same rules as a human via REST. `share_expense`,
`unshare_expense`, and `my_permissions` are available as MCP tools too.

**Managing roles and sharing:**

```bash
# who am I, and am I an admin?
curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"

# grant/revoke admin (caller must already be admin)
curl -X POST   http://localhost:8000/auth/admin/<user_id> -H "Authorization: Bearer $ADMIN_TOKEN"
curl -X DELETE http://localhost:8000/auth/admin/<user_id> -H "Authorization: Bearer $ADMIN_TOKEN"

# share/unshare a specific expense (caller must own it, or be admin)
curl -X POST http://localhost:8000/expenses/<expense_id>/share \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_user_id": 5, "relation": "viewer"}'   # or "editor"

curl -X DELETE http://localhost:8000/expenses/<expense_id>/share/<target_user_id> \
  -H "Authorization: Bearer $TOKEN"
```

**The first admin** has to come from somewhere other than the endpoint
above (granting admin requires already being one) - set
`INITIAL_ADMIN_USERNAMES=<username>` in `.env` and restart the `app`
container; see [Configuration](#configuration).

## MCP server

Built on [FastMCP](https://gofastmcp.com), mounted at `/mcp`
(`mcp_server.py`). Every call requires a Bearer token - either an OAuth
access token or an API key, verified by `oauth/token_verifier.py`'s
`HybridTokenVerifier`. A request with no or an invalid token gets:

```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="<OAUTH_ISSUER>/.well-known/oauth-protected-resource/mcp"
```

so a compliant MCP client can discover this server's authorization server
automatically (RFC 9728).

**Available tools:**

| Tool | Description |
|---|---|
| `list_expenses` | List every expense the current user can view - own, shared, or admin-visible |
| `get_expense(expense_id)` | Get a single expense (requires `can_view`) |
| `add_expense(amount, category, transaction)` | Record a new expense (you become its owner) |
| `update_expense(expense_id, ...)` | Update fields on an existing expense (requires `can_edit`) |
| `delete_expense(expense_id)` | Delete an expense (requires `can_delete`) |
| `share_expense(expense_id, target_user_id, relation)` | Share an expense as `"viewer"` or `"editor"` (requires `can_share`) |
| `unshare_expense(expense_id, target_user_id)` | Remove another user's shared access |
| `my_permissions` | Report whether the current user has the org admin role |
| `list_categories` | Valid expense categories |
| `list_transaction_types` | Valid transaction types |
| `monthly_report(year, month)` | All of *your own* expenses in a month |
| `monthly_total(year, month)` | Total amount for a month (your own only) |
| `yearly_report(year)` | All of *your own* expenses in a year |
| `yearly_total(year)` | Total amount for a year (your own only) |

(The REST API additionally exposes daily/weekly reports - a representative
subset was chosen for MCP tools rather than a 1:1 mirror. The report/total
tools are intentionally **not** RBAC/FGA-aware - they remain self-only,
unlike the CRUD tools above; see
[Authorization](#authorization-rbac--fine-grained-access-openfga).)

## REST API reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/users/` | none | Create a user |
| `GET` | `/users/` | none | List users |
| `GET` | `/users/{id}` | none | Get a user |
| `PUT` | `/users/{id}` | none | Replace a user |
| `PATCH` | `/users/{id}` | none | Partially update a user |
| `DELETE` | `/users/{id}` | none | Delete a user |
| `POST` | `/auth/token` | none | Log in, get a REST session JWT |
| `POST` | `/auth/api-keys` | Bearer | Create an API key |
| `GET` | `/auth/api-keys` | Bearer | List your API keys |
| `DELETE` | `/auth/api-keys/{key_id}` | Bearer | Revoke an API key |
| `GET` | `/auth/me` | Bearer | Current user + `is_admin` |
| `POST` | `/auth/admin/{user_id}` | Bearer (admin) | Grant the admin role |
| `DELETE` | `/auth/admin/{user_id}` | Bearer (admin) | Revoke the admin role |
| `GET` `POST` `PUT` `DELETE` | `/expenses/...` | Bearer | Full expense CRUD (authz-checked) + category/transaction/report filters |
| `POST` | `/expenses/{id}/share` | Bearer (owner/admin) | Share an expense as viewer/editor |
| `DELETE` | `/expenses/{id}/share/{user_id}` | Bearer (owner/admin) | Remove a user's shared access |

Interactive docs: `http://localhost:8000/docs`.

> The `/users` endpoints have no auth guard in the current code (pre-existing
> in this project, not added as part of the OAuth/MCP work) - anyone can
> create, list, or delete a user. Don't run this outside a trusted local/demo
> environment without adding one.

## Database schema

### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PRIMARY KEY |
| `username` | VARCHAR(255) | UNIQUE, INDEX |
| `password` | VARCHAR(255) | bcrypt hash |
| `is_active` | BOOLEAN | default `true` |

### `expenses`

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PRIMARY KEY |
| `amount` | FLOAT | |
| `category` | ENUM | `FOOD`, `TRAVEL`, `ENTERTAINMENT`, `SHOPPING`, `OTHERS` |
| `transaction` | ENUM | `DEBIT`, `CREDIT` |
| `time` | DATETIME | default now |
| `user_id` | INT | FOREIGN KEY → `users.id` |

### OAuth tables (`oauth/models.py`)

| Table | Purpose |
|---|---|
| `oauth_clients` | DCR-registered clients (CIMD clients never get a row - their identity lives at their `client_id` URL) |
| `oauth_authorization_codes` | Single-use authorization codes with their PKCE challenge, 5 minute TTL |
| `oauth_refresh_tokens` | Hashed refresh tokens, rotated on use, 30 day TTL |
| `oauth_revoked_access_tokens` | JTIs of access tokens revoked before natural expiry |
| `api_keys` | Hashed static API keys |

Access tokens themselves are **not** stored - they're self-contained,
RS256-signed JWTs, verified against the public key in
`/.well-known/jwks.json` plus the revocation table above.

### OpenFGA (its own MySQL database, not the `expensetracker` one)

RBAC roles and expense sharing live entirely in OpenFGA's own `openfga`
database (auto-created in the same MySQL container, see
`mysql-init/01-create-openfga-db.sql`) - **not** as columns/tables in
`expensetracker`. There is no `role` column on `users` and no
`expense_shares` table; every permission fact is a relationship tuple:

| Tuple shape | Meaning |
|---|---|
| `user:<id> admin organization:main` | that user has the RBAC admin role |
| `user:<id> owner expense:<id>` | written automatically when an expense is created |
| `organization:main parent_org expense:<id>` | written automatically when an expense is created - links it to the org for the admin-role check |
| `user:<id> viewer expense:<id>` | written by `POST /expenses/{id}/share` with `"relation": "viewer"` |
| `user:<id> editor expense:<id>` | same, with `"relation": "editor"` |

Inspect them directly against OpenFGA's own API (`localhost:8081`, no auth
by default - **don't expose this port outside local dev**):

```bash
STORE_ID=$(curl -s http://localhost:8081/stores | python3 -c "import sys,json;print(json.load(sys.stdin)['stores'][0]['id'])")
curl -X POST http://localhost:8081/stores/$STORE_ID/read -H 'Content-Type: application/json' \
  -d '{"tuple_key": {"object": "expense:1"}}'
```

## Testing the OAuth + MCP flow end to end

A full manual walkthrough, in order:

```bash
# 1. create a user
curl -X POST http://localhost:8000/users/ -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"correcthorsebatterystaple"}'

# 2. register a client (DCR)
curl -X POST http://localhost:8000/oauth/register -H 'Content-Type: application/json' \
  -d '{"redirect_uris":["http://localhost:9000/callback"],"client_name":"test-client"}'
# -> save client_id

# 3. generate a PKCE pair
VERIFIER=$(openssl rand -base64 96 | tr -d '=+/\n' | cut -c1-64)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=')

# 4. open in a browser, log in, approve
open "http://localhost:8000/oauth/authorize?response_type=code&client_id=<client_id>&redirect_uri=http://localhost:9000/callback&code_challenge=$CHALLENGE&code_challenge_method=S256&state=xyz"
# -> redirects to http://localhost:9000/callback?code=...&state=xyz (that URL need not resolve - just copy `code`)

# 5. exchange the code for tokens
curl -X POST http://localhost:8000/oauth/token \
  -d grant_type=authorization_code -d code=<code> \
  -d redirect_uri=http://localhost:9000/callback -d code_verifier=$VERIFIER \
  -d client_id=<client_id>
# -> {"access_token": "...", "refresh_token": "...", ...}

# 6. call an MCP tool
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# -> note the mcp-session-id response header, then:

curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer <access_token>" -H "mcp-session-id: <session_id>" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add_expense","arguments":{"amount":42.5,"category":"FOOD","transaction":"DEBIT"}}}'
```

To test **CIMD** instead of DCR: host a JSON file (any static file server)
containing `{"client_id": "<that exact URL>", "redirect_uris": [...]}`, and
use that URL as `client_id` in steps 4-5 instead of a DCR-issued one (set
`CIMD_ALLOW_INSECURE_HTTP=true` first if it's served over plain `http://`).

To test **API keys** instead of the OAuth dance: skip straight to step 6,
using an `eak_...` key (see [API keys](#api-keys)) as the Bearer token.

## Testing RBAC + sharing end to end

Needs three users and a REST session token each (`POST /auth/token`) -
substitute your own usernames/passwords:

```bash
# 1. create three users, get a token for each
for u in owner_user other_user admin_user; do
  curl -X POST http://localhost:8000/users/ -H 'Content-Type: application/json' \
    -d "{\"username\":\"$u\",\"password\":\"password123\"}"
done

OWNER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/token -d username=owner_user -d password=password123 | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
OTHER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/token -d username=other_user -d password=password123 | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. owner_user creates an expense
EXPENSE=$(curl -s -X POST http://localhost:8000/expenses/ -H "Authorization: Bearer $OWNER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"amount": 50, "category": "FOOD", "transaction": "DEBIT", "user_id": 0}')
EXPENSE_ID=$(echo "$EXPENSE" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 3. other_user has zero access - confirm the 403
curl -i http://localhost:8000/expenses/$EXPENSE_ID -H "Authorization: Bearer $OTHER_TOKEN"

# 4. owner_user shares it as viewer
curl -X POST http://localhost:8000/expenses/$EXPENSE_ID/share -H "Authorization: Bearer $OWNER_TOKEN" -H 'Content-Type: application/json' \
  -d "{\"target_user_id\": <other_user's id>, \"relation\": \"viewer\"}"

# 5. other_user can now view it, but still can't edit or delete it
curl http://localhost:8000/expenses/$EXPENSE_ID -H "Authorization: Bearer $OTHER_TOKEN"
curl -i -X DELETE http://localhost:8000/expenses/$EXPENSE_ID -H "Authorization: Bearer $OTHER_TOKEN"   # -> 403

# 6. promote admin_user to admin (requires an existing admin - use
#    INITIAL_ADMIN_USERNAMES for the very first one) and confirm they can act
#    on owner_user's expense despite no ownership or share at all
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/token -d username=admin_user -d password=password123 | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl http://localhost:8000/expenses/$EXPENSE_ID -H "Authorization: Bearer $ADMIN_TOKEN"           # -> 200
curl -X DELETE http://localhost:8000/expenses/$EXPENSE_ID -H "Authorization: Bearer $ADMIN_TOKEN"  # -> 200
```

To confirm cleanup worked, read the expense's tuples from OpenFGA directly
(see [OpenFGA](#openfga-its-own-mysql-database-not-the-expensetracker-one))
- after step 6's delete, it should return an empty tuple list.

The same sequence works identically through MCP tools
(`share_expense`/`unshare_expense`/`get_expense`/`delete_expense`) instead
of the REST endpoints above - swap the REST calls for
`tools/call` with the matching tool name and arguments.

## Project structure

```
Expense_tracker/
├── main.py                    # FastAPI app: wires REST, OAuth, and MCP together
├── auth.py                    # REST API login (/auth/token) + API key management
├── database.py                # SQLAlchemy engine/session, DATABASE_URL from env
├── mcp_server.py               # FastMCP server + tool definitions, mounted at /mcp
│
├── models/
│   ├── user_model.py           # users table + auth queries
│   └── expense_model.py        # expenses table + query methods
├── schemas/                    # Pydantic request/response models
├── services/                   # business logic called by controllers/tools
├── controller/                 # REST API routers (/users, /expenses)
├── validators/                 # input validation helpers
├── enums/                      # ExpenseCategory, TransactionType
│
├── oauth/                      # the OAuth 2.1 authorization server
│   ├── router.py                # /oauth/*, /.well-known/* endpoints
│   ├── service.py                # token issuance/validation, API keys, business logic
│   ├── models.py                  # oauth_clients, authorization_codes, refresh_tokens, api_keys
│   ├── schemas.py                  # DCR / token / API key Pydantic models
│   ├── cimd.py                      # Client ID Metadata Document fetch + validation
│   ├── pkce.py                       # PKCE S256 verification
│   ├── keys.py                        # RSA signing key generation/persistence, JWKS
│   └── token_verifier.py               # HybridTokenVerifier (OAuth JWT or API key) for FastMCP
│
├── authz/                      # RBAC + fine-grained authorization (OpenFGA)
│   ├── model.py                 # the authorization model (types/relations), as JSON
│   ├── client.py                  # sync OpenFGA HTTP client + idempotent store/model bootstrap
│   └── service.py                  # can_view/can_edit/can_delete/can_share, sharing, admin role management
│
├── templates/
│   ├── home.html                # REST API landing page
│   └── login.html                # OAuth authorize login + consent screen
├── static/                     # CSS/JS for the templates
│
├── mysql-init/                 # SQL run once on a FRESH MySQL volume only
│   └── 01-create-openfga-db.sql  # creates the separate `openfga` database
├── Dockerfile                  # app image
├── docker-compose.yml           # app + MySQL + OpenFGA, with persisted volumes
├── .env.example                  # documented environment variables
└── keys/                          # persisted RSA signing key (docker volume, gitignored)
```

## Troubleshooting

<details>
<summary><code>sqlalchemy.exc.CompileError: VARCHAR requires a length on dialect mysql</code></summary>

A SQLAlchemy `String` column has no length, which SQLite tolerates but MySQL
rejects at `CREATE TABLE`. Give it one, e.g. `String(255)`.
</details>

<details>
<summary><code>ValueError: password cannot be longer than 72 bytes</code> from passlib/bcrypt</summary>

`passlib` 1.7.4 runs an internal self-test against the installed `bcrypt`
version; `bcrypt` 4.1+ changed its API in a way that breaks that self-test
and makes every hash/verify call fail, even for short passwords. Pin
`bcrypt==4.0.1` (already done in `pyproject.toml`/`Dockerfile`).
</details>

<details>
<summary><code>TypeError: can't compare offset-naive and offset-aware datetimes</code></summary>

MySQL's `DATETIME` type has no timezone concept - a timezone-aware Python
`datetime` written to it comes back naive on read. All timestamps in
`oauth/service.py` and `oauth/models.py` are therefore generated as
naive-but-UTC (`datetime.now(timezone.utc).replace(tzinfo=None)`) for
consistent comparison. If you add a new timestamp column, follow the same
pattern.
</details>

<details>
<summary>Protected resource metadata 404s, or the resource URL looks doubled (<code>/mcp/mcp</code>)</summary>

`RemoteAuthProvider`'s `base_url` and `mcp.http_app(path="/mcp")`'s path are
combined to form the resource URL - don't also pass a `resource_base_url`
that already includes `/mcp`, or it doubles up.
</details>

<details>
<summary>Tokens stop validating after starting/changing an ngrok tunnel</summary>

`OAUTH_ISSUER` is embedded in every JWT's `iss`/`aud` claims. Tokens issued
under one issuer value will fail `aud`/`iss` validation after you change
`OAUTH_ISSUER` and restart - log in again to get fresh tokens.
</details>

<details>
<summary><code>Error: failed to initialize database connection: Unknown database 'openfga'</code></summary>

`mysql-init/*.sql` only runs on a **fresh** MySQL data volume (first-ever
container start) - if you already had a `db_data` volume from before adding
OpenFGA, the init script never fires. Create the database manually once:

```bash
docker exec expense_tracker-db-1 mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS openfga;"
docker compose up -d openfga-migrate openfga
```
</details>

<details>
<summary>OpenFGA writes/deletes fail with "tuple to be written already existed" or "did not exist"</summary>

OpenFGA has no upsert - writing a tuple that's already there, or deleting
one that isn't, both return `400 write_failed_due_to_invalid_input`. Every
write/delete in `authz/service.py` reads current state first (`can_*`
checks or `read_tuples`) and only sends the writes/deletes actually needed -
follow that pattern for anything new (see `share_expense`'s viewer↔editor
swap logic for the trickiest case).
</details>

<details>
<summary>A env var change in <code>.env</code> doesn't seem to take effect after <code>docker compose up -d</code></summary>

Two separate ways this bites: (1) the variable was added to `.env.example`
but never actually referenced in `docker-compose.yml`'s `environment:`
block for that service - compose does not auto-forward every `.env` key
into a container, only ones explicitly listed with `${VAR}`. (2) even with
it referenced, `docker compose up -d` alone sometimes doesn't detect an
env-only change as needing a recreate. `docker compose up -d --force-recreate <service>`
fixes case 2; `docker exec <container> env | grep VAR` confirms whether
either happened at all.
</details>

<details>
<summary>Partial update wipes out other fields to <code>NULL</code> (e.g. updating only <code>amount</code> also clears <code>category</code>)</summary>

Pydantic's `.model_dump()` includes every field, `None` or not - a downstream
`if 'category' in expense_data:` check (in `models/expense_model.py`) is
then always true regardless of whether the caller actually provided it. Use
`.model_dump(exclude_none=True)` when only present fields should be applied
(fixed in `services/expense_services.py:update_expense`).
</details>

## Security notes

This is a reference implementation for learning/demoing the MCP
authorization spec (OAuth 2.1 + DCR + CIMD), not a hardened production
authorization server. Before using anything like this in production,
consider:

- Rate limiting on `/oauth/token`, `/oauth/authorize`, and `/auth/token` (none implemented here)
- Locking down `/users/*`, which currently has no auth guard at all
- A real secrets manager instead of `.env` files for `OAUTH_ISSUER`-adjacent
  values and `REST_JWT_SECRET_KEY`
- Consent screen improvements (per-scope approval, not all-or-nothing)
- Structured audit logging of authorization grants and token issuance
- CIMD document fetches are made from the server to a client-supplied URL -
  this is SSRF-shaped by design (that's inherent to CIMD, not a bug), so if
  you deploy this somewhere with internal network access, make sure
  outbound requests from the app can't reach internal-only services
- **OpenFGA's HTTP API (`localhost:8081`) has authentication disabled** -
  anyone who can reach that port can read or write any permission tuple
  directly, bypassing the app entirely. Fine for local dev; never expose
  that port beyond the Docker network in a real deployment (enable OpenFGA's
  own auth, or simply don't publish the port)
- The report/total MCP tools and REST endpoints (`monthly_report`,
  `yearly_total`, etc.) are intentionally **not** authz-aware - they remain
  strictly self-only, unlike the CRUD operations. Extending sharing to
  aggregate reports (e.g. "let an editor see a shared expense's contribution
  to my monthly total") is a deliberately unscoped, more nuanced feature
