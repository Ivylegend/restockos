'use client';

import Link from 'next/link';
import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, ArrowDownLeft, ArrowRight, ArrowUpRight, Boxes, Bot, CircleAlert, CircleCheck, ClipboardList, Cpu, LayoutDashboard, Menu, Package, Play, Plus, Radar, Search, Settings2, ShieldCheck, Truck, Wallet, Warehouse, X } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { nearAmount, toYocto, type Event, type Order, type Policy, type Product, type Quote, type Run, type Summary, type Supplier, type Transaction, type Treasury } from '../../../packages/shared/types';

export type Page = 'overview'|'inventory'|'suppliers'|'agent'|'orders'|'treasury'|'settings';
const pages = {
  overview: {label:'Overview', path:'/', icon:LayoutDashboard, title:'Overview', description:'Track stock levels, supplier activity, and procurement at a glance.'},
  inventory: {label:'Inventory', path:'/inventory', icon:Boxes, title:'Inventory', description:'Manage products, stock levels, and reorder points.'},
  suppliers: {label:'Suppliers', path:'/suppliers', icon:Truck, title:'Suppliers & quotations', description:'Compare supplier reliability, delivery times, and negotiated quotes.'},
  agent: {label:'Procurement agent', path:'/agent', icon:Bot, title:'Procurement agent', description:'Scan inventory and follow each decision from shortage to payment.'},
  orders: {label:'Purchase orders', path:'/orders', icon:ClipboardList, title:'Purchase orders', description:'Review purchase requests, settlement status, and incoming stock.'},
  treasury: {label:'Treasury', path:'/treasury', icon:Wallet, title:'Treasury', description:'Inspect the on-chain budget and verify Testnet payment receipts.'},
  settings: {label:'Settings', path:'/settings', icon:Settings2, title:'Settings', description:'Control what the agent can buy, where it can pay, and when it can act.'},
};
const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const explorer = (hash: string) => 'https://testnet.nearblocks.io/txns/' + encodeURIComponent(hash);
const date = (value: string) => new Intl.DateTimeFormat(undefined, {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}).format(new Date(value));
const money = (value: string) => nearAmount(value) + ' NEAR';

async function request<T>(token: string, path: string, method = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(api + path, {method, headers: {Authorization: 'Bearer ' + token, ...(body ? {'Content-Type':'application/json'} : {})},
    body: body ? JSON.stringify(body) : undefined});
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.map?.((entry:{msg:string}) => entry.msg).join(' · ') || 'The server could not complete the request.');
  return data;
}

export function Workspace({ page }: {page:Page}) {
  const [client] = useState(() => new QueryClient({defaultOptions:{queries:{staleTime:2500, retry:false}}}));
  const [token, setToken] = useState('');
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => { setToken(sessionStorage.getItem('restock-access') || ''); setHydrated(true); }, []);
  function access(value: string) {
    if (value) sessionStorage.setItem('restock-access', value);
    else sessionStorage.removeItem('restock-access');
    client.clear();
    setToken(value);
  }
  return <QueryClientProvider client={client}><Shell page={page} token={token} access={access} hydrated={hydrated} /></QueryClientProvider>;
}

