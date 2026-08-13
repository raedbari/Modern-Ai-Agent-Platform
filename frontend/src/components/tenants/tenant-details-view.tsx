"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Ban,
  Bot,
  CheckCircle2,
  Clock3,
  Copy,
  KeyRound,
  LoaderCircle,
  Power,
  PowerOff,
  RefreshCw,
  ShieldCheck,
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
  TenantDetailApiKey,
  TenantDetailsResponse,
} from "@/lib/tenants/contracts";

type Props = {
  tenantId: string;
};

type ApiErrorPayload = {
  detail?: unknown;
};

type KeyState =
  | "active"
  | "revoked"
  | "expired"
  | "inactive";

const copy = {
  back:
    "\u0627\u0644\u0639\u0648\u062f\u0629 \u0625\u0644\u0649 \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  eyebrow:
    "\u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0639\u0645\u064a\u0644",
  description:
    "\u0645\u0631\u0627\u0642\u0628\u0629 \u062d\u0627\u0644\u0629 \u0627\u0644\u0639\u0645\u064a\u0644 \u0648\u0648\u0643\u0644\u0627\u0626\u0647 \u0648\u0645\u0641\u0627\u062a\u064a\u062d API \u0627\u0644\u0645\u0631\u062a\u0628\u0637\u0629 \u0628\u0647.",
  active:
    "\u0646\u0634\u0637",
  inactive:
    "\u0645\u0648\u0642\u0641",
  activate:
    "\u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u0639\u0645\u064a\u0644",
  suspend:
    "\u062a\u0639\u0637\u064a\u0644 \u0627\u0644\u0639\u0645\u064a\u0644",
  refresh:
    "\u062a\u062d\u062f\u064a\u062b",
  totalAgents:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  activeAgents:
    "\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0646\u0634\u0637\u0648\u0646",
  totalKeys:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d",
  activeKeys:
    "\u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d \u0627\u0644\u0646\u0634\u0637\u0629",
  agents:
    "\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0639\u0645\u064a\u0644",
  agentsDescription:
    "\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u062a\u0627\u0628\u0639\u0648\u0646 \u0644\u0647\u0630\u0647 \u0627\u0644\u0645\u0633\u0627\u062d\u0629 \u0648\u062d\u0627\u0644\u0629 \u0645\u0639\u0631\u0641\u062a\u0647\u0645.",
  apiKeys:
    "\u0645\u0641\u0627\u062a\u064a\u062d API",
  apiKeysDescription:
    "\u064a\u0638\u0647\u0631 \u0647\u0646\u0627 \u0645\u0639\u0631\u0641 \u0627\u0644\u0645\u0641\u062a\u0627\u062d \u0648\u0628\u064a\u0627\u0646\u0627\u062a\u0647 \u0627\u0644\u0648\u0635\u0641\u064a\u0629 \u0641\u0642\u0637\u060c \u0648\u0644\u064a\u0633 \u0627\u0644\u0645\u0641\u062a\u0627\u062d \u0627\u0644\u0633\u0631\u064a.",
  revokeAll:
    "\u0625\u0628\u0637\u0627\u0644 \u062c\u0645\u064a\u0639 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d",
  revoke:
    "\u0625\u0628\u0637\u0627\u0644",
  revoked:
    "\u0645\u0628\u0637\u0644",
  expired:
    "\u0645\u0646\u062a\u0647\u064a",
  never:
    "\u0644\u0627 \u064a\u0648\u062c\u062f",
  notUsed:
    "\u0644\u0645 \u064a\u0633\u062a\u062e\u062f\u0645",
  created:
    "\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0625\u0646\u0634\u0627\u0621",
  lastUsed:
    "\u0622\u062e\u0631 \u0627\u0633\u062a\u062e\u062f\u0627\u0645",
  expires:
    "\u0627\u0644\u0627\u0646\u062a\u0647\u0627\u0621",
  required:
    "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0637\u0644\u0648\u0628\u0629",
  preferred:
    "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0641\u0636\u0644\u0629",
  disabled:
    "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0639\u0637\u0644\u0629",
  noAgents:
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u0648\u0643\u0644\u0627\u0621 \u0644\u0647\u0630\u0627 \u0627\u0644\u0639\u0645\u064a\u0644.",
  noKeys:
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u0645\u0641\u0627\u062a\u064a\u062d API \u0644\u0647\u0630\u0627 \u0627\u0644\u0639\u0645\u064a\u0644.",
  loading:
    "\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0639\u0645\u064a\u0644",
  loadError:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0639\u0645\u064a\u0644.",
  notFound:
    "\u0627\u0644\u0639\u0645\u064a\u0644 \u0627\u0644\u0645\u0637\u0644\u0648\u0628 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f.",
  permissionDenied:
    "\u0644\u064a\u0633 \u0644\u062f\u064a\u0643 \u0627\u0644\u0635\u0644\u0627\u062d\u064a\u0629 \u0644\u062a\u0646\u0641\u064a\u0630 \u0647\u0630\u0627 \u0627\u0644\u0625\u062c\u0631\u0627\u0621.",
  actionFailed:
    "\u062a\u0639\u0630\u0631 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0625\u062c\u0631\u0627\u0621.",
  retry:
    "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629",
  cancel:
    "\u0625\u0644\u063a\u0627\u0621",
  confirmRevoke:
    "\u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0625\u0628\u0637\u0627\u0644",
  revokeOneTitle:
    "\u0625\u0628\u0637\u0627\u0644 \u0645\u0641\u062a\u0627\u062d API",
  revokeOneWarning:
    "\u0633\u064a\u062a\u0648\u0642\u0641 \u0647\u0630\u0627 \u0627\u0644\u0645\u0641\u062a\u0627\u062d \u0639\u0646 \u0627\u0644\u0639\u0645\u0644 \u0641\u0648\u0631\u064b\u0627. \u0644\u0627 \u064a\u0645\u0643\u0646 \u0625\u0639\u0627\u062f\u0629 \u062a\u0641\u0639\u064a\u0644\u0647.",
  revokeAllTitle:
    "\u0625\u0628\u0637\u0627\u0644 \u0643\u0644 \u0645\u0641\u0627\u062a\u064a\u062d API",
  revokeAllWarning:
    "\u0633\u064a\u062a\u0648\u0642\u0641 \u0648\u0635\u0648\u0644 \u062c\u0645\u064a\u0639 \u0627\u0644\u0623\u0646\u0638\u0645\u0629 \u0627\u0644\u062a\u064a \u062a\u0633\u062a\u062e\u062f\u0645 \u0647\u0630\u0647 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d. \u0627\u0643\u062a\u0628 \u0645\u0639\u0631\u0641 \u0627\u0644\u0639\u0645\u064a\u0644 \u0644\u0644\u062a\u0623\u0643\u064a\u062f.",
  tenantId:
    "\u0645\u0639\u0631\u0641 \u0627\u0644\u0639\u0645\u064a\u0644",
  copied:
    "\u062a\u0645 \u0627\u0644\u0646\u0633\u062e",
  unknown:
    "\u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631",
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
  value: string | null,
  fallback: string,
): string {
  if (value === null) {
    return fallback;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return fallback;
  }

  return dateFormatter.format(date);
}

