"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Database,
  LoaderCircle,
  Pencil,
  Power,
  PowerOff,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  UsersRound,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  AgentConfigurationMutation,
  AgentDirectoryItem,
  AgentDirectoryResponse,
  AgentKnowledgeMode,
} from "@/lib/agents/contracts";

import type {
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";

type StatusFilter =
  | "all"
  | "active"
  | "inactive";

type KnowledgeFilter =
  | "all"
  | AgentKnowledgeMode;

type ErrorPayload = {
  detail?: unknown;
};

const copy = {
  eyebrow:
    "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  title:
    "\u062f\u0644\u064a\u0644 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  description:
    "\u0627\u0633\u062a\u0639\u0631\u0636 \u0648\u0643\u0644\u0627\u0621 \u062c\u0645\u064a\u0639 \u0627\u0644\u0639\u0645\u0644\u0627\u0621\u060c \u0639\u062f\u0644 \u0627\u0644\u0627\u0633\u0645 \u0648\u0648\u0636\u0639 \u0627\u0644\u0645\u0639\u0631\u0641\u0629\u060c \u0648\u0623\u062f\u0631 \u062f\u0648\u0631\u0629 \u062d\u064a\u0627\u0629 \u0627\u0644\u0648\u0643\u064a\u0644.",
  total:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  active:
    "\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0646\u0634\u0637\u0648\u0646",
  required:
    "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0637\u0644\u0648\u0628\u0629",
  preferred:
    "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0641\u0636\u0644\u0629",
  disabled:
    "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0639\u0637\u0644\u0629",
  all:
    "\u0627\u0644\u0643\u0644",
  activeState:
    "\u0646\u0634\u0637",
  inactiveState:
    "\u0645\u0648\u0642\u0641",
  search:
    "\u0627\u0628\u062d\u062b \u0628\u0627\u0633\u0645 \u0627\u0644\u0648\u0643\u064a\u0644\u060c \u0645\u0639\u0631\u0641\u0647\u060c \u0623\u0648 \u0627\u0644\u0639\u0645\u064a\u0644",
  refresh:
    "\u062a\u062d\u062f\u064a\u062b",
  agent:
    "\u0627\u0644\u0648\u0643\u064a\u0644",
  tenant:
    "\u0627\u0644\u0639\u0645\u064a\u0644",
  status:
    "\u0627\u0644\u062d\u0627\u0644\u0629",
  knowledge:
    "\u0648\u0636\u0639 \u0627\u0644\u0645\u0639\u0631\u0641\u0629",
  updated:
    "\u0622\u062e\u0631 \u062a\u062d\u062f\u064a\u062b",
  actions:
    "\u0627\u0644\u0625\u062c\u0631\u0627\u0621\u0627\u062a",
  edit:
    "\u062a\u0639\u062f\u064a\u0644",
  activate:
    "\u062a\u0641\u0639\u064a\u0644",
  suspend:
    "\u062a\u0639\u0637\u064a\u0644",
  delete:
    "\u062d\u0630\u0641 \u0646\u0647\u0627\u0626\u064a",
  tenantDetails:
    "\u0639\u0631\u0636 \u0627\u0644\u0639\u0645\u064a\u0644",
  loading:
    "\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  loadError:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0648\u0643\u0644\u0627\u0621.",
  actionFailed:
    "\u062a\u0639\u0630\u0631 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0625\u062c\u0631\u0627\u0621.",
  permissionDenied:
    "\u0644\u064a\u0633 \u0644\u062f\u064a\u0643 \u0627\u0644\u0635\u0644\u0627\u062d\u064a\u0629 \u0644\u062a\u0646\u0641\u064a\u0630 \u0647\u0630\u0627 \u0627\u0644\u0625\u062c\u0631\u0627\u0621.",
  conflict:
    "\u064a\u062c\u0628 \u062a\u0639\u0637\u064a\u0644 \u0627\u0644\u0648\u0643\u064a\u0644 \u0648\u0625\u0632\u0627\u0644\u0629 \u0623\u064a \u062a\u0639\u0627\u0631\u0636 \u0641\u064a \u062f\u0648\u0631\u0629 \u062d\u064a\u0627\u062a\u0647 \u0642\u0628\u0644 \u0627\u0644\u062d\u0630\u0641.",
  partial:
    "\u0644\u0645 \u064a\u0643\u062a\u0645\u0644 \u062a\u062d\u0645\u064a\u0644 \u0648\u0643\u0644\u0627\u0621 \u0628\u0639\u0636 \u0627\u0644\u0639\u0645\u0644\u0627\u0621.",
  empty:
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u0648\u0643\u0644\u0627\u0621 \u064a\u0637\u0627\u0628\u0642\u0648\u0646 \u0627\u0644\u0628\u062d\u062b \u0648\u0627\u0644\u062a\u0635\u0641\u064a\u0629.",
  retry:
    "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629",
  editTitle:
    "\u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0648\u0643\u064a\u0644",
  name:
    "\u0627\u0633\u0645 \u0627\u0644\u0648\u0643\u064a\u0644",
  save:
    "\u062d\u0641\u0638 \u0627\u0644\u062a\u0639\u062f\u064a\u0644\u0627\u062a",
  cancel:
    "\u0625\u0644\u063a\u0627\u0621",
  deleteTitle:
    "\u062d\u0630\u0641 \u0627\u0644\u0648\u0643\u064a\u0644 \u0646\u0647\u0627\u0626\u064a\u064b\u0627",
  deleteWarning:
    "\u0647\u0630\u0627 \u0627\u0644\u0625\u062c\u0631\u0627\u0621 \u062f\u0627\u0626\u0645. \u0639\u0637\u0644 \u0627\u0644\u0648\u0643\u064a\u0644 \u0623\u0648\u0644\u064b\u0627\u060c \u062b\u0645 \u0627\u0643\u062a\u0628 \u0645\u0639\u0631\u0641\u0647 \u0643\u0627\u0645\u0644\u064b\u0627 \u0644\u0644\u062a\u0623\u0643\u064a\u062f.",
  agentId:
    "\u0645\u0639\u0631\u0641 \u0627\u0644\u0648\u0643\u064a\u0644",
  confirmDelete:
    "\u062a\u0623\u0643\u064a\u062f \u0627\u0644\u062d\u0630\u0641",
  noCreate: "يمكن إنشاء Chatbot جديد مباشرة من لوحة الإدارة.",
  createAgent: "إنشاء Chatbot",
  createAgentTitle: "إنشاء Chatbot جديد",
  systemPrompt: "تعليمات الوكيل",
  contactMessage: "رسالة التواصل عند عدم توفر إجابة",
  create: "إنشاء",
} as const;

const numberFormatter =
  new Intl.NumberFormat("ar");

const dateFormatter =
  new Intl.DateTimeFormat(
    "ar",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );

function formatDate(
  value: string,
): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return dateFormatter.format(date);
}

