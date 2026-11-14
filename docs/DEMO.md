# Demo runbook

## Public sandbox

The public sandbox is the safest first look:

1. Open the public Overview.
2. Select **Run interactive sandbox**.
3. Review the agent event stream, three offers, chosen supplier and simulated purchase order.
4. Verify the order is labeled **Simulated** and that Treasury transaction history is unchanged.

Sandbox runs do not sign, broadcast, or spend Testnet assets. They write a sandbox run and quote/order records to the seeded demo workspace so the UI can show a complete interactive path. They do not change the seeded inventory. Public requests are rate-limited per IP within each API process.

## Admin demo with verified chain evidence

The hosted Northline workspace retains the original admin token and signer. Historical Testnet evidence is already available in Treasury:

- Paid 37 USB-C chargers for 0.14208 NEAR: [transaction](https://testnet.nearblocks.io/txns/5UQinDJsDnArv5cWtPiN43SmfqmchxdiGwCcMuasqjzJ), callback `8JaPpxJLS7zHnUXEAweSysBuZp8bgFTQ7iihQMByKMrT`.
- Contract rejected a redirect: [transaction](https://testnet.nearblocks.io/txns/8Jygp1sq5xwfxJRBZiFfz3sWmLHDwAK7UohbMmyKZ5eS).

The same outcomes and treasury invariants are detailed in [testnet-verification.md](testnet-verification.md). A saved receipt is evidence of a past transaction, not a new tenant payment.

## Repeat the Testnet flow

Only an authorized operator with a funded demo environment should repeat the admin test:

```sh
OWNER_TOKEN='your-admin-token' API_URL='https://your-api.example/api' python scripts/judge-demo.py
```

The script starts a normal agent run, verifies three quotes, triggers an actual Testnet purchase through the restricted server signer, waits for finality and callback evidence, then submits a redirected supplier scenario and checks that treasury balances remain unchanged. A rejected transaction can consume agent gas. Inventory reset does not refill the on-chain treasury, and order IDs are not reused.

## New wallet workspace

1. Connect a funded Testnet wallet.
2. Review the workspace name and owner account on Settings.
3. Deploy the `policy.<owner>` Testnet contract. The browser fetches the public compiled WASM and each NEAR action is wallet-confirmed.
4. Configure approved supplier accounts and spending limits, then fund the contract treasury with Testnet NEAR.
5. Run procurement. Confirm the displayed contract, supplier and yocto amount in the wallet.
6. Wait for the API to verify final RPC state. A pending status means finality has not yet been confirmed.

## Recording environment

Video recording uses the actual hosted RestockOS page and saved, verified Testnet receipts; no transaction hashes are generated for the video. The recording must not show an access token, wallet approval, private key, seed phrase, unrelated browser tab, or private business data. The soundtrack is generated from original synthesized audio, and the narration/captions are authored for this demo. See `videos/README.md` for the recording script and output path.