function getKeyState(
  apiKey: TenantDetailApiKey,
): KeyState {
  if (apiKey.revoked_at !== null) {
    return "revoked";
  }

  if (
    apiKey.expires_at !== null &&
    Date.parse(apiKey.expires_at) <= Date.now()
  ) {
    return "expired";
  }

  if (apiKey.is_active) {
    return "active";
  }

  return "inactive";
}

function isActiveKey(
  apiKey: TenantDetailApiKey,
): boolean {
  return getKeyState(apiKey) === "active";
}

function recomputeKeySummary(
  current: TenantDetailsResponse,
  apiKeys: TenantDetailApiKey[],
): TenantDetailsResponse {
  return {
    ...current,
    api_keys: apiKeys,
    summary: {
      ...current.summary,
      api_keys_total: apiKeys.length,
      api_keys_active:
        apiKeys.filter(isActiveKey).length,
      api_keys_revoked:
        apiKeys.filter(
          (apiKey) =>
            apiKey.revoked_at !== null,
        ).length,
      api_keys_expired:
        apiKeys.filter(
          (apiKey) =>
            apiKey.expires_at !== null &&
            Date.parse(
              apiKey.expires_at,
            ) <= Date.now(),
        ).length,
    },
  };
}

async function readError(
  response: Response,
): Promise<string> {
  const payload = (
    await response
      .json()
      .catch(() => null)
  ) as ApiErrorPayload | null;

  if (response.status === 403) {
    return copy.permissionDenied;
  }

  if (
    typeof payload?.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail;
  }

  return copy.actionFailed;
}

