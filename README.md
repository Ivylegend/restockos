# RestockOS

RestockOS helps an electronics retailer restock before a stockout. The agent finds the most urgent shortage, requests three quotes, compares price, delivery and reliability, negotiates a counteroffer, and creates a purchase order. Owners can authorize automatic payment. A NEAR Testnet contract restricts suppliers and amounts independently of the app.

Built for **NEAR HACKATHON 2026** · Primary track **Autonomous Business** (`business`). [Live rules](https://nearhackathon.com/HACKATHON.md) · [Track starter](https://github.com/nearai/near-hackathon-prompt-examples/blob/main/tracks/04-business.md)

## Hosted judge demo

Open the [public demo dashboard](https://restockos-restockos-stack-ogkaac-a88c69-194-31-150-55.sslip.io) without signing in. Follow the charger shortage in Overview, the three offers in Suppliers, the decision log in Procurement agent, and the paid and rejected receipts in [Treasury](https://restockos-restockos-stack-ogkaac-a88c69-194-31-150-55.sslip.io/treasury). The workspace contains seeded Testnet data. Owner authentication is required for settings, inventory changes, agent runs, payments, and resets.

## Verified Testnet demo

| Evidence | Result |
| --- | --- |
| Policy contract | [policy.restock-d2bc4c9f.testnet](https://testnet.nearblocks.io/address/policy.restock-d2bc4c9f.testnet) |
| Successful purchase | [0.14208 NEAR to Northstar Supply](https://testnet.nearblocks.io/txns/5UQinDJsDnArv5cWtPiN43SmfqmchxdiGwCcMuasqjzJ) |
| Settlement callback receipt | `8JaPpxJLS7zHnUXEAweSysBuZp8bgFTQ7iihQMByKMrT` |
| Redirected quote | [Rejected by the contract](https://testnet.nearblocks.io/txns/8Jygp1sq5xwfxJRBZiFfz3sWmLHDwAK7UohbMmyKZ5eS) with `SUPPLIER_NOT_ALLOWED` |

The successful run selected 37 USB-C chargers, negotiated a 4% reduction, and debited the funded treasury. The rejection demo left the treasury’s available, reserved, and spent balances unchanged. The [verification record](docs/testnet-verification.md) also includes a purchase that the agent executed automatically.

## Architecture

- `apps/web` contains the Next.js App Router dashboard, TanStack Query, Tailwind and local shadcn-style UI primitives. Settings uses NEAR Connect for owner wallet actions.
- `apps/api` contains FastAPI, Pydantic, SQLAlchemy 2, Alembic, and PostgreSQL. A workspace owner token protects reads and writes. An optional automation token can trigger normal scans.
- `apps/api/restock/procurement.py` orchestrates typed procurement functions. An optional OpenAI-compatible tool call recommends a quote from approved numeric inputs. Deterministic scoring and policy checks govern execution. No supplier text or signer credentials are sent to the model.
- `contracts/procurement-policy` contains the near-sdk-js policy. It reserves funds before transfer and finalizes or refunds on a private callback. The agent key is scoped to the contract’s `execute_purchase` method with zero attached deposit.
- `scripts/sign-purchase.mjs` uses near-api-js v7. FastAPI stores the signed bytes before broadcasting and checks final RPC status, transaction identity, and on-chain purchase state before marking an order paid.

## Local setup

Use Node.js 24, Python 3.12, and PostgreSQL. Docker Compose is optional if PostgreSQL is already running.

```sh
cp .env.example .env
npm ci --ignore-scripts
python3.12 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
docker compose up -d db
```

Set `OWNER_TOKEN` in `.env` to a random secret, for example the output of `openssl rand -hex 32`. Deploy Testnet before seeding if you want to run the payment demo. The seed uses `DEMO_SUPPLIER_ACCOUNTS` on its first run. For a seeded offline database, use a fresh database when switching to different supplier accounts.

```sh
cd apps/api
../../.venv/bin/alembic upgrade head
../../.venv/bin/python -m restock.seed
../../.venv/bin/uvicorn restock.main:app --host 127.0.0.1 --port 8000
```

In another terminal at the repository root, run `npm run dev -w @restockos/web`. Open [localhost:3000](http://localhost:3000), enter the owner token, and verify the catalog shows 16 products and three stockout alerts. The API docs are at [localhost:8000/docs](http://localhost:8000/docs).

### Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `OWNER_TOKEN` | Server secret entered into the dashboard, kept in tab session storage |
| `AUTOMATION_TOKEN` | Optional token for normal scans through `POST /agent/run` |
| `WEB_ORIGIN` | Exact dashboard origin for CORS |
| `NEXT_PUBLIC_API_URL` | Public API origin, baked into the dashboard build |
| `PUBLIC_DEMO` | Enables anonymous read access to operational demo data when `DEMO_ENABLED` is also on. Enable only on a seeded demo workspace |
| `DEMO_ENABLED` | Enables owner-only redirected quote and demo inventory reset |
| `SCAN_INTERVAL_SECONDS` | In-process scan frequency, with zero disabling it. Only scans when auto-execution is enabled and the workspace is unpaused |
| `NEAR_RPC_URL`, `NEAR_CONTRACT_ID`, `NEAR_AGENT_ID` | Testnet connection and account IDs |
| `NEAR_AGENT_PRIVATE_KEY` | Scoped function-call secret. The signer checks the RPC key permission |
| `DEMO_SUPPLIER_ACCOUNTS` | Three comma-separated Testnet supplier accounts, in seed order |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Optional OpenAI-compatible quote recommendation. Missing keys, errors and invalid choices use deterministic fallback |

## Deploy the contract to Testnet

Use an isolated Testnet account. The script creates `policy.<owner>`, a scoped signer account and three supplier accounts, configures a 0.5 NEAR per-order limit and 2 NEAR total budget, and funds 2 NEAR of purchasing balance. The deployment uses roughly 6 NEAR for contract storage and operating headroom. It deploys a fresh account and initializes it in the same receipt. The contract account has no full-access key, so changes to contract code require a new deployment.

```sh
# Run the pinned SDK's compiler installer on macOS or Linux, then build.
(cd node_modules/near-sdk-js && node lib/cli/post-install.js)
npm run build:contract
node scripts/testnet-bootstrap.mjs .env.testnet
# Copy the runtime values into your root .env before running the seed.
# Keep NEAR_BOOTSTRAP_OWNER_KEY in the local, ignored bootstrap file.
```

The helper obtains faucet tokens by default. If the faucet is unavailable, supply a fresh funded named Testnet account through `NEAR_BOOTSTRAP_OWNER` and `NEAR_BOOTSTRAP_OWNER_KEY` in your local shell. To sign policy changes from Settings, connect the owner account using a Testnet wallet you control. The API takes only the scoped agent key. [Deployment docs](https://docs.near.org/smart-contracts/release/deploy) · [NEAR Connect](https://github.com/azbang/near-connect) · [Transaction RPC](https://docs.near.org/api/rpc/transactions)

## Judge walkthrough

1. Open **Overview** and inspect the USB-C 65W charger’s stockout risk. It starts at 3 units with a reorder point of 20.
2. In **Settings**, turn on automatic execution and save workspace policy. The Testnet deployment already has a funded and unpaused on-chain policy.
3. Select **Run procurement**. Under **Suppliers**, inspect three offers. In **Procurement agent**, inspect the decision and negotiated amount. The agent sends the order automatically when workspace permissions allow it.
4. Open **Treasury** and wait for a paid status and a callback receipt. Open the explorer link. In **Purchase orders**, receive stock when you want to demonstrate the inventory movement.
5. Open **Procurement agent** and select **Run rejection demo** while an item is still below its reorder point. Follow the rejected transaction in **Treasury** and compare available, reserved, and spent balances.
6. To repeat from the same inventory, receive paid orders first, then use **Settings → Reset demo stock**. This preserves transactions and does not refill the on-chain budget.

CLI equivalent against a running, funded API. Export the same owner token and optionally set `API_URL`.

```sh
python scripts/judge-demo.py
```

## Tests

```sh
npm run build
npm run test:contract
npm run build:contract
(cd apps/api && ../../.venv/bin/alembic check && ../../.venv/bin/python -m pytest -q)
```

The contract tests exercise unauthorized callers, allowlist violations, order and budget limits, replay, pause, pending reservations, success, and refund accounting. API tests exercise access control, validation, order lookup, idempotent signing, evidence-based settlement and one-time stock receipt. `judge-demo.py` checks both real Testnet paths and treasury invariants.

## Hosting

1. On Railway, link the repository at its root and add PostgreSQL. The root Dockerfile installs the Node signer alongside FastAPI, migrates and seeds at startup, and serves `/health`. Reference the PostgreSQL service’s `DATABASE_URL` and configure the scoped Testnet variables, owner token and dashboard origin. Use one replica for the in-process scheduled scanner. [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles) · [Railway PostgreSQL](https://docs.railway.com/databases/postgresql)
2. On Vercel, choose Next.js and set the root directory to `apps/web`. Enable inclusion of source files outside the root for `packages/shared` and use Node 24. Set install command to `cd ../.. && npm ci --ignore-scripts` and set `NEXT_PUBLIC_API_URL` to the Railway HTTPS origin. Set Railway `WEB_ORIGIN` to the final Vercel HTTPS origin. [Vercel monorepos](https://vercel.com/docs/monorepos)

## Known limitations

- The supplier adapter supplies deterministic demo offers and counteroffers. External supplier APIs, shipping, invoicing and returns are outside the MVP.
- This is a single-workspace Testnet deployment. Authorization uses a shared owner token, with the actual owner wallet required for on-chain configuration, pause and funding.
- The pinned JavaScript contract SDK is archived. The contract account is immutable after deployment. A live merchant deployment would need a maintained SDK and independent contract review. [SDK status](https://github.com/near/near-sdk-js)
- The worker serializes pending payments and rebroadcasts the same signed bytes after an RPC interruption. A pending transaction whose block reference expires before acceptance requires operator reconciliation. Order IDs are permanently consumed once reserved.
- A hosted demo and a live LLM provider require their own account configuration. The deterministic quote path runs without AI credentials.
- NEAR Intents and advanced analytics are outside this Testnet scope.

## Submission checklist

- [x] Run local build, contract tests, API tests, migrations and the Testnet demo.
- [ ] Publish the repository with the team’s explicit approval by November 14, 2026 at 23:59 UTC.
- [ ] Record the end-to-end walkthrough and publish a public X post with the video, `@NEARProtocol` and `#NEARHackathon`. A video is required for a local-only demo.
- [ ] Re-read the live rules and collect the team lead, email, team size, eligible tracks, mainnet payout address, public repository, demo URL, summary, and contact consent.
- [ ] Review the exact submission payload with the team and submit once by the deadline. [Live rules](https://nearhackathon.com/HACKATHON.md)

Libraries and tools used include Next.js, React, Tailwind, shadcn-style UI patterns, TanStack Query, Lucide, FastAPI, SQLAlchemy, Alembic, PostgreSQL, near-api-js, NEAR Connect, near-sdk-js and AI-assisted development. The workspace was built as a new project for this submission.

### ServiceBlocks Dokploy

Create a separate project and a Docker Compose service using this repository’s `main` branch and `./compose.dokploy.yaml`. Set `POSTGRES_PASSWORD` to a random hex value and add `OWNER_TOKEN` and the Testnet runtime values from the environment table. Assign an HTTPS domain to the `web` service on container port `3000`. The dashboard uses same-origin `/api` requests proxied to FastAPI. PostgreSQL and FastAPI stay on the Compose network. Verify `/api/health` and run `scripts/judge-demo.py` with `API_URL=https://YOUR_HOST/api`. [Dokploy Compose domains](https://docs.dokploy.com/docs/core/docker-compose/domains)
