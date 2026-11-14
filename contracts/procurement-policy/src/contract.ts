import { NearBindgen, NearPromise, LookupMap, call, initialize, near, view } from 'near-sdk-js';
import { account, amount, reserve, settle, type Policy, type Purchase } from './policy.js';

@NearBindgen({ requireInit: true })
class ProcurementPolicy {
  policy: Policy = {
    owner: '', agent: '', suppliers: [], max_order: '0', budget: '0',
    paused: true, available: '0', reserved: '0', spent: '0',
  };
  purchases = new LookupMap<Purchase>('orders');

  @initialize({})
  init({ owner }: { owner: string }) {
    if (!account(owner) || near.predecessorAccountId() !== owner || near.currentAccountId() !== 'policy.' + owner) throw new Error('INVALID_INITIALIZER');
    this.policy.owner = owner;
  }

  private requireOwner() {
    if (near.predecessorAccountId() !== this.policy.owner) throw new Error('OWNER_ONLY');
  }

  @call({})
  configure_policy({ agent, suppliers, max_order, budget, paused }: {
    agent: string; suppliers: string[]; max_order: string; budget: string; paused: boolean;
  }) {
    this.requireOwner();
    if (!account(agent) || agent === near.currentAccountId() ||
        !Array.isArray(suppliers) || suppliers.length > 50 ||
        suppliers.some(supplier => !account(supplier) || supplier === near.currentAccountId()) ||
        typeof paused !== 'boolean') throw new Error('INVALID_POLICY');
    if (amount(max_order) > amount(budget) ||
        amount(budget) < amount(this.policy.spent) + amount(this.policy.reserved)) throw new Error('INVALID_CAPS');
    Object.assign(this.policy, { agent, suppliers: [...new Set(suppliers)], max_order, budget, paused });
  }

  @call({ payableFunction: true })
  fund_treasury() {
    this.requireOwner();
    const deposit = near.attachedDeposit();
    if (deposit <= 0n) throw new Error('DEPOSIT_REQUIRED');
    const available = (amount(this.policy.available) + deposit).toString();
    amount(available);
    this.policy.available = available;
  }

  @call({})
  pause_agent() {
    this.requireOwner();
    this.policy.paused = true;
  }

  @call({})
  execute_purchase({ order_id, supplier, amount: value }: { order_id: string; supplier: string; amount: string }): NearPromise {
    if (typeof order_id !== 'string' || !/^[a-zA-Z0-9_-]{1,80}$/.test(order_id)) throw new Error('INVALID_ORDER_ID');
    const purchase: Purchase = { order_id, supplier, amount: value, status: 'pending' };
    reserve(this.policy, near.predecessorAccountId(), purchase, this.purchases.get(order_id) !== null);
    this.purchases.set(order_id, purchase);
    return NearPromise.new(supplier).transfer(amount(value)).then(
      NearPromise.new(near.currentAccountId()).functionCall(
        'on_transfer', JSON.stringify({ order_id }), 0n, 20_000_000_000_000n,
      ),
    );
  }

  @call({ privateFunction: true })
  on_transfer({ order_id }: { order_id: string }): Purchase {
    const purchase = this.purchases.get(order_id);
    if (!purchase || near.promiseResultsCount() !== 1n) throw new Error('INVALID_CALLBACK');
    let succeeded: boolean;
    try {
      near.promiseResult(0n);
      succeeded = true;
    } catch {
      succeeded = false;
    }
    settle(this.policy, purchase, succeeded);
    this.purchases.set(order_id, purchase);
    return purchase;
  }

  @view({})
  get_policy(): Policy { return this.policy; }

  @view({})
  get_purchase({ order_id }: { order_id: string }): Purchase | null { return this.purchases.get(order_id); }
}
