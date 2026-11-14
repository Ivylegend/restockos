# Payment operations

## Workspace-owner transactions

Tenant purchase orders remain `ready` until the authenticated workspace owner requests an authorization payload and confirms the `execute_purchase` call in their connected NEAR Testnet wallet. The API checks the ready order, owner session, workspace policy, selected quote and contract ID before returning the constrained transaction arguments. The wallet signs directly; RestockOS does not receive a private key.

After the wallet returns a transaction hash, the frontend calls `POST /transactions/verify`. The API checks the final transaction signer and receiver, fetches the policy contract purchase state, and waits for the callback receipt before marking an order paid, rejected or failed. Unknown RPC results stay pending. Never infer payment failure from a timeout or report success from a wallet response alone.

The user's Testnet contract checks the owner or authorized agent predecessor, pause state, unique order ID, supplier allowlist, per-order cap, total budget and available treasury. Pending reservations count against both budget and liquidity. The private callback can only be called by the contract. Success moves reserved value to spent; transfer failure returns it to available while retaining the used order ID. A pause stops new reservations; an already pending transfer may finish.

## Preserved admin signer

The original admin workspace keeps the outbox-style server signer. It persists signed transaction bytes before broadcast, rebroadcasts the same bytes after an uncertain RPC response, and verifies the same hash. `scripts/sign-purchase.mjs` confirms the admin key is a restricted function-call key for `execute_purchase` on the configured admin Testnet contract. Signed payloads are omitted from API responses and cleared after settlement. The signer is never used for tenant sessions or sandbox runs.

The controlled rejection scenario is admin-only and intentionally submits an off-allowlist supplier destination to the contract. It may spend Testnet gas. The normal procurement workflow excludes flagged suppliers. A rejected attempt should leave available, reserved and spent contract balances unchanged.

## Sandbox and recovery

Public `/demo/run` creates a `sandbox` run and `simulated` order in the seeded admin demo workspace. It does not invoke chain signing/broadcast and never records a transaction hash. Public run requests are limited to five per minute per source IP per API process.

An admin can use `/demo/reset` to restore seeded inventory and cancel unsigned orders. It preserves transaction history and does not replenish Testnet funds or recycle order IDs. A paid order can be marked received once; stock changes and inventory movement records use the same database transaction.

## Secrets and Testnet

Use Testnet account IDs and RPC only. Keep bootstrap owner credentials separate from the API environment; only the scoped admin function-call secret belongs in the API runtime. Do not place seed phrases, private keys, `OWNER_TOKEN`, `SESSION_SECRET`, or signed payloads in the browser, logs, video, or Git. The app intentionally has no mainnet mode.
