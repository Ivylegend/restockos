# Repository instructions for coding agents

Before changing RestockOS:

1. Inspect the relevant existing frontend, API, database migration, NEAR contract, tests, and deployment files. Preserve established patterns and working behavior; do not scaffold a replacement app or rewrite modules unnecessarily.
2. Check `git status` before editing. Keep user changes, generated artifacts, and secrets intact. Never read a credential into logs or commit `.env`, private keys, signed transaction payloads, or wallet recovery material.
3. Treat workspace IDs as authorization boundaries. Derive tenant identity only from a verified session, scope all reads/writes/joins/background operations, and add a regression test for cross-workspace access whenever a query changes.
4. Keep the NEAR network set to Testnet. Never add a mainnet path. The frontend must not request or persist seed phrases/private keys. The optional admin signer stays in the API, restricted to its configured contract method, and absent from browser bundles and API responses.
5. Treat LLM output and supplier content as untrusted recommendations. Deterministic policy checks and the deployed contract authorize spending. Public sandbox actions must remain simulated and must never call a signer or broadcast a transaction.
6. Never report a payment as successful from an API response, local state, or fabricated hash. Query final NEAR Testnet transaction status and contract purchase/callback state, then show the explorer link. Unknown RPC outcomes remain pending for reconciliation.
7. Add or update migrations instead of changing an already-applied migration. Test migration upgrades against PostgreSQL when available and inspect data preservation for upgrades from the existing single-workspace schema.
8. Run the relevant tests and frontend build before reporting success. Distinguish checks that ran from checks blocked by missing credentials, wallet approvals, database services, RPC, or deployment access.

Keep API/service responsibilities, typed Pydantic schemas, SQLAlchemy 2 patterns, and existing Next.js/TanStack Query conventions. Document any new environment variable and avoid adding unnecessary dependencies.
