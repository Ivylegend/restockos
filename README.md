# RestockOS

RestockOS is an autonomous procurement workspace for small retailers. It detects low stock, requests three supplier offers, ranks price, delivery and reliability, negotiates within policy, and prepares a purchase order. Public users can explore a seeded sandbox. Each Testnet business workspace is wallet-owned and has isolated operational data. Real Testnet payments are checked by the NEAR policy contract and require the workspace owner's wallet confirmation.

Built for the **NEAR Hackathon 2026 · Autonomous Business** track. The hackathon submission remains pending.

## Architecture

- **Web:** Next.js App Router, TypeScript, Tailwind, TanStack Query and local shadcn-style components. The public landing and seeded dashboard work without authentication; owner and admin actions require a wallet session or the existing admin token.
- **API:** FastAPI, Pydantic, SQLAlchemy 2, Alembic and PostgreSQL. A signed NEP-413 challenge authenticates Testnet account ownership. Every business record carries a `workspace_id`; SQLAlchemy query criteria scope ORM reads and writes to the signed session's workspace.
- **Agent:** Deterministic procurement scoring with optional OpenAI-compatible quote recommendation. Supplier text is not sent to the LLM. Public sandbox runs are deterministic, rate-limited and marked `simulated`; they cannot invoke any signer or contract.
- **Chain:** NEAR Testnet policy contract written with `near-sdk-js`. Each business can deploy `policy.<owner-account>` with an owner-approved wallet transaction. The contract enforces the supplier list, per-order cap, budget, pause, and replay protection. A user wallet confirms a live purchase. The original admin workspace retains its server-side restricted signer.
- **Signing:** `scripts/sign-purchase.mjs` only accepts a function-call key scoped to `execute_purchase` on the configured contract. Its secret is read from the API process environment and never returned to the browser. `scripts/verify-nep413.mjs` verifies wallet sign-in with `near-api-js` v7 and the configured RPC.

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and [operations](docs/operations.md).

## Stack

Next.js 16, React 19, TypeScript, Tailwind CSS 4, TanStack Query 5, `@hot-labs/near-connect` 0.12, FastAPI, Python 3.12+, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL 17, `near-api-js` 7.5 and `near-sdk-js` 2.0.

## Local installation

Requirements: Node 24, Python 3.12 or newer, Docker with Compose, and a PostgreSQL database. The contract build also needs the pinned near-sdk-js toolchain.

```sh
cp .env.example .env
openssl rand -hex 32 # use one fresh value for OWNER_TOKEN
openssl rand -hex 32 # use a different value for SESSION_SECRET
```

Put the generated values into `.env`. Do not use example values for a hosted deployment. Then install and start PostgreSQL:

```sh
npm ci --ignore-scripts
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
docker compose up -d db
```

Apply migrations, seed the admin/demo workspace, and start FastAPI:

