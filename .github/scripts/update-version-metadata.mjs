import { readFile, writeFile } from "node:fs/promises";

const packagePath = "package.json";
const versionsPath = "src/_versions.ts";
const packageJson = JSON.parse(await readFile(packagePath, "utf8"));
const version = packageJson.version;

if (typeof version !== "string" || !/^\d+\.\d+\.\d+$/.test(version)) {
  throw new Error(`Invalid version in ${packagePath}`);
}

let versionMetadata = await readFile(versionsPath, "utf8");
versionMetadata = replaceField(versionMetadata, "version", version);
versionMetadata = replaceField(
  versionMetadata,
  "versionDate",
  new Date().toISOString(),
);

await writeFile(versionsPath, versionMetadata);
console.log(`Updated ${versionsPath} to ${version}`);

function replaceField(contents, field, value) {
  const fieldPattern = new RegExp(`(\\b${field}:\\s*)(['"])[^'"]*\\2`, "g");
  const matchingFields = contents.match(fieldPattern) ?? [];

  if (matchingFields.length !== 1) {
    throw new Error(
      `Expected one quoted ${field} field in ${versionsPath}, found ${matchingFields.length}`,
    );
  }

  return contents.replace(
    fieldPattern,
    (_match, prefix, quote) => `${prefix}${quote}${value}${quote}`,
  );
}
