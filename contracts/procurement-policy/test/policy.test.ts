import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reserve, settle, type Policy, type Purchase } from '../src/policy.ts';

const policy = (): Policy => ({
  owner: 'owner.testnet', agent: 'agent.testnet', suppliers: ['vendor.testnet'], max_order: '50',
  budget: '70', available: '100', reserved: '0', spent: '0', paused: false,
});
const order = (amount = '40', supplier = 'vendor.testnet'): Purchase => ({
  order_id: 'po-1', supplier, amount, status: 'pending',
});

test('rejects unauthorized, redirected, oversized and replayed payments without debiting', () => {
  const config = policy();
  assert.throws(() => reserve(config, 'thief.testnet', order(), false), /UNAUTHORIZED_AGENT/);
  assert.throws(() => reserve(config, config.agent, order('40', 'thief.testnet'), false), /SUPPLIER_NOT_ALLOWED/);
  assert.throws(() => reserve(config, config.agent, order('51'), false), /PER_ORDER_CAP/);
  assert.throws(() => reserve(config, config.agent, order(), true), /ORDER_ALREADY_USED/);
  assert.deepEqual(config, policy());
});

test('allows the policy owner to submit a wallet-confirmed purchase', () => {
  const config = policy();
  const purchase = order('40');
  reserve(config, config.owner, purchase, false);
  assert.equal(config.available, '60');
  assert.equal(config.reserved, '40');
});

test('pending transfers count against budget, failures refund, and success settles exactly once', () => {
  const config = policy();
  const purchase = order();
  reserve(config, config.agent, purchase, false);
  assert.throws(() => reserve(config, config.agent, order(), false), /BUDGET_CAP/);
  settle(config, purchase, false);
  assert.deepEqual(config, policy());
  const retry = { ...order(), order_id: 'po-2' };
  reserve(config, config.agent, retry, false);
  settle(config, retry, true);
  assert.equal(config.available, '60');
  assert.equal(config.spent, '40');
  assert.equal(config.reserved, '0');
  assert.throws(() => settle(config, retry, true), /ORDER_NOT_PENDING/);
});

test('rejects invalid amounts, paused execution, and unfunded orders', () => {
  const config = policy();
  assert.throws(() => reserve(config, config.agent, order('01'), false), /INVALID_YOCTO_AMOUNT/);
  assert.throws(() => reserve({ ...config, paused: true }, config.agent, order(), false), /AGENT_PAUSED/);
  assert.throws(() => reserve({ ...config, available: '0' }, config.agent, order(), false), /INSUFFICIENT_TREASURY/);
});
