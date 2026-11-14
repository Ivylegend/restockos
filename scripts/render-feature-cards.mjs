// Original vector composition around actual application screenshots.
import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {ArrowUpRight,Boxes,LayoutDashboard,PackageSearch,Truck,Bot,ClipboardList,ShieldCheck,Settings2} from 'lucide-react';

const root=path.resolve(import.meta.dirname,'..');
const output=path.join(root,'docs/media/feature-cards');
const sources=path.join(output,'sources');
const sourceDir=process.env.SCREENSHOT_DIR||'/tmp/restockos-product-review';
await mkdir(sources,{recursive:true});
const cards=[
 {file:'01-restockos',source:'dashboard',icon:Boxes,kicker:'AUTONOMOUS PROCUREMENT',heading:'Empty shelves?',serif:'Meet RestockOS.',label:'From low stock to a purchase order.',proof:['AI prepares the order.','NEAR enforces the limits.'],footer:'A working sandbox. Verifiable Testnet evidence.',focus:[292,322,736,312],badge:'PROJECT OVERVIEW'},
 {file:'02-overview',source:'dashboard',icon:LayoutDashboard,kicker:'OVERVIEW DASHBOARD',heading:'See the risk.',serif:'Restock in time.',label:'Know what needs attention first.',proof:['16 products tracked.','3 shortages surfaced.'],footer:'Stock coverage, open orders and a visible activity feed.',focus:[292,166,945,137],badge:'OPERATIONS, AT A GLANCE'},
 {file:'03-inventory',source:'inventory',icon:PackageSearch,kicker:'INVENTORY MANAGEMENT',heading:'Every product.',serif:'One clear signal.',label:'Three left. Reorder at twenty.',proof:['Search your catalog.','Spot low stock early.'],footer:'On-hand stock, reorder points and daily sales estimates.',focus:[292,359,1262,106],badge:'CATCH THE SHORTAGE'},
 {file:'04-suppliers',source:'quotes',icon:Truck,kicker:'SUPPLIERS & QUOTATIONS',heading:'Three offers.',serif:'A smarter choice.',label:'Price. Delivery. Reliability.',proof:['Compare three quotes.','See the counteroffer.'],footer:'Deterministic demo quotes. Supplier integrations are future work.',focus:[292,716,1262,69],badge:'A COMPLIANT SUPPLIER'},
 {file:'05-agent',source:'agent',icon:Bot,kicker:'AI PROCUREMENT AGENT',heading:'From shortage',serif:'to purchase order.',label:'See the reason behind each step.',proof:['Scan. Compare. Negotiate.','Follow the decision log.'],footer:'This public sandbox run is simulated and sends no NEAR.',focus:[310,275,1233,324],badge:'RUN THE PUBLIC SANDBOX'},
 {file:'06-orders',source:'orders',icon:ClipboardList,kicker:'PURCHASE ORDERS',heading:'Know what',serif:'you are buying.',label:'Every order. Every status.',proof:['Review the chosen offer.','Confirm live execution.'],footer:'Sandbox orders are labeled simulated. Live actions need authorization.',focus:[292,358,1262,150],badge:'SIMULATION IS EXPLICIT'},
 {file:'07-treasury',source:'paid',icon:ShieldCheck,kicker:'TREASURY & TRANSACTIONS',heading:'Real receipts.',serif:'Real boundaries.',label:'One payment settled. One redirect failed.',proof:['Verify the Testnet hash.','Inspect the rejection.'],footer:'Historical Testnet evidence, separate from sandbox execution.',focus:[292,613,1262,158],badge:'VERIFIED ON NEAR TESTNET'},
 {file:'08-settings',source:'admin',icon:Settings2,kicker:'SETTINGS & PERMISSIONS',heading:'Your business.',serif:'Your spending rules.',label:'Approved suppliers. Caps. Pause.',proof:['Set the financial limits.','Keep the owner in control.'],footer:'Seeded admin controls. No credentials are shown.',focus:[310,211,1225,259],badge:'OWNER-CONTROLLED POLICY'}
];
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const txt=(s,x,y,size,color='#fbfbff',attrs='')=>`<text x="${x}" y="${y}" font-family="Arial" font-size="${size}" fill="${color}" ${attrs}>${escape(s)}</text>`;
const icon=(Component,x,y,size=28,color='#dcf98b')=>`<g transform="translate(${x} ${y})">${renderToStaticMarkup(createElement(Component,{width:size,height:size,color,strokeWidth:1.8}))}</g>`;
const mark=(await readFile(path.join(root,'apps/web/app/icon.svg'))).toString().replace('<svg ','<svg x="54" y="49" width="42" height="42" ');
const manifest=[];

