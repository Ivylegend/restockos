import { readFile, mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';
import sharp from 'sharp';

const root = path.resolve(import.meta.dirname, '..');
const temp = '/tmp/restockos-video';
const raw = path.join(temp, 'screen.mov');
const voice = path.join(temp, 'voiceover.aiff');
const output = path.join(root, 'videos', 'RestockOS-Product-Demo.mp4');
const captions = JSON.parse(await readFile(path.join(root, 'videos/captions.json'), 'utf8'));
await mkdir(path.join(temp, 'graphics'), { recursive: true });

const intro = `<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101a32"/><stop offset=".55" stop-color="#1a2c54"/><stop offset="1" stop-color="#324e99"/></linearGradient><radialGradient id="glow"><stop stop-color="#91a6ff" stop-opacity=".7"/><stop offset="1" stop-color="#5c75e8" stop-opacity="0"/></radialGradient></defs><rect width="1920" height="1080" fill="url(#bg)"/><circle cx="1440" cy="510" r="460" fill="url(#glow)"/><circle cx="1440" cy="510" r="240" fill="none" stroke="#a8b8ff" stroke-opacity=".23" stroke-width="2"/><circle cx="1440" cy="510" r="330" fill="none" stroke="#82dfd0" stroke-opacity=".18" stroke-width="2" transform="rotate(25 1440 510)"/><rect x="260" y="310" width="110" height="110" rx="28" fill="#7187ff"/><text x="315" y="381" text-anchor="middle" font-family="Arial" font-size="62" font-weight="700" fill="#fff">R</text><text x="260" y="535" font-family="Arial" font-size="86" font-weight="700" letter-spacing="-4" fill="#fff">RestockOS</text><text x="266" y="605" font-family="Arial" font-size="32" fill="#cbd7f3">Autonomous procurement. Owner-controlled policy.</text><text x="266" y="870" font-family="Arial" font-size="21" letter-spacing="5" fill="#9fb1f6">NEAR TESTNET  ·  AUTONOMOUS BUSINESS</text></svg>`;
const outro = `<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101a32"/><stop offset=".55" stop-color="#1a2c54"/><stop offset="1" stop-color="#324e99"/></linearGradient></defs><rect width="1920" height="1080" fill="url(#bg)"/><circle cx="1500" cy="520" r="330" fill="none" stroke="#a8b8ff" stroke-opacity=".2" stroke-width="2"/><circle cx="1500" cy="520" r="230" fill="none" stroke="#82dfd0" stroke-opacity=".16" stroke-width="2" transform="rotate(40 1500 520)"/><rect x="760" y="285" width="120" height="120" rx="30" fill="#7187ff"/><text x="820" y="363" text-anchor="middle" font-family="Arial" font-size="68" font-weight="700" fill="#fff">R</text><text x="960" y="370" font-family="Arial" font-size="78" font-weight="700" letter-spacing="-3" fill="#fff">RestockOS</text><text x="960" y="440" font-family="Arial" font-size="29" fill="#cbd7f3">Autonomous procurement. Protected by policy.</text><text x="960" y="850" font-family="Arial" font-size="20" letter-spacing="4" fill="#9fb1f6">NEAR HACKATHON 2026  ·  TESTNET ONLY</text></svg>`;

const introPath = path.join(temp, 'graphics/intro.png');
const outroPath = path.join(temp, 'graphics/outro.png');
await sharp(Buffer.from(intro)).png().toFile(introPath);
await sharp(Buffer.from(outro)).png().toFile(outroPath);

const imageInputs = [];
const overlays = [];
for (let index = 0; index < captions.length; index++) {
  const caption = captions[index];
  const escaped = caption.text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  const svg = `<svg width="1620" height="105" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="2" width="1616" height="101" rx="18" fill="#0c1731" fill-opacity=".91" stroke="#8197e7" stroke-opacity=".6"/><rect x="24" y="28" width="8" height="49" rx="4" fill="#7f95ff"/><text x="70" y="66" font-family="Arial" font-size="31" font-weight="600" fill="#f7f9ff">${escaped}</text></svg>`;
  const image = path.join(temp, `graphics/caption-${index}.png`);
  await sharp(Buffer.from(svg)).png().toFile(image);
  imageInputs.push(image);
  overlays.push({ image, start: caption.start, end: caption.end });
}

const callouts = [
  { text: 'PUBLIC SANDBOX  ·  SIMULATED', start: 66, end: 80, color: '#1e8b75' },
  { text: 'VERIFIED TESTNET RECEIPTS', start: 88, end: 103, color: '#405dd5' },
];
for (let index = 0; index < callouts.length; index++) {
  const item = callouts[index];
  const svg = `<svg width="640" height="72" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="2" width="636" height="68" rx="14" fill="#101b36" fill-opacity=".94" stroke="${item.color}" stroke-width="3"/><circle cx="34" cy="36" r="8" fill="${item.color}"/><text x="62" y="44" font-family="Arial" font-size="23" font-weight="700" letter-spacing="1" fill="#f7f9ff">${item.text}</text></svg>`;
  const image = path.join(temp, `graphics/callout-${index}.png`);
  await sharp(Buffer.from(svg)).png().toFile(image);
  imageInputs.push(image);
  overlays.push({ image, start: item.start, end: item.end, callout: true });
}

const args = ['-y', '-i', raw];
for (const image of imageInputs) args.push('-loop', '1', '-t', '103', '-i', image);
const introIndex = 1 + imageInputs.length;
args.push('-loop', '1', '-t', '4', '-i', introPath);
const outroIndex = introIndex + 1;
args.push('-loop', '1', '-t', '4', '-i', outroPath);
args.push('-i', voice);
const voiceIndex = outroIndex + 1;
args.push('-f', 'lavfi', '-i', 'aevalsrc=0.018*sin(2*PI*110*t)+0.012*sin(2*PI*164.81*t)+0.009*sin(2*PI*220*t)+0.006*sin(2*PI*261.63*t):s=48000:d=111');
const musicIndex = voiceIndex + 1;

const filters = [
  '[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p[vbase0]',
];
let current = 'vbase0';
for (let index = 0; index < overlays.length; index++) {
  const next = `v${index + 1}`;
  const item = overlays[index];
  const y = item.callout ? 58 : 920;
  const x = item.callout ? 75 : 150;
  filters.push(`[${current}][${index + 1}:v]overlay=${x}:${y}:eof_action=pass:enable='between(t,${item.start},${item.end})'[${next}]`);
  current = next;
}
filters.push(`[${current}]setpts=PTS-STARTPTS,fps=30,format=yuv420p[footage]`);
filters.push(`[${introIndex}:v]fps=30,format=yuv420p,setpts=PTS-STARTPTS[intro]`);
filters.push(`[${outroIndex}:v]fps=30,format=yuv420p,setpts=PTS-STARTPTS[outro]`);
filters.push('[intro][footage]xfade=transition=fade:duration=0.7:offset=3.3[part]');
filters.push('[part][outro]xfade=transition=fade:duration=0.7:offset=105.6[vout]');
filters.push(`[${voiceIndex}:a]volume=1.0,afade=t=in:st=0:d=1[voice]`);
filters.push(`[${musicIndex}:a]volume=0.24,lowpass=f=1500,afade=t=in:st=0:d=2,afade=t=out:st=107:d=3[music]`);
filters.push('[voice][music]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.93[aout]');
args.push('-filter_complex', filters.join(';'), '-map', '[vout]', '-map', '[aout]', '-t', '110', '-r', '30',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', output);

await new Promise((resolve, reject) => {
  const process = spawn('ffmpeg', args, { stdio: 'inherit' });
  process.on('error', reject);
  process.on('close', code => code === 0 ? resolve() : reject(new Error(`ffmpeg exited with ${code}`)));
});
console.log(output);
