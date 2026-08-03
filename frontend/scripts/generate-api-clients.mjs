import {
  mkdtemp,
  mkdir,
  readFile,
  rm,
  writeFile,
} from "node:fs/promises";
import { existsSync } from "node:fs";
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
const repositoryRoot = resolve(frontendRoot, "..");
const canonicalPath = resolve(
  repositoryRoot,
  "backend",
  "openapi.json",
);

const defaultOutputDirectory = resolve(
  frontendRoot,
  "src",
  "lib",
  "api",
  "generated",
);

const HTTP_METHODS = new Set([
  "get",
  "post",
  "put",
  "patch",
  "delete",
  "options",
  "head",
]);

const WIDGET_PATHS = new Set([
  "/api/widget/bootstrap",
  "/api/chat",
  "/health",
  "/ready",
]);

function parseOutputDirectory() {
  const index = process.argv.indexOf("--output-dir");

  if (index === -1) {
    return defaultOutputDirectory;
  }

  const value = process.argv[index + 1];

  if (!value) {
    throw new Error("--output-dir requires a path.");
  }

  return resolve(process.cwd(), value);
}

function clone(value) {
  return structuredClone(value);
}

function deepSort(value) {
  if (Array.isArray(value)) {
    return value.map(deepSort);
  }

  if (
    value === null ||
    typeof value !== "object"
  ) {
    return value;
  }

  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [
        key,
        deepSort(value[key]),
      ]),
  );
}

function collectReferences(value, references) {
  if (Array.isArray(value)) {
    for (const item of value) {
      collectReferences(item, references);
    }

    return;
  }

  if (
    value === null ||
    typeof value !== "object"
  ) {
    return;
  }

  if (
    typeof value.$ref === "string" &&
    value.$ref.startsWith("#/components/")
  ) {
    references.add(value.$ref);
  }

  for (const item of Object.values(value)) {
    collectReferences(item, references);
  }
}

function decodePointerToken(value) {
  return value
    .replaceAll("~1", "/")
    .replaceAll("~0", "~");
}

function parseComponentReference(reference) {
  const match = reference.match(
    /^#\/components\/([^/]+)\/(.+)$/,
  );

  if (!match) {
    return null;
  }

  return {
    section: decodePointerToken(match[1]),
    name: decodePointerToken(match[2]),
  };
}

function pruneComponents(
  canonical,
  paths,
  allowedSecuritySchemes,
) {
  const result = {};
  const references = new Set();
  const processed = new Set();

  collectReferences(paths, references);

  const sourceSecuritySchemes =
    canonical.components?.securitySchemes ?? {};

  if (allowedSecuritySchemes.length > 0) {
    result.securitySchemes = {};

    for (const name of [...allowedSecuritySchemes].sort()) {
      const scheme = sourceSecuritySchemes[name];

      if (!scheme) {
        throw new Error(
          `Missing security scheme: ${name}`,
        );
      }

      result.securitySchemes[name] = clone(scheme);
      collectReferences(scheme, references);
    }
  }

  while (true) {
    const pending = [...references]
      .filter((reference) => !processed.has(reference))
      .sort();

    if (pending.length === 0) {
      break;
    }

    for (const reference of pending) {
      processed.add(reference);

      const parsed = parseComponentReference(reference);

      if (!parsed) {
        continue;
      }

      const source =
        canonical.components?.[parsed.section]?.[parsed.name];

      if (!source) {
        throw new Error(
          `Unresolved component reference: ${reference}`,
        );
      }

      result[parsed.section] ??= {};
      result[parsed.section][parsed.name] = clone(source);

      collectReferences(source, references);
    }
  }

  return deepSort(result);
}

function selectPaths(canonical, predicate, transform) {
  const paths = {};

  for (const path of Object.keys(canonical.paths).sort()) {
    if (!predicate(path)) {
      continue;
    }

    const pathItem = clone(canonical.paths[path]);

    if (transform) {
      transform(path, pathItem);
    }

    paths[path] = pathItem;
  }

  return deepSort(paths);
}

