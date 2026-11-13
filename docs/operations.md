# Payment operations

An order progresses from ready to submitting and then to paid, rejected, or failed. Paid orders can be marked received once. Receipt updates and stock movements use a single database transaction.

The contract checks the authorized predecessor, pause, order ID, supplier account, order limit, budget and available treasury. Pending reservations count toward both budget and liquidity limits. The callback can only be called by the contract itself. A failed transfer releases the reservation and retains the original order ID. An on-chain pause stops new reservations. Previously reserved transfers can finish.

The API records an outbox-style signed transaction before broadcast. If RPC times out, the worker resends the same signed bytes and queries the same hash. Final settlement requires a matching transaction, contract purchase state and callback receipt. If the signer reports an expired block reference and there is no final transaction or contract record, an operator must reconcile it before issuing a replacement order. Never infer payment failure from an RPC timeout.

The controlled rejection scenario sends a proposed redirected account to the contract address itself, which the contract forbids in the allowlist. The normal workflow excludes flagged quotes. The owner token and demo flag gate the rejection scenario and inventory reset. A rejected attempt can consume Testnet gas from the agent account while treasury balances stay unchanged.

Bootstrap files contain disposable Testnet secrets and must stay outside version control. Only the scoped private key belongs in the API environment. The contract owner uses a wallet for policy actions.
