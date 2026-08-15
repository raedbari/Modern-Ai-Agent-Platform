export type DashboardMetric = {
  total: number;
  active: number;
  inactive: number;
};

export type DashboardApiKeyMetric =
  DashboardMetric & {
    expired: number;
    revoked: number;
  };

export type DashboardAuditEvent = {
  id: number;
  event_type: string;
  outcome: "success" | "failure";
  target_type: string | null;
  target_id: string | null;
  created_at: string;
};

export type DashboardTenantRank = {
  id: string;
  name: string;
  is_active: boolean;
  agents_total: number;
  agents_active: number;
  api_keys_active: number;
};

export type DashboardOverview = {
  generated_at: string;
  status: "healthy" | "partial";
  tenants: DashboardMetric;
  agents: DashboardMetric;
  api_keys: DashboardApiKeyMetric;
  audit: {
    loaded: number;
    success: number;
    failure: number;
    recent: DashboardAuditEvent[];
  };
  top_tenants: DashboardTenantRank[];
  warnings: string[];
};
