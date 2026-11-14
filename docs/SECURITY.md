# Security model

## Assets and boundaries

- Workspace inventory, suppliers, quotes, policy, orders, runs, transaction metadata, and audit records are tenant-private.
- The seeded `admin-demo` workspace can be exposed publicly for judging when public demo flags are enabled. It contains demonstration data, not a merchant's private workspace.
- The admin Testnet signer key and owner/session secrets are server-only.
- The NEAR policy contract and its treasury are protected by owner authorization, agent authorization, supplier allowlisting, per-order cap, total budget, pause, and order replay checks.

## Authentication and tenant authorization

Wallet sign-in returns only an account ID and public key after `near-api-js` verifies a short-lived NEP-413 challenge against the configured Testnet RPC. Nonces are single-use, expire after five minutes, and are bound to an account and fixed `AUTH_RECIPIENT`. Wallet sessions are HMAC-signed with `SESSION_SECRET` (or, for compatibility, `OWNER_TOKEN`) and expire after 12 hours.

The API derives the tenant only from the verified session. It does not trust caller-supplied workspace IDs. SQLAlchemy adds workspace filters for each scoped model and assigns/validates the workspace key on inserts. The migration assigns all pre-existing rows to `admin-demo`. Tests exercise cross-tenant reads and stock edits.

The `OWNER_TOKEN` retains access to the admin demo workspace. `AUTOMATION_TOKEN` permits normal procurement execution only. The optional `ADMIN_ACCOUNT_IDS` allowlist is a JSON array; those accounts receive the admin role only after wallet signature verification. Never put an account private key in this setting.

## Public sandbox

Anonymous data access is deliberately limited to the seeded demo workspace. `POST /demo/run` is capped at five calls per minute per IP per API process. It uses deterministic quote logic, creates a `mode=sandbox` run and `simulated` purchase order, and returns an explicit notice. It never invokes the NEAR signer, calls `execute_purchase`, stores a transaction hash, or changes inventory. Normal authenticated `/agent/run`, policy editing, live purchase authorization, receiving stock, and demo reset remain protected.

The in-memory rate limiter does not coordinate across replicas and resets on process restart. Use a shared rate limiter and edge/WAF controls before scaling anonymous access.

## Wallets, signing and transactions

- RestockOS never requests a seed phrase or wallet private key.
- Each user's wallet owns its business workspace and confirms deployment, funding, policy configuration, and purchase execution in the wallet UI.
- Tenant API sessions cannot access the server signer endpoint. New workspace purchases are submitted by the owner wallet after the API checks the order and policy.
- The existing admin key stays in the API environment. The signing script confirms the account access key is a function-call key restricted to exactly `execute_purchase` on the configured Testnet contract.
- The API checks the RPC chain ID before wallet signature and transaction verification. Account and contract IDs must be Testnet IDs.
- A successful UI status requires final transaction evidence plus the contract's stored purchase result. Rejection/unknown execution is not silently treated as success; unknown RPC results remain pending.
- Signed payloads are omitted from API responses and cleared after settlement. Logs must not include keys, session tokens, signed bytes, or transaction payloads.

## Agent and supplier input

LLM tool calling receives structured numeric quote choices, not arbitrary supplier communications or wallet secrets. Model output may select only a known compliant quote ID; the deterministic policy check and contract enforce the limits. Supplier messages cannot change payment destinations, accounts, policy, or allowed tools. The redirected-payment test exercises the contract allowlist.

## Operations checklist

- Set unique high-entropy `OWNER_TOKEN` and `SESSION_SECRET`; set the exact production `AUTH_RECIPIENT` hostname.
- Keep PostgreSQL off the public internet and expose only HTTPS web/API endpoints.
- Set `PUBLIC_DEMO=true` only on a seeded judge/demo environment. Do not use it for merchant production data.
- Set only Testnet RPC/contract/account IDs. Keep mainnet credentials and URLs out of this app.
- Use the smallest required admin role list and signer key permissions. Never create a full-access server key for the agent.
- Back up PostgreSQL before schema upgrades, monitor auth/agent rate limits, rotate secrets when exposed, and reconcile unknown pending transactions before retrying.
- Do not commit `.env`, bootstrap secret files, browser wallet data, session dumps, production database snapshots, or hosted-service credentials.

## Current limitations

Authentication rate limits and public sandbox limits are process-local. Workspace ownership is a single NEAR account per workspace; shared teams and role invitations are not implemented. Supplier offer generation is deterministic demo logic. The NEAR JavaScript SDK used for the contract is pinned for hackathon reproducibility and requires a security/maintenance review before production funds are used.