function Shell({ page, token, access, hydrated }: {page:Page; token:string; access:(v:string)=>void; hydrated:boolean}) {
  const [mobile, setMobile] = useState(false);
  const [unlockError, setUnlockError] = useState('');
  const [notice, setNotice] = useState('');
  const client = useQueryClient();
  const overview = useQuery({queryKey:['summary'], queryFn:()=>request<Summary>(token,'/dashboard/summary'), enabled:!!token && page==='overview', refetchInterval:6000});
  const policy = useQuery({queryKey:['policy'], queryFn:()=>request<Policy>(token,'/agent/policy'), enabled:!!token});
  const workspace = useQuery({queryKey:['workspace'], queryFn:()=>request<{demo_enabled:boolean}>(token,'/workspace'), enabled:!!token});
  const run = useMutation({
    mutationFn:(scenario:string)=>request<Run & {order:Order|null}>(token,'/agent/run','POST',{scenario}),
    onSuccess:(data)=>{ setNotice(data.order?.reason || (data.order ? 'Run complete. Follow the order in Purchase orders.' : data.status==='clear' ? 'No shortage without an open order.' : 'Run recorded. See agent activity.')); client.invalidateQueries(); },
    onError:(err)=>setNotice(err.message),
  });
  const current = pages[page];
  async function unlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(new FormData(event.currentTarget).get('token') || '').trim();
    setUnlockError('');
    try { await request<Policy>(value, '/agent/policy'); access(value); }
    catch (error) { setUnlockError((error as Error).message); }
  }
  return <div className="app-shell">
    <aside className={mobile ? 'sidebar sidebar-open' : 'sidebar'}>
      <Link className="brand" href="/" onClick={()=>setMobile(false)}><span className="brand-icon"><Boxes size={24}/></span><span>Restock<span className="brand-accent">OS</span><small>PROCUREMENT WORKSPACE</small></span></Link>
      <div className="store"><div className="store-icon"><Warehouse size={17}/></div><div><strong>Northline Electronics</strong><small>Retail workspace</small></div></div>
      <span className="nav-label">WORKSPACE</span>
      <nav>{(Object.entries(pages) as [Page, typeof current][]).map(([id,item])=><Link key={id} href={item.path} aria-current={page===id?'page':undefined} className={page===id?'nav-active':''} onClick={()=>setMobile(false)}><item.icon size={17}/>{item.label}{page===id && <span className="nav-dot"/>}</Link>)}</nav>
      <div className="side-bottom"><div className="side-network"><ShieldCheck size={18}/><div><strong>NEAR Testnet</strong><small>Policy-enforced payments</small></div></div>{token && <Button variant="ghost" onClick={()=>access('')}>Lock workspace</Button>}</div>
    </aside>
    {mobile && <button className="scrim" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
    <div className="main-frame">
      <header className="topbar"><div className="breadcrumb"><button className="mobile-menu" aria-label="Open navigation" onClick={()=>setMobile(true)}><Menu size={22}/></button><span>Workspace</span><span>/</span><strong>{current.label}</strong></div><div className="header-right"><Badge variant="info"><span className="dot"/>Testnet</Badge><span className="avatar" aria-label="Workspace owner">NL</span></div></header>
      <main>
        <div className="page-heading"><div><div className="eyebrow"><span className="dot"/>{page==='overview'?'OPERATIONS CENTER':'NORTHLINE ELECTRONICS'}</div><h1>{current.title}</h1><p>{current.description}</p></div>
          {token && (page==='overview'||page==='agent') && <Button onClick={()=>run.mutate('normal')} disabled={run.isPending || policy.data?.paused}><Play size={16}/>{run.isPending?'Running procurement…':'Run procurement'}</Button>}
        </div>
        {notice && <div className="notice" role="status"><Activity size={16}/>{notice}<button aria-label="Dismiss message" onClick={()=>setNotice('')}><X size={16}/></button></div>}
        {!hydrated ? <Loading/> : !token ? <section className="panel unlock"><div className="feature-icon"><ShieldCheck size={24}/></div><h2>Unlock workspace</h2><p>Enter the owner access token from your RestockOS environment.</p><form onSubmit={unlock}><label>Access token<input name="token" type="password" required autoComplete="off" placeholder="Workspace token"/></label><Button>Unlock workspace <ArrowRight size={16}/></Button></form>{unlockError && <ErrorState error={unlockError}/>}</section> :
          <>
            {page==='overview' && <QueryView query={overview}>{data=><Overview data={data} policy={policy.data}/>}</QueryView>}
            {page==='inventory' && <Inventory token={token}/>}
            {page==='suppliers' && <Suppliers token={token}/>}
            {page==='agent' && <Agent token={token} policy={policy.data} demo={workspace.data?.demo_enabled || false} runDemo={()=>run.mutate('redirect')} busy={run.isPending}/>}
            {page==='orders' && <Orders token={token}/>}
            {page==='treasury' && <TreasuryPage token={token}/>}
            {page==='settings' && <SettingsPage token={token} policy={policy.data} demo={workspace.data?.demo_enabled || false}/>}
          </>
        }
        <footer><span>RestockOS</span><span>NEAR Hackathon 2026</span></footer>
      </main>
    </div>
  </div>;
}