```sh
cd apps/api
../../.venv/bin/alembic upgrade head
../../.venv/bin/python -m restock.seed
../../.venv/bin/uvicorn restock.main:app --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```sh
npm run dev -w @restockos/web
```

Open [http://localhost:3000](http://localhost:3000). The catalog starts with 16 electronics products, three stockout risks and three seeded suppliers. Set `PUBLIC_DEMO=true` only when you intend to expose the seeded workspace. The landing page remains visible when public data access is disabled.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL; production uses PostgreSQL, not SQLite. |
| `OWNER_TOKEN` | Preserved admin bearer token. Keep it private. |
| `SESSION_SECRET` | HMAC signing secret for wallet sessions. If unset, the API falls back to `OWNER_TOKEN`; set a separate random value in production. |
| `ADMIN_ACCOUNT_IDS` | JSON array of NEAR Testnet account IDs allowed to receive the admin role after wallet signature verification, for example `["ops.testnet"]`. |
| `AUTH_RECIPIENT` | NEP-413 audience string to sign. Use the exact hosted site hostname in production. |
| `AUTOMATION_TOKEN` | Optional bearer token for trusted scheduled agent runs. |
| `WEB_ORIGIN` | Allowed browser origin for CORS. |
| `NEXT_PUBLIC_API_URL` | API URL embedded in the web build; use `/api` behind the included same-origin proxy. |
| `DEMO_ENABLED` | Enables the public sandbox-run path and demo reset. Sandbox orders are explicitly simulated. |
| `PUBLIC_DEMO` | Allows anonymous reads from the seeded `admin-demo` workspace when `DEMO_ENABLED=true`. |
| `SCAN_INTERVAL_SECONDS` | Optional background scan interval. Zero disables scheduled scans. |
| `NEAR_RPC_URL` | NEAR Testnet RPC URL. The API checks the RPC chain before wallet verification and transaction verification. |
| `NEAR_CONTRACT_ID` | Admin workspace Testnet policy contract. |
| `NEAR_AGENT_ID` | Admin server signer's account ID. |
| `NEAR_AGENT_PRIVATE_KEY` | Admin API only. Restricted function-call key for `execute_purchase` on `NEAR_CONTRACT_ID`. Never place in a web environment. |
| `DEMO_SUPPLIER_ACCOUNTS` | Three comma-separated Testnet supplier accounts used when seeding a fresh workspace. They must be real accounts for successful transfers. |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Optional OpenAI-compatible quote recommendation. Missing or invalid responses fall back to deterministic scoring. |

The complete template is [.env.example](.env.example). Never commit `.env`, `.env.local`, bootstrap keys, wallet credentials, or runtime secrets.

## Database and migrations

Alembic migration `69979f29be0a` creates the original procurement schema. Migration `2c15d3a8f641` adds `workspaces` and one-time wallet challenges, assigns existing records to `admin-demo`, adds a workspace key to every business table and changes product/supplier uniqueness to be workspace-local.

```sh
cd apps/api
../../.venv/bin/alembic upgrade head
../../.venv/bin/alembic current
../../.venv/bin/alembic check
```

Back up PostgreSQL before applying the multi-tenancy migration to an existing database. Existing inventory, orders, quotes, policies, transactions and audit history remain together in the admin workspace. The seed command is idempotent per workspace.

## Sandbox and live Testnet use

1. Anonymous visitors can read the seeded workspace and run the deterministic sandbox from Overview or Procurement agent. Sandbox activity uses `mode=sandbox`; resulting orders show **Simulated**. The endpoint never calls NEAR, signs a transaction, or spends funds. A small per-IP rate limit protects the public action.
2. Select **Connect NEAR Wallet** to connect a Testnet wallet. The browser signs a short-lived one-time NEP-413 challenge; the API verifies the public key against Testnet RPC and issues a scoped workspace session. No seed phrase or private key is requested or stored.
3. The first verified wallet sign-in creates a unique business workspace and seeded catalog. The API gives the owner account a dedicated contract name `policy.<account-id>`.
4. From **Settings**, the owner can deploy the policy contract using wallet-confirmed Testnet transactions. Deployment creates the subaccount, installs the built WASM, initializes the owner, and configures the workspace's initial spend policy. The wallet pays account storage and transaction fees.
5. The owner funds the contract treasury from the same wallet. A purchase order can be executed only after the connected workspace owner authorizes it in their wallet. The contract, not the LLM or API, checks supplier authorization, caps, balance, pause state and order replay.
6. RestockOS waits for final Testnet status and checks the contract purchase state before displaying a verified transaction hash, receipt and explorer link.

The existing admin workspace keeps its owner token and server-side scoped signer for the established demo. Admin account IDs may also connect through the wallet interface by setting `ADMIN_ACCOUNT_IDS`. New tenant workspaces do not use the admin key.

## Admin access and procurement

The existing admin token continues to unlock the Northline demo workspace. Keep it in your operator secret store; the browser stores only the bearer session for the current tab. `AUTOMATION_TOKEN` may trigger normal procurement but cannot edit policy or run the redirected rejection scenario. Only explicitly allowlisted wallet accounts receive the admin role from wallet sign-in.

The procurement flow is: analyze stock coverage → request three quotes → compare normalized price, delivery and reliability → negotiate the deterministic counteroffer → check workspace policy → create a ready order → request owner wallet confirmation (tenant) or use the restricted admin signer → verify final transaction and callback receipt. Supplier quote messages are treated as data, not instructions.

## Tests

```sh
npm run build
npm run test:contract
npm run build:contract
cd apps/api
../../.venv/bin/alembic check
../../.venv/bin/python -m pytest -q
```

The API tests cover access control, sandbox labeling/non-payment, wallet challenge replay, workspace data isolation, validation, signing idempotence, settlement evidence and one-time stock receipt. Contract unit tests cover unauthorized callers, owner-authorized wallet execution, supplier allowlisting, excessive payments, pause, replay and settlement accounting. A real successful Testnet transaction must still be verified against an active funded Testnet account; a unit test is not proof of a live payment.

For a funded admin demo, configure the Testnet env values and run:

```sh
OWNER_TOKEN='your-admin-token' API_URL='http://localhost:8000' python scripts/judge-demo.py
```

The script checks one successful verified purchase and one contract rejection. It can submit Testnet transactions and uses the admin server signer, so run it only when you intend to spend the Testnet treasury/gas.

## Deployment

### ServiceBlocks / Dokploy

Use a separate project and deploy `compose.dokploy.yaml`. Configure `POSTGRES_PASSWORD`, `OWNER_TOKEN`, a unique `SESSION_SECRET`, `ADMIN_ACCOUNT_IDS`, the exact `AUTH_RECIPIENT` hostname, Testnet RPC and admin signer values. Set `WEB_ORIGIN` if using another origin. Keep the database private; expose only the web service over HTTPS. The compose file enables anonymous access to the seeded demo and sandbox.

### Railway API

Deploy the root Dockerfile with a PostgreSQL service. It migrates and seeds at container startup before serving FastAPI. Use one API replica if enabling the in-process scheduled scanner or relying on the in-memory abuse limiter; use shared rate-limit storage before horizontal scaling. Configure the API secrets above and point the web build at the API origin.

### Vercel web

Deploy `apps/web` as the Next.js project with Node 24. Set `NEXT_PUBLIC_API_URL` to the API origin or use a same-origin rewrite. Add the final site hostname as `AUTH_RECIPIENT` on the API. Do not expose `NEAR_AGENT_PRIVATE_KEY` or `OWNER_TOKEN` as `NEXT_PUBLIC_*` variables.

## Demo walkthrough

See [docs/JUDGE_GUIDE.md](docs/JUDGE_GUIDE.md) and [docs/DEMO.md](docs/DEMO.md) for repeatable sandbox and Testnet walkthroughs. Verified hosted transaction records are listed in [docs/testnet-verification.md](docs/testnet-verification.md). Video output and recording steps are documented in `videos/README.md` when a recording environment is available.

## Known limitations

- Public abuse rate limits are in-process. They are useful for a single-instance MVP but must move to shared storage for multi-replica production.
- Supplier adapters use deterministic seeded offers; they do not contact external wholesalers or arrange shipping.
- New tenant workspaces use the owner wallet as the authorized contract caller and must confirm each live purchase. Optional restricted function-call keys are not assumed or created.
- A workspace contract is one contract per owner account. Existing deployed contracts cannot be upgraded by the current immutable account; deploy a new Testnet account after contract changes.
- The repository's near-sdk-js dependency is pinned for hackathon reproducibility. Review the SDK's maintenance status and contract code before production use.
- NEAR Testnet tokens have no mainnet value. Mainnet is intentionally unsupported.
- Wallet sign-in, wallet confirmation, database migration against PostgreSQL, and newly deployed tenant contract execution require environment access and a compatible Testnet wallet; a local build does not prove those external paths.

## Submission status

The GitHub repository and hosted public demo are available, but the hackathon submission is intentionally pending. Before submitting, verify the live deadline/rules and collect the team's required fields, video, repository URL, demo URL, track, and payout address with the team lead. Do not submit from this repository without the team's final review.
