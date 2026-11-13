import { randomBytes } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { Account, actions, JsonRpcProvider, KeyPairEd25519, KeyPairSigner, nearToYocto } from 'near-api-js';

const rpcUrl = process.env.NEAR_RPC_URL || 'https://rpc.testnet.near.org';
const provider = new JsonRpcProvider({ url: rpcUrl });
const output = process.argv[2] || '.env.testnet';
if (existsSync(output)) throw new Error('Choose a new environment output path.');
if ((await provider.viewNodeStatus()).chain_id !== 'testnet') throw new Error('Testnet RPC required.');
const wasm = readFileSync(new URL('../contracts/procurement-policy/build/procurement.wasm', import.meta.url));
const owner = process.env.NEAR_BOOTSTRAP_OWNER || `restock-${randomBytes(4).toString('hex')}.testnet`;
if (!owner.endsWith('.testnet') || owner.length > 48) throw new Error('Use a named Testnet owner account.');
const ownerKey = process.env.NEAR_BOOTSTRAP_OWNER_KEY
  ? new KeyPairEd25519(process.env.NEAR_BOOTSTRAP_OWNER_KEY.replace(/^ed25519:/, ""))
  : KeyPairEd25519.fromRandom();
const contract = `policy.${owner}`;
const agent = `agent.${owner}`;
const suppliers = ['northstar', 'circuit', 'volt'].map(name => `${name}.${owner}`);
const scopedKey = KeyPairEd25519.fromRandom();
const setup = [
  'NEAR_RPC_URL=' + rpcUrl,
  'NEAR_CONTRACT_ID=' + contract,
  'NEAR_AGENT_ID=' + agent,
  'NEAR_AGENT_PRIVATE_KEY=' + scopedKey.toString(),
  'DEMO_SUPPLIER_ACCOUNTS=' + suppliers.join(','),
  'NEAR_BOOTSTRAP_OWNER=' + owner,
  'NEAR_BOOTSTRAP_OWNER_KEY=' + ownerKey.toString(),
];
writeFileSync(output, setup.join('\n') + '\n', { mode: 0o600, flag: 'wx' });

if (!process.env.NEAR_BOOTSTRAP_OWNER_KEY) {
  const faucet = await fetch('https://helper.testnet.near.org/account', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ newAccountId: owner, newAccountPublicKey: ownerKey.getPublicKey().toString() }),
    signal: AbortSignal.timeout(25_000),
  });
  if (!faucet.ok) throw new Error(`Testnet faucet returned HTTP ${faucet.status}.`);
  let found = false;
  for (let attempt = 0; attempt < 15 && !found; attempt++) {
    try { await provider.viewAccount({ accountId: owner }); found = true; }
    catch { await new Promise(resolve => setTimeout(resolve, 1000)); }
  }
  if (!found) throw new Error('Testnet faucet account is unavailable at RPC.');
}
const signer = key => KeyPairSigner.fromSecretKey(key.toString());
const ownerAccount = new Account(owner, provider, signer(ownerKey));
const submit = async (account, receiverId, batch) => {
  const result = await account.signAndSendTransaction({ receiverId, actions: batch, waitUntil: 'FINAL', throwOnFailure: false, retries: 0 });
  if (!result.status || typeof result.status !== 'object' || 'Failure' in result.status) {
    throw new Error(`Testnet setup failed for ${receiverId}: ${JSON.stringify(result.status)}`);
  }
  console.log(receiverId, result.transaction.hash);
};
const call = (method, args, deposit = 0n) => actions.functionCall(method, args, 55_000_000_000_000n, deposit);
await submit(ownerAccount, contract, [
  actions.createAccount(), actions.transfer(nearToYocto('6')),
  actions.deployContract(wasm), call('init', { owner }),
]);
await submit(ownerAccount, agent, [
  actions.createAccount(), actions.transfer(nearToYocto('0.5')),
  actions.addFunctionCallAccessKey(scopedKey.getPublicKey(), contract, ['execute_purchase'], nearToYocto('1')),
]);
for (const supplier of suppliers) {
  await submit(ownerAccount, supplier, [actions.createAccount(), actions.transfer(nearToYocto('0.1'))]);
}
await submit(ownerAccount, contract, [
  call('configure_policy', { agent, suppliers, max_order: nearToYocto('0.5').toString(),
    budget: nearToYocto('2').toString(), paused: false }),
  call('fund_treasury', {}, nearToYocto('2')),
]);
console.log('Contract funded. Runtime and owner credentials saved to the ignored environment file.');
