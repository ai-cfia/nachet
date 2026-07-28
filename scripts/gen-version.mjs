import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const OUT = "src/_versions.ts";
const pkg = JSON.parse(readFileSync("package.json", "utf8"));

if (typeof pkg.name !== "string" || pkg.name.length === 0) {
  throw new Error("Invalid name in package.json");
}

if (typeof pkg.version !== "string" || !/^\d+\.\d+\.\d+$/.test(pkg.version)) {
  throw new Error("Invalid version in package.json");
}

const fields = {
  version: pkg.version,
  name: pkg.name,
  description: pkg.description,
  versionDate: new Date().toISOString(),
};

const body = Object.entries(fields)
  .filter(([, v]) => v !== undefined)
  .map(([k, v]) => `  ${k}: ${JSON.stringify(v)},`)
  .join("\n");

// Generate the whole file so both applications use the same metadata shape.
const out = `// generated file, do not edit
export interface TsAppVersion {
  version: string;
  name: string;
  description?: string;
  versionLong?: string;
  versionDate: string;
  gitCommitHash?: string;
  gitCommitDate?: string;
  gitTag?: string;
}
export const versions: TsAppVersion = {
${body}
};
export default versions;
`;

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, out);
console.log(`Updated ${OUT} to ${pkg.version}`);
