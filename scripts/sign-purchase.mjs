import { Account, actions, baseEncode, JsonRpcProvider, KeyPairSigner } from 'near-api-js';

try {
  const { near_rpc_url, contract, agent, order_id, supplier, amount } = JSON.parse(process.argv[2]);
  if (![contract, agent, supplier].every(id => id === 'testnet' || id.endsWith('.testnet'))) {
    throw new Error('Testnet accounts required');
  }
  const provider = new JsonRpcProvider({ url: near_rpc_url });
  const status = await provider.viewNodeStatus();
  if (status.chain_id !== 'testnet') throw new Error('Testnet RPC required');
  const signer = KeyPairSigner.fromSecretKey(process.env.NEAR_AGENT_PRIVATE_KEY);
  const key = await signer.getPublicKey();
  const access = await provider.viewAccessKey({ accountId: agent, publicKey: key });
  const permission = access.permission?.FunctionCall;
  if (permission?.receiver_id !== contract || permission.method_names.length !== 1 ||
      permission.method_names[0] !== 'execute_purchase') throw new Error('Scoped function-call key required');
  const account = new Account(agent, provider);
  const transaction = await account.createTransaction({
    receiverId: contract,
    publicKey: key,
    actions: [actions.functionCall('execute_purchase', { order_id, supplier, amount }, 70_000_000_000_000n, 0n)],
  });
  const signed = await signer.signTransaction(transaction);
  process.stdout.write(JSON.stringify({
    hash: baseEncode(signed.txHash),
    payload: Buffer.from(signed.signedTransaction.encode()).toString('base64'),
  }));
} catch (error) {
  process.stderr.write(error?.message === 'Scoped function-call key required' ?
    'Configured agent key must be restricted to execute_purchase on this contract.' :
    'Unable to prepare signed NEAR Testnet purchase. Verify RPC, accounts and scoped signer.');
  process.exitCode = 1;
}
