import {
  mkdtemp,
  readFile,
  rm,
} from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import {
  dirname,
  join,
  resolve,
} from "node:path";
import { fileURLToPath } from "node:url";

const scriptFile = fileURLToPath(import.meta.url);
const frontendRoot = resolve(dirname(scriptFile), "..");

const generatorPath = resolve(
  frontendRoot,
  "scripts",
  "generate-api-clients.mjs",
);

const committedDirectory = resolve(
  frontendRoot,
  "src",
  "lib",
  "api",
  "generated",
);

const generatedFiles = [
  "admin-api.ts",
  "widget-api.ts",
];

const temporaryDirectory = await mkdtemp(
  join(tmpdir(), "maap-api-client-check-"),
);

try {
  const result = spawnSync(
    process.execPath,
    [
      generatorPath,
      "--output-dir",
      temporaryDirectory,
    ],
    {
      cwd: frontendRoot,
      stdio: "inherit",
      env: process.env,
    },
  );

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(
      `Client generation exited with ${result.status}`,
    );
  }

  for (const filename of generatedFiles) {
    const expected = await readFile(
      join(temporaryDirectory, filename),
    );

    const committed = await readFile(
      join(committedDirectory, filename),
    );

    if (!expected.equals(committed)) {
      throw new Error(
        `${filename} has drifted. Run npm run generate:api-clients.`,
      );
    }

    console.log(`${filename}=CURRENT`);
  }

  console.log("API_CLIENT_DRIFT_CHECK=PASSED");
} finally {
  await rm(temporaryDirectory, {
    recursive: true,
    force: true,
  });
}