function knowledgeLabel(
  mode: string,
): string {
  if (mode === "required") {
    return copy.required;
  }

  if (mode === "preferred") {
    return copy.preferred;
  }

  if (mode === "disabled") {
    return copy.disabled;
  }

  return mode;
}

async function readErrorMessage(
  response: Response,
): Promise<string> {
  const payload = (
    await response
      .json()
      .catch(() => null)
  ) as ErrorPayload | null;

  if (response.status === 403) {
    return copy.permissionDenied;
  }

  if (response.status === 409) {
    return copy.conflict;
  }

  if (
    typeof payload?.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail;
  }

  return copy.actionFailed;
}

function recomputeSummary(
  items: AgentDirectoryItem[],
  current: AgentDirectoryResponse,
): AgentDirectoryResponse {
  return {
    ...current,
    items,
    summary: {
      total: items.length,
      active: items.filter(
        (item) => item.is_active,
      ).length,
      inactive: items.filter(
        (item) => !item.is_active,
      ).length,
      required: items.filter(
        (item) =>
          item.knowledge_mode ===
          "required",
      ).length,
      preferred: items.filter(
        (item) =>
          item.knowledge_mode ===
          "preferred",
      ).length,
      disabled: items.filter(
        (item) =>
          item.knowledge_mode ===
          "disabled",
      ).length,
    },
  };
}

