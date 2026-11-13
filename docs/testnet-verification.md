# Testnet verification

Verified through the FastAPI workflow on November 13, 2026 against NEAR Testnet.

| Item | Evidence |
| --- | --- |
| Deployment | [DCi7D8SmahwAWvpXMuubuTPYgRCogF72AtX7TFYAXn9h](https://testnet.nearblocks.io/txns/DCi7D8SmahwAWvpXMuubuTPYgRCogF72AtX7TFYAXn9h) |
| Configuration and funding | [Ccm15EMmPtFaynDPftPCA66KGM5uLzWf4ybAQbdspNYr](https://testnet.nearblocks.io/txns/Ccm15EMmPtFaynDPftPCA66KGM5uLzWf4ybAQbdspNYr) |
| Successful purchase | [5UQinDJsDnArv5cWtPiN43SmfqmchxdiGwCcMuasqjzJ](https://testnet.nearblocks.io/txns/5UQinDJsDnArv5cWtPiN43SmfqmchxdiGwCcMuasqjzJ) |
| Final callback receipt | `8JaPpxJLS7zHnUXEAweSysBuZp8bgFTQ7iihQMByKMrT` |
| Redirect rejection | [8Jygp1sq5xwfxJRBZiFfz3sWmLHDwAK7UohbMmyKZ5eS](https://testnet.nearblocks.io/txns/8Jygp1sq5xwfxJRBZiFfz3sWmLHDwAK7UohbMmyKZ5eS) |

The API recorded three supplier quotes, negotiated a 4% reduction and settled a 37-unit order for 0.14208 NEAR. The contract rejected the second purchase because its destination was outside the allowlist. The table shows treasury state from final contract views.

| Contract state | Before purchase | After purchase | After rejection |
| --- | ---: | ---: | ---: |
| Available NEAR | 2 | 1.85792 | 1.85792 |
| Reserved NEAR | 0 | 0 | 0 |
| Spent NEAR | 0 | 0.14208 | 0.14208 |

A separate scan with automatic execution enabled paid 0.04224 NEAR without a manual execute request. [Automatic payment](https://testnet.nearblocks.io/txns/2ARHiZ8ZhwU972eL2okbw7geAtc7bTQeXQBiVtuQwXFW)

Desktop Chrome and a 390 px mobile viewport exercised all seven dashboard pages, inventory search and edit form, purchase-order lookup, receipt and rejection rendering, and mobile navigation.
