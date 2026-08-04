export type TenantDirectoryItem = {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  agents_total: number;
  agents_active: number;
  api_keys_total: number;
  api_keys_active: number;
};

export type TenantDirectorySummary = {
  total: number;
  active: number;
  inactive: number;
  agents_total: number;
  agents_active: number;
  api_keys_total: number;
  api_keys_active: number;
};

export type TenantDirectoryResponse = {
  generated_at: string;
  status: "healthy" | "partial";
  summary: TenantDirectorySummary;
  items: TenantDirectoryItem[];
  warnings: string[];
};

export type TenantDetailAgent = {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  knowledge_mode: string;
  created_at: string;
  updated_at: string;
};

export type TenantDetailApiKey = {
  key_id: string;
  tenant_id: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  last_used_at: string | null;
};

export type TenantDetailsResponse = {
  generated_at: string;
  tenant: {
    id: string;
    name: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
  summary: {
    agents_total: number;
    agents_active: number;
    api_keys_total: number;
    api_keys_active: number;
    api_keys_revoked: number;
    api_keys_expired: number;
  };
  agents: TenantDetailAgent[];
  api_keys: TenantDetailApiKey[];
};
