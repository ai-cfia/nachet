import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const OUT = 'src/_versions.ts';

const pkg = JSON.parse(readFileSync('package.json', 'utf8'));

const git = (cmd) => {
  try {
    return execSync(cmd, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim() || undefined;
  } catch {
    return undefined;
  }
};

const hash = git('git rev-parse --short HEAD');

const fields = {
  version: pkg.version,
  name: pkg.name,
  description: pkg.description,
  versionLong: hash ? `${pkg.version}-${hash}` : undefined,
  versionDate: new Date().toISOString(),
};

const body = Object.entries(fields)
  .filter(([, v]) => v !== undefined)
  .map(([k, v]) => `    ${k}: ${JSON.stringify(v)},`)
  .join('\n');

const out = `// generated file, do not edit
export interface TsAppVersion {
    version: string;
    name: string;
    description?: string;
    versionLong?: string;
    versionDate: string;
}

export const versions: TsAppVersion = {
${body}
};

export default versions;
`;

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, out);