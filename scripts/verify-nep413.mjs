import { JsonRpcProvider } from 'near-api-js';
import { verifyMessage } from 'near-api-js/nep413';

try {
  const { rpc, account_id, public_key, signature, message, nonce, recipient } = JSON.parse(process.argv[2]);
  const provider = new JsonRpcProvider({ url: rpc });
  if ((await provider.viewNodeStatus()).chain_id !== 'testnet') throw new Error('Testnet RPC required');
  await verifyMessage({
    signerAccountId: account_id,
    signerPublicKey: public_key,
    signature: Buffer.from(signature, 'base64'),
    payload: { message, recipient, nonce: Buffer.from(nonce, 'base64') },
    provider,
  });
  process.stdout.write('verified');
} catch {
  process.stderr.write('NEP-413 signature could not be verified against the Testnet account key.');
  process.exitCode = 1;
}