export function TenantDetailsView({
  tenantId,
}: Props) {
  const [data, setData] =
    useState<TenantDetailsResponse | null>(
      null,
    );
  const [isLoading, setIsLoading] =
    useState(true);
  const [loadError, setLoadError] =
    useState<string | null>(null);
  const [actionError, setActionError] =
    useState<string | null>(null);
  const [busyAction, setBusyAction] =
    useState<string | null>(null);
  const [revokeKeyTarget, setRevokeKeyTarget] =
    useState<TenantDetailApiKey | null>(
      null,
    );
  const [showRevokeAll, setShowRevokeAll] =
    useState(false);
  const [revokeAllConfirmation, setRevokeAllConfirmation] =
    useState("");
  const [copiedValue, setCopiedValue] =
    useState<string | null>(null);

  const requestDetails = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<TenantDetailsResponse> => {
      const response = await fetch(
        `/api/tenants/${
          encodeURIComponent(tenantId)
        }/details`,
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
          `/?next=${
            encodeURIComponent(
              `/dashboard/tenants/${tenantId}`,
            )
          }`,
        );

        throw new Error("unauthorized");
      }

      if (response.status === 404) {
        throw new Error("not-found");
      }

      if (!response.ok) {
        throw new Error("load-failed");
      }

      return (
        await response.json()
      ) as TenantDetailsResponse;
    },
    [tenantId],
  );

  const refreshDetails = useCallback(
    async () => {
      setIsLoading(true);
      setLoadError(null);

      try {
        setData(
          await requestDetails(),
        );
      } catch (error) {
        setLoadError(
          error instanceof Error &&
          error.message === "not-found"
            ? copy.notFound
            : copy.loadError,
        );
      } finally {
        setIsLoading(false);
      }
    },
    [requestDetails],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadInitial(): Promise<void> {
      try {
        const payload =
          await requestDetails(
            controller.signal,
          );

        if (!controller.signal.aborted) {
          setData(payload);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setLoadError(
            error instanceof Error &&
            error.message === "not-found"
              ? copy.notFound
              : copy.loadError,
          );
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
  }, [requestDetails]);

  const activeApiKeys = useMemo(
    () =>
      data?.api_keys.filter(
        isActiveKey,
      ) ?? [],
    [data],
  );

  async function copyIdentifier(
    value: string,
  ): Promise<void> {
    try {
      await navigator.clipboard.writeText(
        value,
      );

      setCopiedValue(value);

      window.setTimeout(() => {
        setCopiedValue((current) =>
          current === value
            ? null
            : current,
        );
      }, 1400);
    } catch {
      setActionError(copy.actionFailed);
    }
  }

  async function toggleTenantStatus(): Promise<void> {
    if (data === null) {
      return;
    }

    setBusyAction("tenant-status");
    setActionError(null);

    try {
      const response = await fetch(
        `/api/tenants/${
          encodeURIComponent(tenantId)
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
            is_active:
              !data.tenant.is_active,
          }),
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Ftenants",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readError(response),
        );
        return;
      }

      const updated = (
        await response.json()
      ) as TenantDetailsResponse["tenant"];

      setData((current) =>
        current === null
          ? current
          : {
              ...current,
              tenant: {
                ...current.tenant,
                is_active:
                  updated.is_active,
                updated_at:
                  updated.updated_at,
              },
            },
      );
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAction(null);
    }
  }

  async function toggleAgentStatus(
    agent: TenantDetailsResponse["agents"][number],
  ): Promise<void> {
    const actionKey =
      `agent-status:${agent.id}`;

    setBusyAction(actionKey);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/agents/${
          encodeURIComponent(tenantId)
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
          `/?next=${
            encodeURIComponent(
              `/dashboard/tenants/${tenantId}`,
            )
          }`,
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readError(response),
        );
        return;
      }

      await refreshDetails();
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAction(null);
    }
  }

  async function permanentlyDeleteAgent(
    agent: TenantDetailsResponse["agents"][number],
  ): Promise<void> {
    if (agent.is_active) {
      setActionError(
        "يجب تعطيل الوكيل قبل الحذف النهائي.",
      );
      return;
    }

    const confirmation = window.prompt(
      `حذف الوكيل "${agent.name}" نهائيًا.\n\n` +
      "اكتب معرف الوكيل للتأكيد:\n" +
      agent.id,
      "",
    );

    if (confirmation === null) {
      return;
    }

    if (confirmation.trim() !== agent.id) {
      setActionError(
        "معرف التأكيد لا يطابق معرف الوكيل.",
      );
      return;
    }

    const actionKey =
      `agent-delete:${agent.id}`;

    setBusyAction(actionKey);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/agents/${
          encodeURIComponent(tenantId)
        }/${
          encodeURIComponent(agent.id)
        }?confirm=${
          encodeURIComponent(agent.id)
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
          `/?next=${
            encodeURIComponent(
              `/dashboard/tenants/${tenantId}`,
            )
          }`,
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readError(response),
        );
        return;
      }

      await refreshDetails();
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAction(null);
    }
  }

  async function revokeOneKey(): Promise<void> {
    if (revokeKeyTarget === null) {
      return;
    }

    const target = revokeKeyTarget;

    setBusyAction(
      `key:${target.key_id}`,
    );
    setActionError(null);

    try {
      const response = await fetch(
        `/api/tenants/${
          encodeURIComponent(tenantId)
        }/api-keys/${
          encodeURIComponent(target.key_id)
        }/revoke`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Ftenants",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readError(response),
        );
        return;
      }

      const updated = (
        await response.json()
      ) as TenantDetailApiKey;

      setData((current) => {
        if (current === null) {
          return current;
        }

        const keys = current.api_keys.map(
          (apiKey) =>
            apiKey.key_id ===
            updated.key_id
              ? updated
              : apiKey,
        );

        return recomputeKeySummary(
          current,
          keys,
        );
      });

      setRevokeKeyTarget(null);
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAction(null);
    }
  }

  async function revokeAllKeys(): Promise<void> {
    if (
      data === null ||
      revokeAllConfirmation !== tenantId
    ) {
      return;
    }

    setBusyAction("revoke-all");
    setActionError(null);

    try {
      const response = await fetch(
        `/api/tenants/${
          encodeURIComponent(tenantId)
        }/api-keys/revoke-all`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Ftenants",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readError(response),
        );
        return;
      }

      await response.json();

      const revokedAt =
        new Date().toISOString();

      setData((current) => {
        if (current === null) {
          return current;
        }

        const keys = current.api_keys.map(
          (apiKey) => ({
            ...apiKey,
            is_active: false,
            revoked_at:
              apiKey.revoked_at ??
              revokedAt,
          }),
        );

        return recomputeKeySummary(
          current,
          keys,
        );
      });

      setShowRevokeAll(false);
      setRevokeAllConfirmation("");
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyAction(null);
    }
  }

  if (isLoading && data === null) {
    return (
      <main className="tenant-details-page">
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
      <main className="tenant-details-page">
        <section className="tenants-state">
          <AlertTriangle aria-hidden="true" />
          <h2>{loadError}</h2>

          <Link
            className="details-back-link"
            href="/dashboard/tenants"
          >
            <ArrowRight aria-hidden="true" />
            {copy.back}
          </Link>

          <button
            type="button"
            onClick={() => {
              void refreshDetails();
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
      label: copy.totalAgents,
      value: data.summary.agents_total,
      icon: UsersRound,
    },
    {
      label: copy.activeAgents,
      value: data.summary.agents_active,
      icon: Bot,
    },
    {
      label: copy.totalKeys,
      value: data.summary.api_keys_total,
      icon: KeyRound,
    },
    {
      label: copy.activeKeys,
      value: data.summary.api_keys_active,
      icon: ShieldCheck,
    },
  ];

  return (
    <main className="tenant-details-page">
      <Link
        className="details-back-link"
        href="/dashboard/tenants"
      >
        <ArrowRight aria-hidden="true" />
        {copy.back}
      </Link>

      <section className="tenant-details-header">
        <div>
          <span className="tenant-details-header__eyebrow">
            <UsersRound aria-hidden="true" />
            {copy.eyebrow}
          </span>

          <div className="tenant-details-header__title">
            <h2>{data.tenant.name}</h2>

            <span
              className={
                data.tenant.is_active
                  ? "tenant-status is-active"
                  : "tenant-status"
              }
            >
              <i />
              {data.tenant.is_active
                ? copy.active
                : copy.inactive}
            </span>
          </div>

          <button
            className="tenant-id-copy"
            type="button"
            dir="ltr"
            onClick={() => {
              void copyIdentifier(
                data.tenant.id,
              );
            }}
          >
            <code>{data.tenant.id}</code>
            <Copy aria-hidden="true" />
            {copiedValue === data.tenant.id && (
              <small>{copy.copied}</small>
            )}
          </button>

          <p>{copy.description}</p>
        </div>

        <div className="tenant-details-header__actions">
          <button
            type="button"
            disabled={
              busyAction === "tenant-status"
            }
            onClick={() => {
              void toggleTenantStatus();
            }}
          >
            {busyAction === "tenant-status" ? (
              <LoaderCircle
                className="tenants-spinner"
                aria-hidden="true"
              />
            ) : data.tenant.is_active ? (
              <PowerOff aria-hidden="true" />
            ) : (
              <Power aria-hidden="true" />
            )}

            {data.tenant.is_active
              ? copy.suspend
              : copy.activate}
          </button>

          <button
            type="button"
            disabled={isLoading}
            onClick={() => {
              void refreshDetails();
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

      <section className="tenant-details-metrics">
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <article
              key={metric.label}
              className="tenant-details-metric"
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

      <section className="tenant-details-grid">
        <article className="tenant-details-panel">
          <header className="tenant-details-panel__header">
            <div>
              <h3>{copy.agents}</h3>
              <p>{copy.agentsDescription}</p>
            </div>

            <span>
              {numberFormatter.format(
                data.agents.length,
              )}
            </span>
          </header>

          {data.agents.length === 0 ? (
            <div className="tenant-details-empty">
              <Bot aria-hidden="true" />
              <p>{copy.noAgents}</p>
            </div>
          ) : (
            <div className="tenant-agent-list">
              {data.agents.map((agent) => (
                <div
                  key={agent.id}
                  className="tenant-agent-row"
                >
                  <span className="tenant-agent-row__icon">
                    <Bot aria-hidden="true" />
                  </span>

                  <div className="tenant-agent-row__identity">
                    <strong>{agent.name}</strong>

                    <button
                      type="button"
                      dir="ltr"
                      onClick={() => {
                        void copyIdentifier(
                          agent.id,
                        );
                      }}
                    >
                      <code>{agent.id}</code>
                      <Copy aria-hidden="true" />
                    </button>
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
                      ? copy.active
                      : copy.inactive}
                  </span>

                  <span className="knowledge-mode">
                    {agent.knowledge_mode === "required"
                      ? copy.required
                      : agent.knowledge_mode === "preferred"
                        ? copy.preferred
                        : copy.disabled}
                  </span>

              <div
                style={{
                  display: "flex",
                  gap: "0.5rem",
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <button
                  type="button"
                  disabled={
                    busyAction !== null
                  }
                  onClick={() => {
                    void toggleAgentStatus(
                      agent,
                    );
                  }}
                >
                  {busyAction ===
                  `agent-status:${agent.id}` ? (
                    <LoaderCircle
                      aria-hidden="true"
                    />
                  ) : agent.is_active ? (
                    <PowerOff
                      aria-hidden="true"
                    />
                  ) : (
                    <Power
                      aria-hidden="true"
                    />
                  )}

                  {agent.is_active
                    ? "تعطيل"
                    : "تفعيل"}
                </button>

                <button
                  type="button"
                  className="revoke-all-button"
                  disabled={
                    busyAction !== null ||
                    agent.is_active
                  }
                  title={
                    agent.is_active
                      ? "عطّل الوكيل أولًا قبل الحذف."
                      : "حذف الوكيل نهائيًا."
                  }
                  onClick={() => {
                    void permanentlyDeleteAgent(
                      agent,
                    );
                  }}
                >
                  {busyAction ===
                  `agent-delete:${agent.id}` ? (
                    <LoaderCircle
                      aria-hidden="true"
                    />
                  ) : (
                    <Trash2
                      aria-hidden="true"
                    />
                  )}

                  حذف
                </button>
              </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="tenant-details-panel tenant-details-panel--keys">
          <header className="tenant-details-panel__header">
            <div>
              <h3>{copy.apiKeys}</h3>
              <p>{copy.apiKeysDescription}</p>
            </div>

            <button
              className="revoke-all-button"
              type="button"
              disabled={
                activeApiKeys.length === 0
              }
              onClick={() => {
                setShowRevokeAll(true);
                setRevokeAllConfirmation("");
                setActionError(null);
              }}
            >
              <Ban aria-hidden="true" />
              {copy.revokeAll}
            </button>
          </header>

          {data.api_keys.length === 0 ? (
            <div className="tenant-details-empty">
              <KeyRound aria-hidden="true" />
              <p>{copy.noKeys}</p>
            </div>
          ) : (
            <div className="tenant-key-table">
              {data.api_keys.map((apiKey) => {
                const state =
                  getKeyState(apiKey);

                const isBusy =
                  busyAction ===
                  `key:${apiKey.key_id}`;

                return (
                  <div
                    key={apiKey.key_id}
                    className="tenant-key-row"
                  >
                    <div className="tenant-key-row__identity">
                      <span>
                        <KeyRound aria-hidden="true" />
                      </span>

                      <div>
                        <strong>
                          {apiKey.name ??
                            copy.unknown}
                        </strong>

                        <button
                          type="button"
                          dir="ltr"
                          onClick={() => {
                            void copyIdentifier(
                              apiKey.key_id,
                            );
                          }}
                        >
                          <code>
                            {apiKey.key_id}
                          </code>
                          <Copy aria-hidden="true" />
                        </button>
                      </div>
                    </div>

                    <span
                      className={`api-key-state is-${state}`}
                    >
                      {state === "active" && (
                        <CheckCircle2
                          aria-hidden="true"
                        />
                      )}

                      {state === "revoked" && (
                        <Ban aria-hidden="true" />
                      )}

                      {state === "expired" && (
                        <Clock3 aria-hidden="true" />
                      )}

                      {state === "inactive" && (
                        <PowerOff aria-hidden="true" />
                      )}

                      {state === "active"
                        ? copy.active
                        : state === "revoked"
                          ? copy.revoked
                          : state === "expired"
                            ? copy.expired
                            : copy.inactive}
                    </span>

                    <dl className="tenant-key-row__dates">
                      <div>
                        <dt>{copy.lastUsed}</dt>
                        <dd>
                          {formatDate(
                            apiKey.last_used_at,
                            copy.notUsed,
                          )}
                        </dd>
                      </div>

                      <div>
                        <dt>{copy.expires}</dt>
                        <dd>
                          {formatDate(
                            apiKey.expires_at,
                            copy.never,
                          )}
                        </dd>
                      </div>
                    </dl>

                    <button
                      className="revoke-key-button"
                      type="button"
                      disabled={
                        state !== "active" ||
                        isBusy
                      }
                      onClick={() => {
                        setRevokeKeyTarget(
                          apiKey,
                        );
                        setActionError(null);
                      }}
                    >
                      {isBusy ? (
                        <LoaderCircle
                          className="tenants-spinner"
                          aria-hidden="true"
                        />
                      ) : (
                        <Ban aria-hidden="true" />
                      )}
                      {copy.revoke}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </article>
      </section>

      {revokeKeyTarget && (
        <div className="tenant-dialog-backdrop">
          <section
            className="tenant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="revoke-key-title"
          >
            <header>
              <span>
                <AlertTriangle aria-hidden="true" />
              </span>

              <button
                type="button"
                aria-label="\u0625\u063a\u0644\u0627\u0642"
                disabled={
                  busyAction ===
                  `key:${revokeKeyTarget.key_id}`
                }
                onClick={() => {
                  setRevokeKeyTarget(null);
                }}
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <h3 id="revoke-key-title">
              {copy.revokeOneTitle}
            </h3>

            <p>{copy.revokeOneWarning}</p>

            <strong className="tenant-dialog__name">
              {revokeKeyTarget.name ??
                copy.unknown}
            </strong>

            <code
              className="tenant-dialog__id"
              dir="ltr"
            >
              {revokeKeyTarget.key_id}
            </code>

            <footer>
              <button
                type="button"
                disabled={
                  busyAction ===
                  `key:${revokeKeyTarget.key_id}`
                }
                onClick={() => {
                  setRevokeKeyTarget(null);
                }}
              >
                {copy.cancel}
              </button>

              <button
                type="button"
                className="is-danger"
                disabled={
                  busyAction ===
                  `key:${revokeKeyTarget.key_id}`
                }
                onClick={() => {
                  void revokeOneKey();
                }}
              >
                <Ban aria-hidden="true" />
                {copy.confirmRevoke}
              </button>
            </footer>
          </section>
        </div>
      )}

      {showRevokeAll && (
        <div className="tenant-dialog-backdrop">
          <section
            className="tenant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="revoke-all-title"
          >
            <header>
              <span>
                <AlertTriangle aria-hidden="true" />
              </span>

              <button
                type="button"
                aria-label="\u0625\u063a\u0644\u0627\u0642"
                disabled={
                  busyAction === "revoke-all"
                }
                onClick={() => {
                  setShowRevokeAll(false);
                  setRevokeAllConfirmation("");
                }}
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <h3 id="revoke-all-title">
              {copy.revokeAllTitle}
            </h3>

            <p>{copy.revokeAllWarning}</p>

            <code
              className="tenant-dialog__id"
              dir="ltr"
            >
              {tenantId}
            </code>

            <label htmlFor="revoke-all-confirmation">
              {copy.tenantId}
            </label>

            <input
              id="revoke-all-confirmation"
              type="text"
              dir="ltr"
              autoComplete="off"
              value={revokeAllConfirmation}
              onChange={(event) => {
                setRevokeAllConfirmation(
                  event.target.value,
                );
              }}
            />

            <footer>
              <button
                type="button"
                disabled={
                  busyAction === "revoke-all"
                }
                onClick={() => {
                  setShowRevokeAll(false);
                  setRevokeAllConfirmation("");
                }}
              >
                {copy.cancel}
              </button>

              <button
                type="button"
                className="is-danger"
                disabled={
                  revokeAllConfirmation !==
                    tenantId ||
                  busyAction === "revoke-all"
                }
                onClick={() => {
                  void revokeAllKeys();
                }}
              >
                {busyAction === "revoke-all" ? (
                  <LoaderCircle
                    className="tenants-spinner"
                    aria-hidden="true"
                  />
                ) : (
                  <Trash2 aria-hidden="true" />
                )}
                {copy.confirmRevoke}
              </button>
            </footer>
          </section>
        </div>
      )}
    </main>
  );
}