function Loading() { return <div className="loading-grid" role="status" aria-label="Loading workspace"><span/><span/><span/></div>; }
function ErrorState({error, retry}: {error:string; retry?:()=>void}) { return <div className="error" role="alert"><CircleAlert size={18}/><span>{error}</span>{retry && <Button variant="outline" onClick={retry}>Retry</Button>}</div>; }
function Empty({children}: {children:ReactNode}) { return <div className="empty"><Radar size={23}/><p>{children}</p></div>; }
function QueryView<T>({query, children}: {query:{data:T|undefined; isPending:boolean; error:Error|null; refetch:()=>unknown};children:(data:T)=>ReactNode}) {
  if (query.isPending) return <Loading/>;
  if (query.error || !query.data) return <ErrorState error={query.error?.message || 'Workspace data unavailable.'} retry={()=>{void query.refetch();}}/>;
  return children(query.data);
}
function Panel({title, subtitle, action, children}: {title:string; subtitle?:string; action?:ReactNode; children?:ReactNode}) {
  return <section className="panel"><div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
function Metric({label, value, help, icon:Icon, tone}: {label:string;value:string|number;help:string;icon:typeof Package;tone:string}) {
  return <article className="metric panel"><div className="metric-top"><div className={'metric-icon '+tone}><Icon size={18}/></div><span>{label}</span></div><strong>{value}</strong><small>{help}</small></article>;
}
function Status({value}: {value:string}) {
  const variant = ['paid','received','success','selected','active'].includes(value)?'good':['rejected','failed','flagged'].includes(value)?'bad':['submitting','pending','paused'].includes(value)?'warn':'neutral';
  return <Badge variant={variant}>{value === 'submitting' ? 'Awaiting finality' : value.replaceAll('_',' ')}</Badge>;
}
function ActivityFeed({events}: {events:Event[]}) {
  return events.length ? <ol className="activity-feed">{events.map(event=><li key={event.id}><span className={'activity-icon '+(event.kind==='settlement'?'green':'blue')}>{event.kind==='settlement'?<ArrowDownLeft size={15}/>:event.kind==='policy'?<ShieldCheck size={15}/>:<Activity size={15}/>}</span><div><strong>{event.kind}</strong><p>{event.message}</p><time>{date(event.created_at)}</time></div></li>)}</ol> : <Empty>Run procurement to see inventory checks, quote decisions, and payments here.</Empty>;
}
function Overview({data,policy}: {data:Summary;policy?:Policy}) {
  return <>
    <div className="metrics">
      <Metric label="Tracked products" value={data.products} help="Active catalog SKUs" icon={Package} tone="blue"/>
      <Metric label="Low-stock alerts" value={data.shortages} help="Below reorder point" icon={CircleAlert} tone="amber"/>
      <Metric label="Open orders" value={data.open_orders} help="Awaiting payment or delivery" icon={ClipboardList} tone="violet"/>
      <Metric label="Settled spend" value={nearAmount(data.settled_yocto)} help="NEAR Testnet verified" icon={Wallet} tone="green"/>
    </div>
    <div className="overview-grid">
      <Panel title="Stockout risk" subtitle="Products closest to running out" action={<Link className="text-link" href="/inventory">View inventory <ArrowRight size={14}/></Link>}>
        {data.low_stock.length ? <div className="table-wrap"><table><thead><tr><th>Product</th><th>On hand</th><th>Coverage</th></tr></thead><tbody>{data.low_stock.map(p=><tr key={p.id}><td><div className="item-name"><span className="product-icon"><Cpu size={16}/></span><div><strong>{p.name}</strong><small>{p.sku}</small></div></div></td><td>{p.stock} <span className="muted">/ {p.reorder_point}</span></td><td><Badge variant={p.daily_sales && p.stock/p.daily_sales < 2 ? 'bad':'warn'}>{p.daily_sales ? (p.stock/p.daily_sales).toFixed(1)+' days' : 'No estimate'}</Badge></td></tr>)}</tbody></table></div>:<Empty>All products are above their reorder points.</Empty>}
      </Panel>
      <Panel title="Agent activity" subtitle="Latest procurement decisions" action={<Link className="text-link" href="/agent">View runs <ArrowRight size={14}/></Link>}><ActivityFeed events={data.activity.slice(0,5)}/></Panel>
      <Panel title="Catalog by category" subtitle="Tracked SKUs across the workspace"><div className="bars">{data.categories.map(c=><div className="bar-row" key={c.name}><span>{c.name}</span><div><i style={{width:(c.count/Math.max(1,...data.categories.map(v=>v.count)))*100+'%'}}/></div><strong>{c.count}</strong></div>)}</div></Panel>
      <section className="panel agent-card"><span className="feature-icon"><Bot size={24}/></span><h2>Procurement agent</h2><p>{policy?.paused?'Procurement is paused.':policy?.auto_execute?'Approved purchases can settle automatically.':'Orders wait for manual payment execution.'}</p><Link className="text-link" href="/settings">Manage permissions <ArrowRight size={14}/></Link></section>
    </div>
  </>;
}

function SearchBox({value,onChange,placeholder}: {value:string;onChange:(v:string)=>void;placeholder:string}) {
  return <label className="search"><Search size={16}/><input aria-label={placeholder} placeholder={placeholder} value={value} onChange={e=>onChange(e.target.value)}/></label>;
}
function matches(filter: string, ...fields: (string|number|null)[]) { return fields.join(' ').toLowerCase().includes(filter.trim().toLowerCase()); }

function Inventory({token}: {token:string}) {
  const [filter,setFilter] = useState('');
  const [editing,setEditing] = useState<Product|'new'|null>(null);
  const client = useQueryClient();
  const query = useQuery({queryKey:['products'],queryFn:()=>request<Product[]>(token,'/products')});
  const save = useMutation({
    mutationFn:(fields:FormData)=>{
      const values = {stock:Number(fields.get('stock')), reorder_point:Number(fields.get('threshold')), daily_sales:Number(fields.get('sales'))};
      return editing==='new' ? request(token,'/products','POST',{...values, sku:fields.get('sku'),name:fields.get('name'),category:fields.get('category'),unit_price:toYocto(String(fields.get('price')))})
        : request(token,'/products/'+(editing as Product).id,'PATCH',values);
    },
    onSuccess:()=>{setEditing(null);client.invalidateQueries();},
  });
  return <Panel title="Product catalog" subtitle="Stock levels and sales velocity" action={<Button variant="outline" onClick={()=>{save.reset();setEditing('new');}}><Plus size={16}/>Add product</Button>}>
    <div className="table-toolbar"><SearchBox value={filter} onChange={setFilter} placeholder="Search products or SKU"/></div>
    <QueryView query={query}>{data=>{
      const rows = data.filter(p=>matches(filter,p.name,p.sku,p.category));
      return rows.length ? <div className="table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>On hand</th><th>Reorder at</th><th>Sales / day</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map(p=><tr key={p.id}><td><div className="item-name"><span className="product-icon"><Cpu size={16}/></span><div><strong>{p.name}</strong><small>{p.sku}</small></div></div></td><td>{p.category}</td><td>{p.stock}</td><td>{p.reorder_point}</td><td>{p.daily_sales}</td><td><Badge variant={p.stock<p.reorder_point?'warn':'good'}>{p.stock<p.reorder_point?'Low stock':'In stock'}</Badge></td><td><Button variant="ghost" onClick={()=>{save.reset();setEditing(p);}}>Edit</Button></td></tr>)}</tbody></table></div>:<Empty>No products match your search.</Empty>;
    }}</QueryView>
    {editing && <dialog open className="dialog"><div className="dialog-inner"><div className="panel-heading"><h2>{editing==='new'?'Add product':'Edit '+editing.name}</h2><button aria-label="Close editor" onClick={()=>setEditing(null)}><X size={20}/></button></div><form className="form-grid" onSubmit={e=>{e.preventDefault();save.mutate(new FormData(e.currentTarget));}}>
      {editing==='new' && <><label>SKU<input name="sku" required pattern="[A-Z0-9-]+" maxLength={24}/></label><label>Name<input name="name" required maxLength={120}/></label><label>Category<input name="category" required maxLength={60}/></label><label>Unit price in NEAR<input name="price" required inputMode="decimal"/></label></>}
      <label>On hand<input type="number" min="0" name="stock" required defaultValue={editing==='new'?0:editing.stock}/></label>
      <label>Reorder point<input type="number" min="1" name="threshold" required defaultValue={editing==='new'?10:editing.reorder_point}/></label>
      <label>Daily sales<input type="number" min="0" step="0.01" name="sales" required defaultValue={editing==='new'?1:editing.daily_sales}/></label>
      <Button disabled={save.isPending}>{save.isPending?'Saving…':'Save product'}</Button>
    </form>{save.error && <ErrorState error={save.error.message}/>}</div></dialog>}
  </Panel>;
}

function Suppliers({token}: {token:string}) {
  const [filter,setFilter]=useState('');
  const suppliers=useQuery({queryKey:['suppliers'],queryFn:()=>request<Supplier[]>(token,'/suppliers')});
  const quotes=useQuery({queryKey:['quotes'],queryFn:()=>request<Quote[]>(token,'/quotes'),refetchInterval:7000});
  const products=useQuery({queryKey:['products'],queryFn:()=>request<Product[]>(token,'/products')});
  return <div className="stack"><QueryView query={suppliers}>{rows=><div className="supplier-grid">{rows.map(s=><article className="panel supplier" key={s.id}><div className="feature-icon"><Truck size={22}/></div><h2>{s.name}</h2><p className="account">{s.account}</p><div><Badge variant="good">{s.reliability}% reliability</Badge><Badge variant="info">{s.lead_days} day delivery</Badge></div></article>)}</div>}</QueryView>
    <Panel title="Supplier quotes" subtitle="Offers received and negotiated across agent runs"><div className="table-toolbar"><SearchBox value={filter} onChange={setFilter} placeholder="Search quotes"/></div><QueryView query={quotes}>{data=>{
      const rows=data.map(q=>({...q,supplier:suppliers.data?.find(s=>s.id===q.supplier_id)?.name||q.account,product:products.data?.find(p=>p.id===q.product_id)?.name||String(q.product_id)})).filter(q=>matches(filter,q.account,q.supplier,q.product,q.status));
      return rows.length ? <div className="table-wrap"><table><thead><tr><th>Supplier</th><th>Product</th><th>Units</th><th>Offer</th><th>Negotiated</th><th>Delivery</th><th>Status</th></tr></thead><tbody>{rows.map(q=><tr key={q.id}><td><strong>{q.supplier}</strong><small className="account">{q.account}</small></td><td>{q.product}</td><td>{q.quantity}</td><td>{money(q.amount)}</td><td>{q.negotiated_amount?money(q.negotiated_amount):'—'}</td><td>{q.lead_days} days</td><td><Status value={q.status}/></td></tr>)}</tbody></table></div>:<Empty>No matching quotes. Run procurement to request offers.</Empty>;
    }}</QueryView></Panel></div>;
}

function Agent({token,policy,demo,runDemo,busy}: {token:string;policy?:Policy;demo:boolean;runDemo:()=>void;busy:boolean}) {
  const query=useQuery({queryKey:['runs'],queryFn:()=>request<Run[]>(token,'/agent/runs'),refetchInterval:5000});
  return <div className="stack"><section className="panel agent-banner"><span className="feature-icon"><Bot size={24}/></span><div><h2>Autonomous procurement</h2><p>{policy?.auto_execute?'Eligible orders are sent to the policy contract automatically.':'The agent prepares orders for owner execution.'}</p></div><Status value={policy?.paused?'paused':'active'}/></section>
    {demo && <Panel title="Policy rejection demo" subtitle="Submit a redirected quote to the contract and inspect the rejection." action={<Button variant="outline" onClick={runDemo} disabled={busy || policy?.paused}><ShieldCheck size={16}/>Run rejection demo</Button>}/>}
    <Panel title="Run history" subtitle="Inventory checks, quote selection, and settlement events"><QueryView query={query}>{runs=>runs.length ? <div className="run-list">{runs.map((run,i)=><details key={run.id} open={i===0||undefined}><summary><div><strong>{run.scenario==='redirect'?'Policy rejection demo':'Procurement scan'}</strong><small>{date(run.created_at)} · {run.mode}</small></div><Status value={run.status}/></summary><ActivityFeed events={run.events}/></details>)}</div>:<Empty>No agent runs yet.</Empty>}</QueryView></Panel></div>;
}

function Orders({token}: {token:string}) {
  const [filter,setFilter]=useState('');
  const client=useQueryClient();
  const query=useQuery({queryKey:['orders'],queryFn:()=>request<Order[]>(token,'/purchase-orders'),refetchInterval:4500});
  const update=useMutation({mutationFn:({id,action}:{id:string;action:string})=>request<Order>(token,'/purchase-orders/'+id+'/'+action,'POST'),onSuccess:()=>client.invalidateQueries()});
  return <Panel title="Purchase order register" subtitle="Payments and inbound inventory"><div className="table-toolbar"><SearchBox value={filter} onChange={setFilter} placeholder="Search purchase orders"/></div>{update.error && <ErrorState error={update.error.message}/>}
    <QueryView query={query}>{data=>{
      const rows=data.filter(o=>matches(filter,o.id,o.supplier,o.product,o.status));
      return rows.length?<div className="table-wrap"><table><thead><tr><th>Order / Product</th><th>Supplier</th><th>Quantity</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map(o=><tr key={o.id}><td><strong>{o.product}</strong><small>PO-{o.id.slice(0,8).toUpperCase()}</small></td><td>{o.supplier}</td><td>{o.quantity}</td><td>{money(o.amount)}</td><td><Status value={o.status}/>{o.reason&&<small className="order-reason">{o.reason}</small>}</td><td className="order-actions">{['ready','paid'].includes(o.status)&&<Button variant="outline" disabled={update.isPending} onClick={()=>update.mutate({id:o.id,action:o.status==='ready'?'execute':'receive'})}>{o.status==='ready'?'Execute':'Receive stock'}</Button>}{o.hash&&<a className="text-link" href={explorer(o.hash)} target="_blank" rel="noreferrer">Explorer <ArrowUpRight size={13}/></a>}</td></tr>)}</tbody></table></div>:<Empty>No purchase orders match your search.</Empty>;
    }}</QueryView></Panel>;
}

