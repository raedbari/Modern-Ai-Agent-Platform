#!/usr/bin/env node
/**
 * Generate typed TypeScript API clients from OpenAPI schema.
 * 
 * Creates two separate clients:
 * 1. Admin Client - for server-side admin operations (includes admin endpoints)
 * 2. Widget Client - for browser-safe widget operations (excludes admin secrets)
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { readFile, writeFile, mkdir } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const execAsync = promisify(exec);
const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, '..');
const backendRoot = join(projectRoot, '..', 'backend');

const OPENAPI_PATH = join(backendRoot, 'openapi.json');
const ADMIN_CLIENT_OUTPUT = join(projectRoot, 'src', 'lib', 'api', 'admin-client.types.ts');
const WIDGET_CLIENT_OUTPUT = join(projectRoot, 'src', 'lib', 'api', 'widget-client.types.ts');

/**
 * Filter OpenAPI schema to include only specific path prefixes.
 */
function filterSchema(schema, pathPrefixes) {
  const filtered = JSON.parse(JSON.stringify(schema)); // Deep clone
  
  filtered.paths = {};
  for (const [path, pathItem] of Object.entries(schema.paths || {})) {
    if (pathPrefixes.some(prefix => path.startsWith(prefix))) {
      filtered.paths[path] = pathItem;
    }
  }
  
  return filtered;
}

/**
 * Filter security schemes to only include safe ones for browser.
 */
function filterSecuritySchemes(schema, allowedSchemes) {
  const filtered = JSON.parse(JSON.stringify(schema));
  
  if (filtered.components?.securitySchemes) {
    const schemes = {};
    for (const [name, def] of Object.entries(filtered.components.securitySchemes)) {
      if (allowedSchemes.includes(name)) {
        schemes[name] = def;
      }
    }
    filtered.components.securitySchemes = schemes;
  }
  
  return filtered;
}

/**
 * Generate TypeScript types using openapi-typescript.
 */
async function generateTypes(schemaPath, outputPath) {
  try {
    const command = `npx openapi-typescript "${schemaPath}" -o "${outputPath}"`;
    await execAsync(command, { cwd: projectRoot });
    console.log(`✓ Generated: ${outputPath}`);
  } catch (error) {
    console.error(`✗ Failed to generate ${outputPath}:`, error.message);
    throw error;
  }
}

/**
 * Add helper types and client wrapper to generated types.
 */
async function enhanceGeneratedTypes(filePath, clientType) {
  const content = await readFile(filePath, 'utf-8');
  
  const enhanced = `${content}

/**
 * ${clientType} API Client Types
 * 
 * Auto-generated from OpenAPI schema. DO NOT EDIT MANUALLY.
 * To regenerate: npm run generate:api-clients
 */

// Re-export paths for easier imports
export type Paths = paths;
export type Components = components;

// Helper type to extract response type from an operation
export type ResponseType<T> = T extends { responses: { 200: { content: { 'application/json': infer R } } } }
  ? R
  : never;

// Helper type to extract request body type from an operation
export type RequestBody<T> = T extends { requestBody: { content: { 'application/json': infer R } } }
  ? R
  : never;

// Helper type to extract parameters from an operation
export type PathParams<T> = T extends { parameters: { path: infer P } } ? P : never;
export type QueryParams<T> = T extends { parameters: { query: infer Q } } ? Q : never;
`;
  
  await writeFile(filePath, enhanced, 'utf-8');
  console.log(`✓ Enhanced: ${filePath}`);
}

/**
 * Create client wrapper modules.
 */
