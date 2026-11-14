export type Purchase = { order_id: string; supplier: string; amount: string; status: 'pending' | 'success' | 'failure' };
export type Policy = {
  owner: string; agent: string; suppliers: string[]; max_order: string; budget: string;
  paused: boolean; available: string; reserved: string; spent: string;
};
const MAX = (1n << 128n) - 1n;

export function amount(value: string): bigint {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]{0,38})$/.test(value) || BigInt(value) > MAX) {
    throw new Error('INVALID_YOCTO_AMOUNT');
  }
  return BigInt(value);
}

export function account(value: string): boolean {
  return typeof value === 'string' && value.length >= 2 && value.length <= 64 &&
    /^(?:[a-z0-9]+[-_.])*[a-z0-9]+$/.test(value);
}

export function reserve(policy: Policy, caller: string, purchase: Purchase, exists: boolean): void {
  if (caller !== policy.agent && caller !== policy.owner) throw new Error('UNAUTHORIZED_AGENT');
  if (policy.paused) throw new Error('AGENT_PAUSED');
  if (exists) throw new Error('ORDER_ALREADY_USED');
  if (!policy.suppliers.includes(purchase.supplier)) throw new Error('SUPPLIER_NOT_ALLOWED');
  const value = amount(purchase.amount);
  if (value === 0n || value > amount(policy.max_order)) throw new Error('PER_ORDER_CAP');
  if (value + amount(policy.spent) + amount(policy.reserved) > amount(policy.budget)) throw new Error('BUDGET_CAP');
  if (value > amount(policy.available)) throw new Error('INSUFFICIENT_TREASURY');
  policy.available = (amount(policy.available) - value).toString();
  policy.reserved = (amount(policy.reserved) + value).toString();
}

export function settle(policy: Policy, purchase: Purchase, succeeded: boolean): void {
  if (purchase.status !== 'pending') throw new Error('ORDER_NOT_PENDING');
  const value = amount(purchase.amount);
  policy.reserved = (amount(policy.reserved) - value).toString();
  if (succeeded) policy.spent = (amount(policy.spent) + value).toString();
  else policy.available = (amount(policy.available) + value).toString();
  purchase.status = succeeded ? 'success' : 'failure';
}
