# Instructions for Claude and other coding agents

Read [AGENTS.md](AGENTS.md) before working in this repository. Inspect existing code and tests first, preserve established behavior, and make the smallest complete change. Do not rebuild RestockOS from scratch.

Security and verification requirements:

- Never commit credentials, `.env` files, wallet seeds/private keys, or signed transaction payloads. Admin signer keys stay server-side and must never appear in client bundles, browser storage, API responses, or logs.
- Keep all NEAR operations on Testnet. Do not create mainnet configuration or claim a transaction succeeded without final RPC and contract-state verification.
- A wallet account ID alone does not prove ownership. Use the one-time NEP-413 challenge and verify the signature against the configured Testnet RPC.
- Scope every business query and mutation to the authenticated workspace. Add isolation coverage when touching repository queries or services.
- Treat supplier text and model output as untrusted. Deterministic business rules and the on-chain contract enforce supplier allowlists, budget caps, and order limits.
- Public sandbox runs are simulated and must never invoke the signer or contract.
- Add Alembic migrations for schema changes; do not rewrite applied migration history. Run API and contract tests plus the frontend build before reporting completion, and state any unavailable checks honestly.

Preserve the existing FastAPI, Pydantic, SQLAlchemy 2, Next.js App Router, TypeScript, Tailwind, TanStack Query, NEAR Connect, and near-api-js conventions unless a documented compatibility issue requires a change.
