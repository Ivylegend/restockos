import { existsSync, mkdirSync, symlinkSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

mkdirSync('node_modules/.bin', { recursive: true });
for (const [destination, source] of [
  ['node_modules/.bin/tsc', '../../../../node_modules/.bin/tsc'],
  ['node_modules/near-sdk-js', '../../../node_modules/near-sdk-js'],
]) {
  if (!existsSync(destination)) symlinkSync(source, destination);
}
const result = spawnSync('near-sdk-js', ['build', 'src/contract.ts', 'build/procurement.wasm'], { stdio: 'inherit' });
process.exitCode = result.status ?? 1;
