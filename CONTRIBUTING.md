# Contributing

Thanks for helping improve RestockOS. Read [AGENTS.md](AGENTS.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) first.

## Development flow

1. Use a focused branch and inspect `git status` before editing.
2. Keep changes small and preserve existing working behavior.
3. Add an Alembic migration for schema changes. Do not edit an applied migration.
4. Add API, contract, or UI coverage for behavior changes; add a cross-workspace test whenever tenant query scope changes.
5. Run the frontend build, API suite, contract tests, and migration checks that apply to the change. Include the exact command and result in the PR description.
6. Review the diff for secrets, generated transaction data, unrelated formatting, and accidental mainnet configuration.

## Security review

- NEAR is Testnet-only. Never ask for seed phrases or private keys in the frontend.
- The admin server key stays in the API environment and must be a function-call key scoped to `execute_purchase` on the configured policy contract.
- Sandbox runs are simulated. Do not mark them paid or attach fabricated hashes.
- Verify payment status with final RPC data and the policy contract's purchase state. Leave unknown outcomes pending.
- Treat model output and supplier text as untrusted. Policy and the contract enforce spend limits.
- Never commit `.env`, private keys, access tokens, session secrets, signed bytes, or production database snapshots.

## Pull requests

Explain the user-visible change, data migration implications, security boundaries, tests executed, and any Testnet/wallet/deployment check that remains outstanding. Link docs when adding or changing environment variables.