function TreasuryPage({token}: {token:string}) {
  const [filter,setFilter]=useState('');
  const chain=useQuery({queryKey:['treasury'],queryFn:()=>request<Treasury>(token,'/treasury'),refetchInterval:10000});
  const tx=useQuery({queryKey:['transactions'],queryFn:()=>request<Transaction[]>(token,'/transactions'),refetchInterval:4500});
  return <div className="stack"><QueryView query={chain}>{t=>t.policy?<><div className="metrics three"><Metric label="Available" value={nearAmount(t.policy.available)} help="NEAR available to reserve" icon={Wallet} tone="blue"/><Metric label="Reserved" value={nearAmount(t.policy.reserved)} help="NEAR awaiting settlement" icon={Activity} tone="amber"/><Metric label="Spent" value={nearAmount(t.policy.spent)} help="NEAR transferred to suppliers" icon={CircleCheck} tone="green"/></div><div className="notice"><ShieldCheck size={17}/> <span className="account">{t.contract}</span> <Badge variant={t.policy.paused?'warn':'good'}>{t.policy.paused?'Paused':'Active'}</Badge></div></>:<ErrorState error={t.error || 'Treasury not available.'} retry={()=>{void chain.refetch();}}/>}</QueryView>
    <Panel title="Transactions" subtitle="Final Testnet outcomes and settlement receipts"><div className="table-toolbar"><SearchBox value={filter} onChange={setFilter} placeholder="Search transaction or order ID"/></div><QueryView query={tx}>{data=>{
      const rows=data.filter(t=>matches(filter,t.hash,t.order_id,t.status,t.receipt_id));
      return rows.length?<div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Order</th><th>Status</th><th>Receipt</th><th>Submitted</th></tr></thead><tbody>{rows.map(t=><tr key={t.id}><td><a className="text-link mono" href={explorer(t.hash)} target="_blank" rel="noreferrer">{t.hash.slice(0,13)}… <ArrowUpRight size={13}/></a><small>{t.signer}</small></td><td>PO-{t.order_id.slice(0,8).toUpperCase()}</td><td><Status value={t.status}/>{t.reason&&<small className="order-reason">{t.reason}</small>}</td><td className="mono" title={t.receipt_id||undefined}>{t.receipt_id?t.receipt_id.slice(0,13)+'…':'—'}</td><td>{date(t.created_at)}</td></tr>)}</tbody></table></div>:<Empty>No Testnet transactions have been recorded.</Empty>;
    }}</QueryView></Panel></div>;
}

