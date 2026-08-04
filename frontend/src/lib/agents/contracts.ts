export type AgentKnowledgeMode =
  | "required"
  | "preferred"
  | "disabled";

export type AgentDirectoryItem = {
  id: string;
  tenant_id: string;
  tenant_name: string;
  name: string;
  is_active: boolean;
  knowledge_mode: string;
  created_at: string;
  updated_at: string;
};

export type AgentDirectorySummary = {
  total: number;
  active: number;
  inactive: number;
  required: number;
  preferred: number;
  disabled: number;
};

export type AgentDirectoryResponse = {
  generated_at: string;
  status: "healthy" | "partial";
  summary: AgentDirectorySummary;
  items: AgentDirectoryItem[];
  warnings: string[];
};

export type AgentConfigurationMutation = {
  name?: string;
  knowledge_mode?: AgentKnowledgeMode;
};
