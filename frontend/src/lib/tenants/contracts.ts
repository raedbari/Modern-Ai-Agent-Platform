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
