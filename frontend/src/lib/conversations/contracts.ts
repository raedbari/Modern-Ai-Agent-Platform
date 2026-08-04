
export type ConversationMessageRole =
  | "system"
  | "user"
  | "assistant"
  | "tool";

export type ConversationRecord = {
  id: string;
  tenant_id: string;
  agent_id: string;
  agent_name: string;
  user_identifier: string | null;
  metadata: Record<string, unknown> | null;
  message_count: number;
  user_message_count: number;
  assistant_message_count: number;
  last_message_role:
    | ConversationMessageRole
    | null;
  last_message_preview: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDirectoryResponse = {
  items: ConversationRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type ConversationMessageRecord = {
  id: string;
  tenant_id: string;
  conversation_id: string;
  role: ConversationMessageRole;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export type ConversationMessagesResponse = {
  items: ConversationMessageRecord[];
  total: number;
  limit: number;
  offset: number;
};
