# Judge guide

## Public walk-through (no account required)

1. Open the hosted RestockOS public dashboard. Overview shows the seeded 16-product electronics workspace and three low-stock risks.
2. Select **Run interactive sandbox**. Follow the new `sandbox` activity in Procurement agent and the **Simulated** purchase order in Purchase orders. The UI states that no wallet was asked to sign and no NEAR was sent.
3. Open Inventory and search by SKU or product name. Open Suppliers to inspect the three supplier profiles and their quote rows. The run displays the selected/negotiated compliant offer.
4. Open Treasury to inspect Testnet transaction hashes, final statuses, callback receipts and explorer links. These rows are real Testnet evidence from the earlier verified demo; sandbox runs never create transaction rows.

## Verified Testnet evidence

The historic hosted demo records:

- A successful 0.14208 NEAR purchase: [Testnet transaction](https://testnet.nearblocks.io/txns/5UQinDJsDnArv5cWtPiN43SmfqmchxdiGwCcMuasqjzJ). The API verified finality and contract purchase state; callback receipt `8JaPpxJLS7zHnUXEAweSysBuZp8bgFTQ7iihQMByKMrT`.
- A redirected supplier account rejected by the policy contract: [Testnet rejection](https://testnet.nearblocks.io/txns/8Jygp1sq5xwfxJRBZiFfz3sWmLHDwAK7UohbMmyKZ5eS). Treasury available, reserved and spent balances stayed unchanged.
- Contract deployment and funding details are recorded in [testnet verification](testnet-verification.md).

These are historical receipts. They do not prove that a newly created tenant contract has been deployed or funded.

## Try your own Testnet workspace

1. Choose **Connect NEAR Wallet** and select a Testnet account. The wallet signs a one-time RestockOS login challenge; no recovery phrase or private key is requested.
2. The first verified connection creates a private workspace, seeded with 16 products and three configured supplier records. Authenticated data is filtered by workspace ID on the API.
3. Open Settings and deploy the workspace Testnet policy. Wallet prompts create `policy.<owner-account-id>`, install the current contract WASM, initialize the owner and apply the workspace spending limits. The wallet will spend Testnet account storage and gas.
4. Fund the policy treasury from that same owner wallet. Policy values can be edited by the workspace owner. The contract independently enforces its own supplier list and spending limits.
5. Run procurement. The order remains ready until the owner selects **Confirm with wallet** and reviews the transaction in the wallet. RestockOS displays a transaction only after verifying final Testnet RPC and contract state.

Do not approve a wallet transaction that differs from the displayed contract, supplier, amount, or Testnet network. No mainnet flow is supported.

## Admin and controlled rejection

The existing admin workspace is preserved. With the admin bearer token, judges/operators can inspect Settings, stock permissions, and the admin server-signing path. The server key is scoped to the configured admin Testnet contract's `execute_purchase` method and is never exposed to the browser. The redirected rejection scenario is only available to admin and may use Testnet gas; prefer the saved verified rejection above when a fresh transaction is unnecessary.

## Reproducible checks

```sh
npm run build
npm run test:contract
cd apps/api
../../.venv/bin/alembic check
../../.venv/bin/python -m pytest -q
```

For a live admin-signer run, set `OWNER_TOKEN` and `API_URL`, then execute `python scripts/judge-demo.py`. It submits Testnet actions and should only be run when the operator intends to use the demo treasury and agent gas balance.

The hackathon submission is not submitted from this repository. The team must still review the final submission fields and publish the required video/link.