function countOperations(paths) {
  let count = 0;

  for (const pathItem of Object.values(paths)) {
    for (const method of Object.keys(pathItem)) {
      if (HTTP_METHODS.has(method)) {
        count += 1;
      }
    }
  }

  return count;
}

function validateOperationSecurity(
  spec,
  allowedSecuritySchemes,
) {
  const allowed = new Set(allowedSecuritySchemes);

  for (const [path, pathItem] of Object.entries(spec.paths)) {
    for (const [method, operation] of Object.entries(pathItem)) {
      if (!HTTP_METHODS.has(method)) {
        continue;
      }

      const security =
        operation.security ?? spec.security ?? [];

      for (const requirement of security) {
        for (const name of Object.keys(requirement)) {
          if (!allowed.has(name)) {
            throw new Error(
              `Forbidden security scheme ${name} in ` +
              `${method.toUpperCase()} ${path}`,
            );
          }
        }
      }
    }
  }
}

function buildAdminSpec(canonical) {
  const paths = selectPaths(
    canonical,
    (path) =>
      path.startsWith("/api/admin/") ||
      path.startsWith("/api/knowledge-bases") ||
      path === "/health" ||
      path === "/ready",
  );

  const securitySchemes = [
    "AdminJWT",
    "InternalAdminKey",
    "TenantApiKey",
  ];

  const spec = {
    openapi: canonical.openapi,
    info: {
      ...clone(canonical.info),
      title: `${canonical.info.title} Admin API`,
    },
    paths,
    components: pruneComponents(
      canonical,
      paths,
      securitySchemes,
    ),
  };

  validateOperationSecurity(spec, securitySchemes);

  for (const path of Object.keys(spec.paths)) {
    if (
      path === "/api/chat" ||
      path.startsWith("/api/widget/")
    ) {
      throw new Error(
        `Browser Widget path leaked into Admin contract: ${path}`,
      );
    }
  }

  return deepSort(spec);
}

function buildWidgetSpec(canonical) {
  const paths = selectPaths(
    canonical,
    (path) => WIDGET_PATHS.has(path),
    (path, pathItem) => {
      if (path === "/api/chat" && pathItem.post) {
        pathItem.post.security = [
          { WidgetToken: [] },
        ];
      }
    },
  );

  const securitySchemes = ["WidgetToken"];

  const spec = {
    openapi: canonical.openapi,
    info: {
      ...clone(canonical.info),
      title: `${canonical.info.title} Browser Widget API`,
    },
    paths,
    components: pruneComponents(
      canonical,
      paths,
      securitySchemes,
    ),
  };

  validateOperationSecurity(spec, securitySchemes);

  for (const path of Object.keys(spec.paths)) {
    if (
      path.startsWith("/api/admin/") ||
      path.startsWith("/api/knowledge-bases")
    ) {
      throw new Error(
        `Privileged path leaked into Widget contract: ${path}`,
      );
    }
  }

  const chatSecurity =
    spec.paths["/api/chat"]?.post?.security;

  if (
    JSON.stringify(chatSecurity) !==
    JSON.stringify([{ WidgetToken: [] }])
  ) {
    throw new Error(
      "Widget chat must require WidgetToken only.",
    );
  }

  return deepSort(spec);
}

