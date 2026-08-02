#!/usr/bin/env node
/**
 * Simple TypeScript client generator from OpenAPI schema.
 * Creates typed interfaces without external dependencies.
 */

import { readFile, writeFile, mkdir } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, '..');
const backendRoot = join(projectRoot, '..', 'backend');

const OPENAPI_PATH = join(backendRoot, 'openapi.json');
const OUTPUT_DIR = join(projectRoot, 'src', 'lib', 'api');

/**
 * Generate TypeScript interface from JSON Schema.
 */
function generateInterface(name, schema) {
  if (!schema.properties) return '';
  
  const props = Object.entries(schema.properties).map(([key, prop]) => {
    const required = schema.required?.includes(key);
    const optional = required ? '' : '?';
    const type = getTypeScriptType(prop);
    return `  ${key}${optional}: ${type};`;
  });
  
  return `export interface ${name} {\n${props.join('\n')}\n}\n`;
}

/**
 * Convert JSON Schema type to TypeScript type.
 */
function getTypeScriptType(prop) {
  if (prop.anyOf) {
    return prop.anyOf.map(getTypeScriptType).join(' | ');
  }
  
  if (prop.type === 'array') {
    return `${getTypeScriptType(prop.items)}[]`;
  }
  
  if (prop.type === 'object') {
    if (prop.additionalProperties) {
      return `Record<string, ${getTypeScriptType(prop.additionalProperties)}>`;
    }
    return 'Record<string, unknown>';
  }
  
  switch (prop.type) {
    case 'string':
      if (prop.format === 'date-time') return 'string'; // ISO date string
      if (prop.format === 'uuid') return 'string';
      return 'string';
    case 'number':
    case 'integer':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'null':
      return 'null';
    default:
      return 'unknown';
  }
}

/**
 * Generate path operation types.
 */
function generatePathTypes(paths, prefix) {
  const operations = [];
  
  for (const [path, methods] of Object.entries(paths)) {
    for (const [method, operation] of Object.entries(methods)) {
      if (!['get', 'post', 'put', 'patch', 'delete'].includes(method)) continue;
      
      const operationId = operation.operationId || `${method}_${path.replace(/[^a-zA-Z0-9]/g, '_')}`;
      const requestBody = operation.requestBody?.content?.['application/json']?.schema;
      const response = operation.responses?.['200']?.content?.['application/json']?.schema;
      
      operations.push({
        path,
        method: method.toUpperCase(),
        operationId,
        requestBody,
        response,
        parameters: operation.parameters || []
      });
    }
  }
  
  return operations;
}

/**
 * Filter schema by path prefix.
 */
function filterPaths(paths, prefixes) {
  const filtered = {};
  for (const [path, methods] of Object.entries(paths)) {
    if (prefixes.some(prefix => path.startsWith(prefix))) {
      filtered[path] = methods;
    }
  }
  return filtered;
}

/**
 * Generate client file.
 */
async function generateClient(schema, pathPrefixes, outputFile, clientName, securitySchemes) {
  const paths = filterPaths(schema.paths, pathPrefixes);
  const operations = generatePathTypes(paths, '');
  
  let output = `/**
 * ${clientName} API Client Types
 * 
 * Auto-generated from OpenAPI schema. DO NOT EDIT MANUALLY.
 * To regenerate: npm run generate:api-clients
 * 
 * Security schemes: ${securitySchemes.join(', ')}
 */

// ============================================================================
// Common Types
// ============================================================================

export type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface ApiError {
  detail: string;
  [key: string]: unknown;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
}

// ============================================================================
// Schema Types
// ============================================================================

`;

  // Generate interfaces from components/schemas
  if (schema.components?.schemas) {
    for (const [name, schemaObj] of Object.entries(schema.components.schemas)) {
      output += generateInterface(name, schemaObj) + '\n';
    }
  }
  
  output += `
// ============================================================================
// API Operations
// ============================================================================

export interface ApiOperations {
`;

  for (const op of operations) {
    output += `  /**\n   * ${op.method} ${op.path}\n   */\n`;
    output += `  '${op.operationId}': {\n`;
    output += `    method: '${op.method}';\n`;
    output += `    path: '${op.path}';\n`;
    
    if (op.requestBody) {
      output += `    requestBody: unknown; // TODO: Type from schema\n`;
    }
    
    if (op.response) {
      output += `    response: unknown; // TODO: Type from schema\n`;
    }
    
    output += `  };\n`;
  }
  
  output += `}\n\n`;
  
  output += `// API Base URL\n`;
  output += `export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';\n`;
  
  await writeFile(outputFile, output, 'utf-8');
  console.log(`✓ Generated: ${outputFile}`);
}

/**
 * Main execution.
 */
async function main() {
  try {
    console.log('🚀 Generating API clients...\n');
    
    // Load OpenAPI schema
    const schema = JSON.parse(await readFile(OPENAPI_PATH, 'utf-8'));
    console.log(`✓ Loaded: ${OPENAPI_PATH}`);
    console.log(`  Paths: ${Object.keys(schema.paths).length}`);
    console.log(`  Schemas: ${Object.keys(schema.components?.schemas || {}).length}\n`);
    
    // Create output directory
    await mkdir(OUTPUT_DIR, { recursive: true });
    
    // Generate Admin Client
    console.log('📝 Generating Admin Client...');
    await generateClient(
      schema,
      ['/api/admin', '/api/chat', '/api/knowledge-bases', '/health', '/ready'],
      join(OUTPUT_DIR, 'admin-client.ts'),
      'Admin',
      ['AdminJWT', 'InternalAdminKey', 'TenantApiKey']
    );
    
    // Generate Widget Client
    console.log('📝 Generating Widget Client...');
    await generateClient(
      schema,
      ['/api/widget', '/api/chat', '/health'],
      join(OUTPUT_DIR, 'widget-client.ts'),
      'Widget',
      ['WidgetToken']
    );
    
    // Create index file
    const indexContent = `/**
 * API Clients
 * 
 * - admin-client: Server-side only (contains admin secrets)
 * - widget-client: Browser-safe (public endpoints only)
 */

// Re-export for convenience
export * from './admin-client';
export * from './widget-client';

// Prevent admin client usage in browser
if (typeof window !== 'undefined') {
  console.warn(
    '[API Warning] Admin client should only be used server-side. ' +
    'Use widget-client for browser code.'
  );
}
`;
    
    await writeFile(join(OUTPUT_DIR, 'index.ts'), indexContent, 'utf-8');
    
    console.log('\n✅ API clients generated successfully!\n');
    console.log('Generated files:');
    console.log(`  - ${join(OUTPUT_DIR, 'admin-client.ts')}`);
    console.log(`  - ${join(OUTPUT_DIR, 'widget-client.ts')}`);
    console.log(`  - ${join(OUTPUT_DIR, 'index.ts')}`);
    
  } catch (error) {
    console.error('\n✗ Failed:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