for(const [index,card] of cards.entries()){
 const source=path.join(sources,card.source+'.png');
 try{await copyFile(path.join(sourceDir,card.source+'-preview.png'),source);}catch(error){if(error.code!=='ENOENT')throw error;await readFile(source);}
 const image='data:image/png;base64,'+(await readFile(source)).toString('base64');
 const [fx,fy,fw,fh]=card.focus;const sx=48,sy=566,scale=984/1600;
 const serifSize=card.serif.length>18?89:100;
 const labelSize=card.label.length>39?27:30;
 const labelWidth=Math.min(968,Math.max(640,card.label.length*labelSize*.51+64));
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
 <defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0c0a1d"/><stop offset=".6" stop-color="#11122e"/><stop offset="1" stop-color="#081526"/></linearGradient>
  <radialGradient id="glow"><stop stop-color="#4d4ac6" stop-opacity=".3"/><stop offset="1" stop-color="#4d4ac6" stop-opacity="0"/></radialGradient>
  <filter id="blur"><feGaussianBlur stdDeviation="4"/></filter>
  <filter id="shadow" x="-15%" y="-30%" width="140%" height="170%"><feDropShadow dx="0" dy="14" stdDeviation="20" flood-color="#000" flood-opacity=".55"/></filter>
  <clipPath id="screen"><rect x="48" y="566" width="984" height="553.5" rx="0"/></clipPath>
  <pattern id="grid" width="62" height="62" patternUnits="userSpaceOnUse"><path d="M62 0H0V62" fill="none" stroke="#a9a7db" stroke-opacity=".04"/></pattern>
 </defs>
 <rect width="1080" height="1350" fill="url(#bg)"/>
 <image href="${image}" x="-200" y="300" width="1480" height="833" opacity=".075" filter="url(#blur)"/>
 <rect width="1080" height="1350" fill="url(#grid)"/>
 <ellipse cx="930" cy="190" rx="650" ry="580" fill="url(#glow)"/>
 <path d="M0 1300C140 1120 300 1260 440 1100S840 1120 1080 880" fill="none" stroke="#8d9fff" stroke-opacity=".12"/>
 ${mark}${txt('RESTOCKOS',111,78,23,'#fff','font-weight="700" letter-spacing="2"')}
 ${txt(String(index+1).padStart(2,'0')+' / 08',1025,78,22,'#adacc2','text-anchor="end" font-weight="700"')}
 ${txt(card.kicker,60,157,19,'#dcf98b','font-weight="700" letter-spacing="4"')}
 ${txt(card.heading,56,252,79,'#fff','font-weight="700" letter-spacing="-4"')}
 <text x="55" y="365" font-family="Georgia" font-size="${serifSize}" font-style="italic" letter-spacing="-4" fill="#f6f4fc">${escape(card.serif)}</text>
 <g opacity=".9">${icon(card.icon,62,397,25)}${txt(card.badge,103,416,17,'#b9b7cd','font-weight="700" letter-spacing="1.7"')}</g>
 <g transform="rotate(-1.5 60 472)" filter="url(#shadow)"><rect x="60" y="451" width="${labelWidth}" height="65" fill="#f7f6f1"/>${txt(card.label,83,494,labelSize,'#111020','font-weight="700" letter-spacing="-1"')}</g>
 <g filter="url(#shadow)"><rect x="46" y="528" width="988" height="596" rx="25" fill="#212139" stroke="#53536e" stroke-width="1.5"/><rect x="48" y="530" width="984" height="38" rx="24" fill="#24243c"/><rect x="48" y="550" width="984" height="20" fill="#24243c"/>
  <circle cx="71" cy="549" r="4" fill="#8c8ba3"/><circle cx="87" cy="549" r="4" fill="#6c6c87"/><circle cx="103" cy="549" r="4" fill="#50526f"/>
  ${txt('RESTOCKOS  /  '+card.kicker,540,554,11,'#c1bed3','text-anchor="middle" letter-spacing="1.5"')}
  <image href="${image}" x="48" y="566" width="984" height="553.5" clip-path="url(#screen)"/>
  <rect x="${sx+fx*scale}" y="${sy+fy*scale}" width="${fw*scale}" height="${fh*scale}" rx="7" fill="#dcf98b" fill-opacity=".035" stroke="#b6df55" stroke-width="2.5"/>
 </g>
 <path d="M1016 1010v29h-29" fill="none" stroke="#dcf98b" stroke-width="2.2"/>
 <g filter="url(#shadow)"><rect x="470" y="1070" width="570" height="111" fill="#dcf98b"/>
  ${txt(card.proof[0],497,1114,30,'#11151b','font-weight="700" letter-spacing="-1"')}
  ${txt(card.proof[1],497,1153,30,'#11151b','font-weight="700" letter-spacing="-1"')}
 </g>
 ${txt(card.footer,60,1220,18,'#aaa9c4')}
 <rect x="60" y="1254" width="960" height="1" fill="#8d8da7" fill-opacity=".23"/>
 ${icon(ArrowUpRight,62,1280,22)}${txt(index===0?'Built at NEAR HACKATHON':'Explore '+(['Overview','Overview','Inventory','Suppliers','Procurement agent','Purchase orders','Treasury','Settings'][index]),98,1299,20,'#e5e5f4','font-weight="700"')}
 ${txt('TESTNET ONLY',1022,1298,15,'#a2a2bd','text-anchor="end" letter-spacing="2"')}
 </svg>`;
 await writeFile(path.join(output,card.file+'.svg'),svg);
 await sharp(Buffer.from(svg)).png().toFile(path.join(output,card.file+'.png'));
 manifest.push({file:card.file+'.png',alt:card.kicker+': '+card.label+' '+card.proof.join(' ')+' '+card.footer});
 console.log('Rendered '+card.file);
}
const thumbs=await Promise.all(manifest.map(async(card,i)=>({input:await sharp(path.join(output,card.file)).resize(270,338).toBuffer(),left:(i%4)*270,top:Math.floor(i/4)*338})));
await sharp({create:{width:1080,height:676,channels:3,background:'#0c0a1d'}}).composite(thumbs).png().toFile(path.join(output,'contact-sheet.png'));
await writeFile(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RestockOS feature cards</title><style>body{margin:0;background:#0c0a1d;color:#f4f3ff;font:16px Arial}header{max-width:1400px;margin:45px auto;padding:0 24px}h1{font-size:44px;letter-spacing:-2px}p{color:#b4b2ce;line-height:1.6}main{max-width:1400px;margin:0 auto;padding:24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:24px}figure{margin:0}img{width:100%;border-radius:12px}figcaption{font-size:13px;color:#b4b2ce;margin:10px 2px 28px;line-height:1.5}a{color:#dcf98b}</style><header><h1>RestockOS, in eight frames.</h1><p>Actual application screenshots, annotated for a product walkthrough. Sandbox orders are simulated. Treasury receipts are historical Testnet evidence.</p><a href="RestockOS-Feature-Cards.zip">Download all eight PNGs</a></header><main>${manifest.map(card=>`<figure><a href="${card.file}"><img src="${card.file}" alt="${escape(card.alt)}"></a><figcaption>${escape(card.alt)}</figcaption></figure>`).join('')}</main></html>`;
await writeFile(path.join(output,'index.html'),html);
