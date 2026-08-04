import type {
  components,
} from "@/lib/api/generated/admin-api";

export type KnowledgeBaseRecord =
  components["schemas"]["KnowledgeBaseAdminResponse"];

export type KnowledgeDocumentRecord =
  components["schemas"]["DocumentAdminResponse"];

export type KnowledgeIngestionJobRecord =
  components["schemas"]["IngestionJobAdminResponse"];