function runGenerator(inputPath, outputPath) {
  const localBinary = resolve(
    frontendRoot,
    "node_modules",
    ".bin",
    process.platform === "win32"
      ? "openapi-typescript.cmd"
      : "openapi-typescript",
  );

  let command;
  let args;

  if (existsSync(localBinary)) {
    command = localBinary;
    args = [
      inputPath,
      "-o",
      outputPath,
    ];
  } else {
    const npmCliCandidates = [
      process.env.npm_execpath,
      resolve(
        dirname(process.execPath),
        "node_modules",
        "npm",
        "bin",
        "npm-cli.js",
      ),
    ].filter(Boolean);

    const npmCli = npmCliCandidates.find((candidate) =>
      existsSync(candidate),
    );

    if (!npmCli) {
      throw new Error(
        "Could not locate npm-cli.js for pinned generator bootstrap.",
      );
    }

    command = process.execPath;
    args = [
      npmCli,
      "exec",
      "--yes",
      "--package=openapi-typescript@7.13.0",
      "--",
      "openapi-typescript",
      inputPath,
      "-o",
      outputPath,
    ];
  }

  const result = spawnSync(command, args, {
    cwd: frontendRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      NODE_OPTIONS:
        process.env.NODE_OPTIONS ??
        "--max-old-space-size=1024",
      npm_config_audit: "false",
      npm_config_fund: "false",
      npm_config_omit: "optional",
    },
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(
      `openapi-typescript exited with ${result.status}`,
    );
  }
}

async function normalizeGeneratedFile(
  temporaryPath,
  finalPath,
  sourceLabel,
) {
  const generated = await readFile(
    temporaryPath,
    "utf8",
  );

  const normalized = generated
    .replaceAll("\r\n", "\n")
    .replaceAll("\r", "\n")
    .trimEnd();

  const header = [
    "/**",
    " * Generated file. Do not edit manually.",
    ` * Source: ${sourceLabel}`,
    " */",
    "",
  ].join("\n");

  await mkdir(dirname(finalPath), {
    recursive: true,
  });

  await writeFile(
    finalPath,
    `${header}${normalized}\n`,
    {
      encoding: "utf8",
    },
  );
}

async function main() {
  const outputDirectory = parseOutputDirectory();

  const canonical = JSON.parse(
    await readFile(canonicalPath, "utf8"),
  );

  const adminSpec = buildAdminSpec(canonical);
  const widgetSpec = buildWidgetSpec(canonical);

  const temporaryDirectory = await mkdtemp(
    join(tmpdir(), "maap-api-clients-"),
  );

  try {
    const adminSpecPath = join(
      temporaryDirectory,
      "admin-openapi.json",
    );

    const widgetSpecPath = join(
      temporaryDirectory,
      "widget-openapi.json",
    );

    const adminOutputPath = join(
      temporaryDirectory,
      "admin-api.ts",
    );

    const widgetOutputPath = join(
      temporaryDirectory,
      "widget-api.ts",
    );

    await writeFile(
      adminSpecPath,
      `${JSON.stringify(adminSpec, null, 2)}\n`,
      "utf8",
    );

    await writeFile(
      widgetSpecPath,
      `${JSON.stringify(widgetSpec, null, 2)}\n`,
      "utf8",
    );

    runGenerator(adminSpecPath, adminOutputPath);
    runGenerator(widgetSpecPath, widgetOutputPath);

    await normalizeGeneratedFile(
      adminOutputPath,
      join(outputDirectory, "admin-api.ts"),
      "backend/openapi.json ? privileged server/admin surface",
    );

    await normalizeGeneratedFile(
      widgetOutputPath,
      join(outputDirectory, "widget-api.ts"),
      "backend/openapi.json ? browser-safe Widget surface",
    );
  } finally {
    await rm(temporaryDirectory, {
      recursive: true,
      force: true,
    });
  }

  console.log(
    `ADMIN_PATH_COUNT=${Object.keys(adminSpec.paths).length}`,
  );

  console.log(
    `ADMIN_OPERATION_COUNT=${countOperations(adminSpec.paths)}`,
  );

  console.log(
    `WIDGET_PATH_COUNT=${Object.keys(widgetSpec.paths).length}`,
  );

  console.log(
    `WIDGET_OPERATION_COUNT=${countOperations(widgetSpec.paths)}`,
  );

  console.log(`API_CLIENT_OUTPUT=${outputDirectory}`);
}

await main();