export function AgentsView() {
  const [data, setData] =
    useState<AgentDirectoryResponse | null>(
      null,
    );
  const [isLoading, setIsLoading] =
    useState(true);
  const [loadError, setLoadError] =
    useState<string | null>(null);
  const [actionError, setActionError] =
    useState<string | null>(null);
  const [search, setSearch] =
    useState("");
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>("all");
  const [knowledgeFilter, setKnowledgeFilter] =
    useState<KnowledgeFilter>("all");
  const [busyAgentId, setBusyAgentId] =
    useState<string | null>(null);
  const [editAgent, setEditAgent] =
    useState<AgentDirectoryItem | null>(
      null,
    );
  const [editName, setEditName] =
    useState("");
  const [editKnowledgeMode, setEditKnowledgeMode] =
    useState<AgentKnowledgeMode>(
      "preferred",
    );
  const [deleteAgent, setDeleteAgent] =
    useState<AgentDirectoryItem | null>(
      null,
    );
  const [deleteConfirmation, setDeleteConfirmation] =
    useState("");
  const [showCreateAgent, setShowCreateAgent] =
    useState(false);
  const [createTenants, setCreateTenants] =
    useState<Array<{ id: string; name: string; is_active: boolean }>>([]);
  const [createTenantId, setCreateTenantId] =
    useState("");
  const [createName, setCreateName] =
    useState("");
  const [createSystemPrompt, setCreateSystemPrompt] =
    useState("");
  const [createContactMessage, setCreateContactMessage] =
    useState("");
  const [createKnowledgeMode, setCreateKnowledgeMode] =
    useState<AgentKnowledgeMode>("preferred");
  const [isCreatingAgent, setIsCreatingAgent] =
    useState(false);

  const requestDirectory = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<AgentDirectoryResponse> => {
      const response = await fetch(
        "/api/agents",
        {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal,
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Fagents",
        );

        throw new Error("unauthorized");
      }

      if (!response.ok) {
        throw new Error("load-failed");
      }

      return (
        await response.json()
      ) as AgentDirectoryResponse;
    },
    [],
  );

  const refreshDirectory = useCallback(
    async () => {
      setIsLoading(true);
      setLoadError(null);

      try {
        setData(
          await requestDirectory(),
        );
      } catch {
        setLoadError(copy.loadError);
      } finally {
        setIsLoading(false);
      }
    },
    [requestDirectory],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadInitial(): Promise<void> {
      try {
        const payload =
          await requestDirectory(
            controller.signal,
          );

        if (!controller.signal.aborted) {
          setData(payload);
        }
      } catch {
        if (!controller.signal.aborted) {
          setLoadError(copy.loadError);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadInitial();

    return () => {
      controller.abort();
    };
  }, [requestDirectory]);

  const visibleItems = useMemo(() => {
    if (data === null) {
      return [];
    }

    const normalizedSearch =
      search.trim().toLocaleLowerCase();

    return data.items.filter((agent) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        agent.name
          .toLocaleLowerCase()
          .includes(normalizedSearch) ||
        agent.id
          .toLocaleLowerCase()
          .includes(normalizedSearch) ||
        agent.tenant_name
          .toLocaleLowerCase()
          .includes(normalizedSearch) ||
        agent.tenant_id
          .toLocaleLowerCase()
          .includes(normalizedSearch);

      const matchesStatus =
        statusFilter === "all" ||
        (
          statusFilter === "active" &&
          agent.is_active
        ) ||
        (
          statusFilter === "inactive" &&
          !agent.is_active
        );

      const matchesKnowledge =
        knowledgeFilter === "all" ||
        agent.knowledge_mode ===
          knowledgeFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesKnowledge
      );
    });
  }, [
    data,
    knowledgeFilter,
    search,
    statusFilter,
  ]);

  async function openCreateAgent(): Promise<void> {
    setActionError(null);

    try {
      const response = await fetch(
        "/api/tenants",
        {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Fagents",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      const directory =
        await response.json() as TenantDirectoryResponse;
      const available = directory.items.filter(
        (tenant) => tenant.is_active,
      );

      if (available.length === 0) {
        setActionError(
          "أنشئ عميلاً نشطًا أولًا قبل إنشاء Chatbot.",
        );
        return;
      }

      setCreateTenants(available);
      setCreateTenantId(available[0].id);
      setCreateName("");
      setCreateSystemPrompt("");
      setCreateContactMessage("");
      setCreateKnowledgeMode("preferred");
      setShowCreateAgent(true);
    } catch {
      setActionError(copy.actionFailed);
    }
  }

  async function createAgent(): Promise<void> {
    const name = createName.trim();
    if (!createTenantId || !name) {
      return;
    }

    setIsCreatingAgent(true);
    setActionError(null);

    try {
      const response = await fetch(
        "/api/agents",
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            tenant_id: createTenantId,
            name,
            system_prompt:
              createSystemPrompt.trim() || null,
            knowledge_mode: createKnowledgeMode,
            contact_message:
              createContactMessage.trim() || null,
          }),
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Fagents",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      setShowCreateAgent(false);
      await refreshDirectory();
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setIsCreatingAgent(false);
    }
  }

  async function toggleAgentStatus(
    agent: AgentDirectoryItem,
  ): Promise<void> {
    setBusyAgentId(agent.id);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/agents/${
          encodeURIComponent(
            agent.tenant_id,
          )
        }/${
          encodeURIComponent(agent.id)
        }/status`,
        {
          method: "PATCH",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            is_active: !agent.is_active,
          }),
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Fagents",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      const updated = (
        await response.json()
      ) as {
        is_active: boolean;
        updated_at: string;
      };

      setData((current) => {
        if (current === null) {
          return current;
        }

        const items = current.items.map(
          (item) =>
            item.id === agent.id &&
            item.tenant_id ===
              agent.tenant_id
              ? {
                  ...item,
                  is_active:
                    updated.is_active,
                  updated_at:
                    updated.updated_at,
                }
              : item,
        );

        return recomputeSummary(
          items,
          current,
        );
      });
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAgentId(null);
    }
  }

  async function saveAgentConfiguration(): Promise<void> {
    if (editAgent === null) {
      return;
    }

    const normalizedName =
      editName.trim();

    if (
      normalizedName.length === 0 ||
      normalizedName.length > 255
    ) {
      setActionError(
        "\u064a\u062c\u0628 \u0623\u0646 \u064a\u062d\u062a\u0648\u064a \u0627\u0633\u0645 \u0627\u0644\u0648\u0643\u064a\u0644 \u0639\u0644\u0649 1 \u0625\u0644\u0649 255 \u0645\u062d\u0631\u0641\u064b\u0627.",
      );
      return;
    }

    const payload:
      AgentConfigurationMutation = {};

    if (normalizedName !== editAgent.name) {
      payload.name = normalizedName;
    }

    if (
      editKnowledgeMode !==
      editAgent.knowledge_mode
    ) {
      payload.knowledge_mode =
        editKnowledgeMode;
    }

    if (Object.keys(payload).length === 0) {
      setEditAgent(null);
      return;
    }

    setBusyAgentId(editAgent.id);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/agents/${
          encodeURIComponent(
            editAgent.tenant_id,
          )
        }/${
          encodeURIComponent(editAgent.id)
        }/config`,
        {
          method: "PATCH",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Fagents",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      const updated = (
        await response.json()
      ) as {
        name: string;
        knowledge_mode: string;
        updated_at: string;
      };

      setData((current) => {
        if (current === null) {
          return current;
        }

        const items = current.items.map(
          (item) =>
            item.id === editAgent.id &&
            item.tenant_id ===
              editAgent.tenant_id
              ? {
                  ...item,
                  name: updated.name,
                  knowledge_mode:
                    updated.knowledge_mode,
                  updated_at:
                    updated.updated_at,
                }
              : item,
        );

        return recomputeSummary(
          items,
          current,
        );
      });

      setEditAgent(null);
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAgentId(null);
    }
  }

  async function confirmPermanentDelete(): Promise<void> {
    if (
      deleteAgent === null ||
      deleteAgent.is_active ||
      deleteConfirmation !== deleteAgent.id
    ) {
      return;
    }

    setBusyAgentId(deleteAgent.id);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/agents/${
          encodeURIComponent(
            deleteAgent.tenant_id,
          )
        }/${
          encodeURIComponent(deleteAgent.id)
        }?confirm=${
          encodeURIComponent(
            deleteConfirmation,
          )
        }`,
        {
          method: "DELETE",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Fagents",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      setData((current) => {
        if (current === null) {
          return current;
        }

        return recomputeSummary(
          current.items.filter(
            (item) =>
              !(
                item.id === deleteAgent.id &&
                item.tenant_id ===
                  deleteAgent.tenant_id
              ),
          ),
          current,
        );
      });

      setDeleteAgent(null);
      setDeleteConfirmation("");
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAgentId(null);
    }
  }

  if (isLoading && data === null) {
    return (
      <main className="agents-page">
        <section className="tenants-state">
          <LoaderCircle
            className="tenants-spinner"
            aria-hidden="true"
          />
          <h2>{copy.loading}</h2>
        </section>
      </main>
    );
  }

  if (loadError && data === null) {
    return (
      <main className="agents-page">
        <section className="tenants-state">
          <AlertTriangle aria-hidden="true" />
          <h2>{loadError}</h2>

          <button
            type="button"
            onClick={() => {
              void refreshDirectory();
            }}
          >
            <RefreshCw aria-hidden="true" />
            {copy.retry}
          </button>
        </section>
      </main>
    );
  }

  if (data === null) {
    return null;
  }

  const metrics = [
    {
      label: copy.total,
      value: data.summary.total,
      icon: Bot,
    },
    {
      label: copy.active,
      value: data.summary.active,
      icon: CheckCircle2,
    },
    {
      label: copy.required,
      value: data.summary.required,
      icon: Database,
    },
    {
      label: copy.preferred,
      value: data.summary.preferred,
      icon: UsersRound,
    },
  ];

  return (
    <main className="agents-page">
      <section className="agents-header">
        <div>
          <span className="agents-header__eyebrow">
            <Bot aria-hidden="true" />
            {copy.eyebrow}
          </span>

          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            className="agents-refresh"
            type="button"
            onClick={() => {
              void openCreateAgent();
            }}
          >
            <Plus aria-hidden="true" />
            {copy.createAgent}
          </button>

        <button
          className="agents-refresh"
          type="button"
          disabled={isLoading}
          onClick={() => {
            void refreshDirectory();
          }}
        >
          <RefreshCw
            className={
              isLoading
                ? "tenants-spinner"
                : undefined
            }
            aria-hidden="true"
          />
          {copy.refresh}
        </button>
        </div>
      </section>

      <section className="agents-metrics">
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <article
              key={metric.label}
              className="agents-metric"
            >
              <span>
                <Icon aria-hidden="true" />
              </span>

              <div>
                <small>{metric.label}</small>
                <strong>
                  {numberFormatter.format(
                    metric.value,
                  )}
                </strong>
              </div>
            </article>
          );
        })}
      </section>


      {data.status === "partial" && (
        <div className="tenants-warning">
          <AlertTriangle aria-hidden="true" />
          <span>{copy.partial}</span>
        </div>
      )}

      {actionError && (
        <div
          className="tenants-action-error"
          role="alert"
        >
          <AlertTriangle aria-hidden="true" />
          <span>{actionError}</span>

          <button
            type="button"
            aria-label="\u0625\u063a\u0644\u0627\u0642"
            onClick={() => {
              setActionError(null);
            }}
          >
            <X aria-hidden="true" />
          </button>
        </div>
      )}

      <section className="agents-directory">
        <header className="agents-toolbar">
          <div className="agents-search">
            <Search aria-hidden="true" />

            <input
              type="search"
              value={search}
              placeholder={copy.search}
              aria-label={copy.search}
              onChange={(event) => {
                setSearch(event.target.value);
              }}
            />
          </div>

          <div className="agents-filter-groups">
            <div className="agents-filters">
              {(
                [
                  ["all", copy.all],
                  ["active", copy.activeState],
                  ["inactive", copy.inactiveState],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={
                    statusFilter === value
                      ? "is-active"
                      : undefined
                  }
                  onClick={() => {
                    setStatusFilter(value);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            <select
              value={knowledgeFilter}
              aria-label={copy.knowledge}
              onChange={(event) => {
                setKnowledgeFilter(
                  event.target
                    .value as KnowledgeFilter,
                );
              }}
            >
              <option value="all">
                {copy.all} ? {copy.knowledge}
              </option>
              <option value="required">
                {copy.required}
              </option>
              <option value="preferred">
                {copy.preferred}
              </option>
              <option value="disabled">
                {copy.disabled}
              </option>
            </select>
          </div>
        </header>

        <div className="agents-table">
          <div className="agents-table__head">
            <span>{copy.agent}</span>
            <span>{copy.tenant}</span>
            <span>{copy.status}</span>
            <span>{copy.knowledge}</span>
            <span>{copy.updated}</span>
            <span>{copy.actions}</span>
          </div>

          {visibleItems.length === 0 ? (
            <div className="agents-empty">
              <Bot aria-hidden="true" />
              <p>{copy.empty}</p>
            </div>
          ) : (
            visibleItems.map((agent) => {
              const isBusy =
                busyAgentId === agent.id;

              return (
                <article
                  key={`${agent.tenant_id}:${agent.id}`}
                  className="agents-row"
                >
                  <div className="agents-row__identity">
                    <span>
                      <Bot aria-hidden="true" />
                    </span>

                    <div>
                      <strong>
                        {agent.name}
                      </strong>
                      <code dir="ltr">
                        {agent.id}
                      </code>
                    </div>
                  </div>

                  <div className="agents-row__tenant">
                    <Link
                      href={`/dashboard/tenants/${
                        encodeURIComponent(
                          agent.tenant_id,
                        )
                      }`}
                    >
                      {agent.tenant_name}
                      <ArrowLeft aria-hidden="true" />
                    </Link>

                    <code dir="ltr">
                      {agent.tenant_id}
                    </code>
                  </div>

                  <span
                    className={
                      agent.is_active
                        ? "tenant-status is-active"
                        : "tenant-status"
                    }
                  >
                    <i />
                    {agent.is_active
                      ? copy.activeState
                      : copy.inactiveState}
                  </span>

                  <span
                    className={`agent-knowledge is-${agent.knowledge_mode}`}
                  >
                    {knowledgeLabel(
                      agent.knowledge_mode,
                    )}
                  </span>

                  <time>
                    {formatDate(
                      agent.updated_at,
                    )}
                  </time>

                  <div className="agents-actions">
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        setEditAgent(agent);
                        setEditName(agent.name);
                        setEditKnowledgeMode(
                          (
                            [
                              "required",
                              "preferred",
                              "disabled",
                            ] as const
                          ).includes(
                            agent.knowledge_mode as
                              AgentKnowledgeMode,
                          )
                            ? agent.knowledge_mode as
                                AgentKnowledgeMode
                            : "preferred",
                        );
                        setActionError(null);
                      }}
                    >
                      <Pencil aria-hidden="true" />
                      {copy.edit}
                    </button>

                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        void toggleAgentStatus(
                          agent,
                        );
                      }}
                    >
                      {isBusy ? (
                        <LoaderCircle
                          className="tenants-spinner"
                          aria-hidden="true"
                        />
                      ) : agent.is_active ? (
                        <PowerOff aria-hidden="true" />
                      ) : (
                        <Power aria-hidden="true" />
                      )}

                      {agent.is_active
                        ? copy.suspend
                        : copy.activate}
                    </button>

                    <button
                      type="button"
                      className="is-danger"
                      disabled={
                        isBusy ||
                        agent.is_active
                      }
                      title={
                        agent.is_active
                          ? copy.conflict
                          : copy.delete
                      }
                      onClick={() => {
                        setDeleteAgent(agent);
                        setDeleteConfirmation("");
                        setActionError(null);
                      }}
                    >
                      <Trash2 aria-hidden="true" />
                      {copy.delete}
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>

      {showCreateAgent && (
        <div className="tenant-dialog-backdrop">
          <section
            className="tenant-dialog agent-edit-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-create-title"
          >
            <header>
              <span><Plus aria-hidden="true" /></span>
              <button
                type="button"
                aria-label="إغلاق"
                disabled={isCreatingAgent}
                onClick={() => setShowCreateAgent(false)}
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <h3 id="agent-create-title">
              {copy.createAgentTitle}
            </h3>

            <label htmlFor="agent-create-tenant">
              {copy.tenant}
            </label>
            <select
              id="agent-create-tenant"
              value={createTenantId}
              onChange={(event) =>
                setCreateTenantId(event.target.value)
              }
            >
              {createTenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>

            <label htmlFor="agent-create-name">
              {copy.name}
            </label>
            <input
              id="agent-create-name"
              type="text"
              maxLength={255}
              value={createName}
              onChange={(event) => setCreateName(event.target.value)}
            />

            <label htmlFor="agent-create-prompt">
              {copy.systemPrompt}
            </label>
            <textarea
              id="agent-create-prompt"
              rows={6}
              maxLength={10000}
              value={createSystemPrompt}
              onChange={(event) => setCreateSystemPrompt(event.target.value)}
              style={{ width: "100%", resize: "vertical" }}
            />

            <label htmlFor="agent-create-knowledge">
              {copy.knowledge}
            </label>
            <select
              id="agent-create-knowledge"
              value={createKnowledgeMode}
              onChange={(event) =>
                setCreateKnowledgeMode(
                  event.target.value as AgentKnowledgeMode,
                )
              }
            >
              <option value="required">{copy.required}</option>
              <option value="preferred">{copy.preferred}</option>
              <option value="disabled">{copy.disabled}</option>
            </select>

            <label htmlFor="agent-create-contact">
              {copy.contactMessage}
            </label>
            <textarea
              id="agent-create-contact"
              rows={3}
              maxLength={1000}
              value={createContactMessage}
              onChange={(event) => setCreateContactMessage(event.target.value)}
              style={{ width: "100%", resize: "vertical" }}
            />

            <footer>
              <button
                type="button"
                disabled={isCreatingAgent}
                onClick={() => setShowCreateAgent(false)}
              >
                {copy.cancel}
              </button>
              <button
                type="button"
                disabled={
                  isCreatingAgent ||
                  !createTenantId ||
                  createName.trim().length === 0
                }
                onClick={() => void createAgent()}
              >
                {isCreatingAgent ? (
                  <LoaderCircle
                    className="tenants-spinner"
                    aria-hidden="true"
                  />
                ) : (
                  <Plus aria-hidden="true" />
                )}
                {copy.create}
              </button>
            </footer>
          </section>
        </div>
      )}

      {editAgent && (
        <div className="tenant-dialog-backdrop">
          <section
            className="tenant-dialog agent-edit-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-edit-title"
          >
            <header>
              <span>
                <Pencil aria-hidden="true" />
              </span>

              <button
                type="button"
                aria-label="\u0625\u063a\u0644\u0627\u0642"
                disabled={
                  busyAgentId === editAgent.id
                }
                onClick={() => {
                  setEditAgent(null);
                }}
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <h3 id="agent-edit-title">
              {copy.editTitle}
            </h3>

            <code
              className="tenant-dialog__id"
              dir="ltr"
            >
              {editAgent.id}
            </code>

            <label htmlFor="agent-edit-name">
              {copy.name}
            </label>

            <input
              id="agent-edit-name"
              type="text"
              maxLength={255}
              value={editName}
              onChange={(event) => {
                setEditName(
                  event.target.value,
                );
              }}
            />

            <label htmlFor="agent-edit-knowledge">
              {copy.knowledge}
            </label>

            <select
              id="agent-edit-knowledge"
              value={editKnowledgeMode}
              onChange={(event) => {
                setEditKnowledgeMode(
                  event.target
                    .value as AgentKnowledgeMode,
                );
              }}
            >
              <option value="required">
                {copy.required}
              </option>
              <option value="preferred">
                {copy.preferred}
              </option>
              <option value="disabled">
                {copy.disabled}
              </option>
            </select>

            <footer>
              <button
                type="button"
                disabled={
                  busyAgentId === editAgent.id
                }
                onClick={() => {
                  setEditAgent(null);
                }}
              >
                {copy.cancel}
              </button>

              <button
                type="button"
                disabled={
                  busyAgentId === editAgent.id ||
                  editName.trim().length === 0
                }
                onClick={() => {
                  void saveAgentConfiguration();
                }}
              >
                {busyAgentId === editAgent.id ? (
                  <LoaderCircle
                    className="tenants-spinner"
                    aria-hidden="true"
                  />
                ) : (
                  <CheckCircle2 aria-hidden="true" />
                )}
                {copy.save}
              </button>
            </footer>
          </section>
        </div>
      )}

      {deleteAgent && (
        <div className="tenant-dialog-backdrop">
          <section
            className="tenant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-delete-title"
          >
            <header>
              <span>
                <AlertTriangle aria-hidden="true" />
              </span>

              <button
                type="button"
                aria-label="\u0625\u063a\u0644\u0627\u0642"
                disabled={
                  busyAgentId ===
                  deleteAgent.id
                }
                onClick={() => {
                  setDeleteAgent(null);
                  setDeleteConfirmation("");
                }}
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <h3 id="agent-delete-title">
              {copy.deleteTitle}
            </h3>

            <p>{copy.deleteWarning}</p>

            <strong className="tenant-dialog__name">
              {deleteAgent.name}
            </strong>

            <code
              className="tenant-dialog__id"
              dir="ltr"
            >
              {deleteAgent.id}
            </code>

            <label htmlFor="agent-delete-confirmation">
              {copy.agentId}
            </label>

            <input
              id="agent-delete-confirmation"
              type="text"
              dir="ltr"
              autoComplete="off"
              value={deleteConfirmation}
              onChange={(event) => {
                setDeleteConfirmation(
                  event.target.value,
                );
              }}
            />

            <footer>
              <button
                type="button"
                disabled={
                  busyAgentId ===
                  deleteAgent.id
                }
                onClick={() => {
                  setDeleteAgent(null);
                  setDeleteConfirmation("");
                }}
              >
                {copy.cancel}
              </button>

              <button
                type="button"
                className="is-danger"
                disabled={
                  deleteAgent.is_active ||
                  deleteConfirmation !==
                    deleteAgent.id ||
                  busyAgentId ===
                    deleteAgent.id
                }
                onClick={() => {
                  void confirmPermanentDelete();
                }}
              >
                {busyAgentId ===
                deleteAgent.id ? (
                  <LoaderCircle
                    className="tenants-spinner"
                    aria-hidden="true"
                  />
                ) : (
                  <Trash2 aria-hidden="true" />
                )}
                {copy.confirmDelete}
              </button>
            </footer>
          </section>
        </div>
      )}
    </main>
  );
}
