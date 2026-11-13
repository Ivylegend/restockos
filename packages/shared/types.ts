export type Product = {id:number; sku:string; name:string; category:string; stock:number; reorder_point:number; daily_sales:number; unit_price:string};
export type Supplier = {id:number; name:string; account:string; lead_days:number; reliability:number};
export type Quote = {id:number; product_id:number; supplier_id:number; account:string; amount:string; negotiated_amount:string|null; status:string; quantity:number; lead_days:number; reliability:number};
export type Event = {id:number; kind:string; message:string; created_at:string};
export type Run = {id:string; scenario:string; status:string; mode:string; created_at:string; events:Event[]};
export type Order = {id:string; product:string; supplier:string; account:string; quantity:number; amount:string; status:string; reason:string|null; hash:string|null; created_at:string};
export type Transaction = {id:number; order_id:string; hash:string; status:string; contract:string; signer:string; receipt_id:string|null; reason:string|null; created_at:string};
export type Policy = {paused:boolean; auto_execute:boolean; approved_accounts:string[]; max_order:string; budget:string};
export type ChainPolicy = {owner:string; agent:string; suppliers:string[]; paused:boolean; max_order:string; budget:string; available:string; reserved:string; spent:string};
export type Treasury = {contract:string|null; policy:ChainPolicy|null; error:string|null};
export type Summary = {products:number; shortages:number; open_orders:number; settled_yocto:string; low_stock:Product[]; activity:Event[]; categories:{name:string; count:number}[]};

export function toYocto(value: string): string {
  if (!/^\d{1,15}(\.\d{1,24})?$/.test(value.trim())) throw new Error('Enter a valid NEAR amount with up to 24 decimal places.');
  const [whole, fraction = ''] = value.trim().split('.');
  return (BigInt(whole) * 10n ** 24n + BigInt(fraction.padEnd(24, '0'))).toString();
}

export function nearAmount(value: string, decimals = 6): string {
  const amount = BigInt(value);
  const base = 10n ** 24n;
  const remainder = amount % base;
  const fraction = remainder.toString().padStart(24, '0').slice(0, decimals).replace(/0+$/, '');
  if (amount < base && remainder && !fraction) return '<0.' + '0'.repeat(decimals - 1) + '1';
  return (amount / base).toString() + (fraction ? '.' + fraction : '');
}