async function createClientWrappers() {
  // Admin Client Wrapper
  const adminWrapper = `/**
 * Admin API Client
 * 
 * Server-side only - contains admin authentication and privileged operations.
 * **Never import this in browser/client-side code.**
 * 
 * Security schemes available:
 * - AdminJWT: Bearer token from login endpoint
 * - InternalAdminKey: Legacy X-Admin-Key header (deprecated)
 * - TenantApiKey: Server-side tenant API key
 */

export * from './admin-client.types';
export type { Paths as AdminPaths, Components as AdminComponents } from './admin-client.types';

/**
 * Base URL for admin API calls.
 * Override via NEXT_PUBLIC_API_URL or use default localhost.
 */
export const ADMIN_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Check if code is running on server (Node.js environment).
 */
export const isServer = typeof window === 'undefined';

// Runtime check to prevent accidental browser usage
if (!isServer) {
  console.error(
    'Admin API client imported in browser! ' +
    'This exposes admin credentials. Use widget-client instead.'
  );
}
`;

  // Widget Client Wrapper
  const widgetWrapper = `/**
 * Widget API Client
 * 
 * Browser-safe client for widget/public operations.
 * Only includes endpoints safe for browser use.
 * 
 * Security schemes available:
 * - WidgetToken: Short-lived browser-safe JWT from bootstrap endpoint
 */

export * from './widget-client.types';
export type { Paths as WidgetPaths, Components as WidgetComponents } from './widget-client.types';

/**
 * Base URL for widget API calls.
 */
export const WIDGET_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
`;

  await mkdir(join(projectRoot, 'src', 'lib', 'api'), { recursive: true });
  await writeFile(join(projectRoot, 'src', 'lib', 'api', 'admin-client.ts'), adminWrapper);
  await writeFile(join(projectRoot, 'src', 'lib', 'api', 'widget-client.ts'), widgetWrapper);
  
  console.log('✓ Created client wrappers');
}

/**
 * Main generation flow.
 */
async function main() {
  try {
    console.log('🚀 Generating API clients from OpenAPI schema...\n');
    
    // Load base schema
    const baseSchema = JSON.parse(await readFile(OPENAPI_PATH, 'utf-8'));
    console.log(`✓ Loaded OpenAPI schema: ${OPENAPI_PATH}`);
    console.log(`  Paths: ${Object.keys(baseSchema.paths || {}).length}`);
    console.log(`  Schemas: ${Object.keys(baseSchema.components?.schemas || {}).length}\n`);
    
    // Create output directories
    await mkdir(dirname(ADMIN_CLIENT_OUTPUT), { recursive: true });
    await mkdir(dirname(WIDGET_CLIENT_OUTPUT), { recursive: true });
    
    // Generate Admin Client (all endpoints)
    console.log('📝 Generating Admin Client (server-side only)...');
    const adminSchema = filterSchema(baseSchema, ['/api/admin', '/api/chat', '/api/knowledge-bases', '/health', '/ready']);
    const adminSchemaPath = join(projectRoot, '.temp-admin-schema.json');
    await writeFile(adminSchemaPath, JSON.stringify(adminSchema, null, 2));
    await generateTypes(adminSchemaPath, ADMIN_CLIENT_OUTPUT);
    await enhanceGeneratedTypes(ADMIN_CLIENT_OUTPUT, 'Admin');
    
    // Generate Widget Client (browser-safe endpoints only)
    console.log('\n📝 Generating Widget Client (browser-safe)...');
    const widgetSchema = filterSchema(baseSchema, ['/api/widget', '/api/chat', '/health']);
    const widgetSchemaFiltered = filterSecuritySchemes(widgetSchema, ['WidgetToken']);
    const widgetSchemaPath = join(projectRoot, '.temp-widget-schema.json');
    await writeFile(widgetSchemaPath, JSON.stringify(widgetSchemaFiltered, null, 2));
    await generateTypes(widgetSchemaPath, WIDGET_CLIENT_OUTPUT);
    await enhanceGeneratedTypes(WIDGET_CLIENT_OUTPUT, 'Widget');
    
    // Create wrapper modules
    console.log('\n📦 Creating client wrappers...');
    await createClientWrappers();
    
    // Cleanup temp files
    await execAsync(`rm -f "${adminSchemaPath}" "${widgetSchemaPath}"`);
    
    console.log('\n✅ API clients generated successfully!\n');
    console.log('Generated files:');
    console.log(`  - ${ADMIN_CLIENT_OUTPUT}`);
    console.log(`  - ${WIDGET_CLIENT_OUTPUT}`);
    console.log(`  - src/lib/api/admin-client.ts`);
    console.log(`  - src/lib/api/widget-client.ts`);
    console.log('\nUsage:');
    console.log('  // Server-side (API routes, server components):');
    console.log('  import { AdminPaths } from "@/lib/api/admin-client";');
    console.log('');
    console.log('  // Browser-side (client components):');
    console.log('  import { WidgetPaths } from "@/lib/api/widget-client";');
    
  } catch (error) {
    console.error('\n✗ Generation failed:', error.message);
    process.exit(1);
  }
}

main();