function SettingsPage({token,policy,demo}: {token:string;policy?:Policy;demo:boolean}) {
  const client=useQueryClient();
  const suppliers=useQuery({queryKey:['suppliers'],queryFn:()=>request<Supplier[]>(token,'/suppliers')});
  const chain=useQuery({queryKey:['treasury'],queryFn:()=>request<Treasury>(token,'/treasury'),refetchInterval:10000});
  const [account,setAccount]=useState('');
  const [connection,setConnection]=useState<import('@hot-labs/near-connect').NearConnector|null>(null);
  const [message,setMessage]=useState('');
  const [walletError,setWalletError]=useState('');
  const [walletPending,setWalletPending]=useState(false);
  const save=useMutation({mutationFn:(value:Policy)=>request<Policy>(token,'/agent/policy','PUT',value),
    onSuccess:()=>{setMessage('Workspace permissions saved.');client.invalidateQueries();}});
  const reset=useMutation({mutationFn:()=>request(token,'/demo/reset','POST'),onSuccess:()=>{setMessage('Demo stock restored. Payment history was preserved.');client.invalidateQueries();}});
  async function connect() {
    setWalletError('');
    try {
      const {NearConnector}=await import('@hot-labs/near-connect');
      const connector=connection || new NearConnector({network:'testnet',features:{testnet:true}});
      if (!connection) {
        connector.on('wallet:signIn', event=>setAccount(event.accounts[0]?.accountId || ''));
        connector.on('wallet:signOut',()=>setAccount(''));
        setConnection(connector);
      }
      const signedIn=await connector.getConnectedWallet().catch(()=>null);
      if (signedIn?.accounts[0]) setAccount(signedIn.accounts[0].accountId);
      else await connector.connect();
    } catch (error) { setWalletError((error as Error).message); }
  }
  async function disconnect() {
    try { await connection?.disconnect(); setAccount(''); }
    catch (error) { setWalletError((error as Error).message); }
  }
  async function onchain(method:string, fields:FormData) {
    const treasury=chain.data;
    if (!connection || !treasury?.contract || !treasury.policy) return;
    setWalletPending(true); setWalletError(''); setMessage('');
    try {
      const args=method==='configure_policy'?{agent:treasury.policy.agent,suppliers:fields.getAll('approved'),
        max_order:toYocto(String(fields.get('max_order'))),budget:toYocto(String(fields.get('budget'))),paused:fields.has('paused')}: {};
      const deposit=method==='fund_treasury'?toYocto(String(fields.get('deposit'))):'0';
      if (method==='fund_treasury' && deposit==='0') throw new Error('Enter a positive funding amount.');
      const wallet=await connection.wallet();
      const result=await wallet.signAndSendTransaction({network:'testnet',signerId:account,receiverId:treasury.contract,
        actions:[{type:'FunctionCall',params:{methodName:method,args,gas:'50000000000000',deposit}}]});
      if (result && typeof result.status === 'object' && 'Failure' in result.status) throw new Error('The Testnet contract rejected this request.');
      setMessage('Wallet request submitted. Treasury refreshes as finality becomes available.');
      client.invalidateQueries({queryKey:['treasury']});
    } catch(error) { setWalletError((error as Error).message); }
    finally {setWalletPending(false);}
  }
  function update(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields=new FormData(event.currentTarget);
    setMessage('');setWalletError('');
    if ((event.nativeEvent as SubmitEvent).submitter?.getAttribute('value')==='chain') {
      void onchain('configure_policy',fields);
      return;
    }
    try {
      save.mutate({paused:fields.has('paused'),auto_execute:fields.has('auto_execute'),
        approved_accounts:fields.getAll('approved').map(String),
        max_order:toYocto(String(fields.get('max_order'))),budget:toYocto(String(fields.get('budget')))});
    } catch(error) {setWalletError((error as Error).message);}
  }
  const chainOwner=!!account && account===chain.data?.policy?.owner;
  return <div className="stack">{message&&<div className="notice" role="status"><CircleCheck size={17}/>{message}</div>}
    {walletError&&<ErrorState error={walletError}/>}
    <Panel title="Agent permissions" subtitle="Workspace limits apply before the agent signs. The NEAR contract enforces its own limits.">
      {policy?<form key={JSON.stringify(policy)} onSubmit={update} className="settings-form">
        <div className="form-grid"><label>Maximum per order in NEAR<input name="max_order" defaultValue={nearAmount(policy.max_order,24)} inputMode="decimal" required/></label><label>Total budget in NEAR<input name="budget" defaultValue={nearAmount(policy.budget,24)} inputMode="decimal" required/></label></div>
        <QueryView query={suppliers}>{rows=><fieldset><legend>Approved suppliers</legend>{rows.map(s=><label key={s.id} className="check"><input type="checkbox" name="approved" value={s.account} defaultChecked={policy.approved_accounts.includes(s.account)}/><span>{s.name}<small>{s.account}</small></span></label>)}</fieldset>}</QueryView>
        <label className="check"><input type="checkbox" name="auto_execute" defaultChecked={policy.auto_execute}/><span>Execute approved orders automatically</span></label>
        <label className="check"><input type="checkbox" name="paused" defaultChecked={policy.paused}/><span>Pause agent</span></label>
        <div className="button-group"><Button disabled={save.isPending || !suppliers.data}>{save.isPending?'Saving…':'Save workspace policy'}</Button>
          {chainOwner && <Button variant="outline" name="operation" value="chain" disabled={walletPending || !suppliers.data}>Sign on-chain policy</Button>}</div>
      </form>:<Loading/>}
      {save.error&&<ErrorState error={save.error.message}/>}
    </Panel>
    <Panel title="NEAR wallet" subtitle="Connect the contract owner account to configure, pause, or fund the treasury." action={<Button variant="outline" onClick={()=>void (account ? disconnect() : connect())}><Wallet size={16}/>{account?'Disconnect wallet':'Connect Testnet wallet'}</Button>}>
      {account && <div className="settings-form"><div className="account">{account}</div>{chainOwner ? <><form className="button-group fund-form" onSubmit={e=>{e.preventDefault();void onchain('fund_treasury',new FormData(e.currentTarget));}}><label>Fund treasury in NEAR<input name="deposit" inputMode="decimal" required/></label><Button disabled={walletPending}>Fund treasury</Button></form><Button variant="outline" disabled={walletPending} onClick={()=>void onchain('pause_agent',new FormData())}>Pause on-chain agent</Button></> : <p className="muted">Connect the account listed as owner on the deployed contract.</p>}</div>}
      {chain.data?.policy&&<div className="settings-form"><div className="account">Contract owner · {chain.data.policy.owner}</div><div className="muted">On-chain cap {money(chain.data.policy.max_order)} · Budget {money(chain.data.policy.budget)} · {chain.data.policy.paused?'Paused':'Active'}</div></div>}
    </Panel>
    {demo&&<Panel title="Demo inventory" subtitle="Restore seeded stock counts and cancel unsigned orders." action={<Button variant="outline" disabled={reset.isPending} onClick={()=>{if(window.confirm('Restore the seeded stock quantities and cancel unsigned orders?')) reset.mutate();}}>Reset demo stock</Button>}>{reset.error&&<ErrorState error={reset.error.message}/>}</Panel>}
  </div>;
}
