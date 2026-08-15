"use client";

import {
  Bot,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  MessageSquareText,
  MessagesSquare,
  RefreshCw,
  Search,
  Sparkles,
  UserRound,
  UsersRound,
  Wrench,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import styles from "./conversations-view.module.css";

import type {
  ConversationDirectoryResponse,
  ConversationMessageRecord,
  ConversationMessagesResponse,
  ConversationRecord,
} from "@/lib/conversations/contracts";
import type {
  TenantDirectoryItem,
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";

const copy = {
  eyebrow: "مراقبة المحادثات",
  title: "محادثات العملاء والوكلاء",
  description:
    "استعرض المحادثات المحفوظة، راقب الرسائل وحالة الإجابات، وتحقق من نشاط كل وكيل داخل نطاق العميل الصحيح.",
  refresh: "تحديث البيانات",
  tenant: "العميل",
  chooseTenant: "اختر العميل",
  searchLabel: "البحث",
  search: "ابحث في المحادثة أو المستخدم أو الوكيل",
  agent: "الوكيل",
  allAgents: "جميع الوكلاء",
  conversations: "المحادثات",
  messages: "إجمالي الرسائل",
  userMessages: "رسائل المستخدم",
  assistantMessages: "ردود الوكيل",
  directory: "قائمة المحادثات",
  conversationCount: "محادثة",
  noConversation: "لا توجد محادثات لهذا العميل.",
  noSearchResult: "لا توجد محادثات تطابق البحث والتصفية.",
  selectConversation: "اختر محادثة لعرض الرسائل.",
  loadingTenants: "جاري تحميل العملاء",
  loadingConversations: "جاري تحميل المحادثات",
  loadingMessages: "جاري تحميل الرسائل",
  tenantError: "تعذر تحميل قائمة العملاء.",
  directoryError: "تعذر تحميل محادثات العميل.",
  detailsError: "تعذر تحميل تفاصيل المحادثة ورسائلها.",
  retry: "إعادة المحاولة",
  userIdentifier: "معرف المستخدم",
  anonymous: "مستخدم غير معرّف",
  conversationId: "معرف المحادثة",
  createdAt: "تاريخ الإنشاء",
  updatedAt: "آخر نشاط",
  messageCount: "الرسائل",
  userRole: "المستخدم",
  assistantRole: "الوكيل",
  systemRole: "النظام",
  toolRole: "أداة",
  answerStatus: "حالة الإجابة",
  sources: "المصادر",
  noMessages: "لا توجد رسائل محفوظة في هذه المحادثة.",
  grounded: "إجابة موثقة",
  generated: "إجابة مولدة",
  insufficientKnowledge: "معرفة غير كافية",
  temporarilyUnavailable: "الخدمة غير متاحة مؤقتًا",
  metadata: "بيانات الجلسة",
  noMetadata: "لا توجد بيانات وصفية إضافية.",
} as const;

const numberFormatter = new Intl.NumberFormat("ar");

const dateFormatter = new Intl.DateTimeFormat(
  "ar",
  {
    dateStyle: "medium",
    timeStyle: "short",
  },
);

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : dateFormatter.format(date);
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}

async function requestJson<T>(
  url: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(
    url,
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
      "/?next=%2Fdashboard%2Fconversations",
    );

    throw new Error(
      "Admin session is not active.",
    );
  }

  if (!response.ok) {
    throw new Error(
      `Conversation request failed: ${response.status}`,
    );
  }

  return (await response.json()) as T;
}

function roleLabel(
  role: ConversationMessageRecord["role"],
): string {
  if (role === "user") {
    return copy.userRole;
  }

  if (role === "assistant") {
    return copy.assistantRole;
  }

  if (role === "system") {
    return copy.systemRole;
  }

  return copy.toolRole;
}

function answerStatusLabel(
  value: unknown,
): string | null {
  if (value === "grounded") {
    return copy.grounded;
  }

  if (value === "generated") {
    return copy.generated;
  }

  if (value === "insufficient_knowledge") {
    return copy.insufficientKnowledge;
  }

  if (value === "temporarily_unavailable") {
    return copy.temporarilyUnavailable;
  }

  return typeof value === "string"
    ? value
    : null;
}

function messageClass(
  role: ConversationMessageRecord["role"],
): string {
  if (role === "user") {
    return styles.messageUser;
  }

  if (role === "assistant") {
    return styles.messageAssistant;
  }

  if (role === "tool") {
    return styles.messageTool;
  }

  return styles.messageSystem;
}

function MessageRoleIcon({
  role,
}: {
  role: ConversationMessageRecord["role"];
}) {
  if (role === "user") {
    return <UserRound aria-hidden="true" />;
  }

  if (role === "assistant") {
    return <Sparkles aria-hidden="true" />;
  }

  if (role === "tool") {
    return <Wrench aria-hidden="true" />;
  }

  return <MessageSquareText aria-hidden="true" />;
}

export function ConversationsView() {
  const [tenants, setTenants] =
    useState<TenantDirectoryItem[]>([]);
  const [selectedTenantId, setSelectedTenantId] =
    useState("");
  const [directory, setDirectory] =
    useState<ConversationDirectoryResponse | null>(
      null,
    );
  const [
    selectedConversationId,
    setSelectedConversationId,
  ] = useState("");
  const [conversation, setConversation] =
    useState<ConversationRecord | null>(null);
  const [messages, setMessages] =
    useState<ConversationMessageRecord[]>([]);
  const [search, setSearch] = useState("");
  const [agentFilter, setAgentFilter] =
    useState("all");
  const [refreshVersion, setRefreshVersion] =
    useState(0);
  const [
    detailRefreshVersion,
    setDetailRefreshVersion,
  ] = useState(0);
  const [isLoadingTenants, setIsLoadingTenants] =
    useState(true);
  const [
    isLoadingDirectory,
    setIsLoadingDirectory,
  ] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] =
    useState(false);
  const [tenantsError, setTenantsError] =
    useState<string | null>(null);
  const [directoryError, setDirectoryError] =
    useState<string | null>(null);
  const [detailsError, setDetailsError] =
    useState<string | null>(null);

  useEffect(() => {
    const controller =
      new AbortController();

    void requestJson<TenantDirectoryResponse>(
      "/api/tenants",
      controller.signal,
    )
      .then((payload) => {
        if (controller.signal.aborted) {
          return;
        }

        const firstTenant =
          payload.items.find(
            (item) => item.is_active,
          ) ?? payload.items[0];

        setTenants(payload.items);
        setTenantsError(null);
        setSelectedTenantId(
          firstTenant?.id ?? "",
        );
        setIsLoadingDirectory(
          Boolean(firstTenant),
        );
      })
      .catch((error: unknown) => {
        if (
          !controller.signal.aborted &&
          !isAbortError(error)
        ) {
          setTenantsError(
            copy.tenantError,
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoadingTenants(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!selectedTenantId) {
      return;
    }

    const controller =
      new AbortController();

    const path =
      `/api/conversations/${
        encodeURIComponent(
          selectedTenantId,
        )
      }?limit=200&offset=0`;

    void requestJson<ConversationDirectoryResponse>(
      path,
      controller.signal,
    )
      .then((payload) => {
        if (controller.signal.aborted) {
          return;
        }

        const firstConversationId =
          payload.items[0]?.id ?? "";

        setDirectory(payload);
        setDirectoryError(null);
        setSelectedConversationId(
          firstConversationId,
        );
        setConversation(null);
        setMessages([]);
        setIsLoadingDetails(
          Boolean(firstConversationId),
        );
      })
      .catch((error: unknown) => {
        if (
          !controller.signal.aborted &&
          !isAbortError(error)
        ) {
          setDirectoryError(
            copy.directoryError,
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoadingDirectory(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [
    refreshVersion,
    selectedTenantId,
  ]);

  useEffect(() => {
    if (
      !selectedTenantId ||
      !selectedConversationId
    ) {
      return;
    }

    const controller =
      new AbortController();

    const basePath =
      `/api/conversations/${
        encodeURIComponent(
          selectedTenantId,
        )
      }/${
        encodeURIComponent(
          selectedConversationId,
        )
      }`;

    void Promise.all([
      requestJson<ConversationRecord>(
        basePath,
        controller.signal,
      ),
      requestJson<ConversationMessagesResponse>(
        `${basePath}/messages?limit=500&offset=0`,
        controller.signal,
      ),
    ])
      .then(
        ([
          conversationPayload,
          messagesPayload,
        ]) => {
          if (controller.signal.aborted) {
            return;
          }

          setConversation(
            conversationPayload,
          );
          setMessages(
            messagesPayload.items,
          );
          setDetailsError(null);
        },
      )
      .catch((error: unknown) => {
        if (
          !controller.signal.aborted &&
          !isAbortError(error)
        ) {
          setDetailsError(
            copy.detailsError,
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoadingDetails(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [
    detailRefreshVersion,
    selectedConversationId,
    selectedTenantId,
  ]);

  const selectedTenant = useMemo(
    () =>
      tenants.find(
        (tenant) =>
          tenant.id === selectedTenantId,
      ) ?? null,
    [selectedTenantId, tenants],
  );

  const agentOptions = useMemo(() => {
    const map = new Map<string, string>();

    for (const item of directory?.items ?? []) {
      map.set(
        item.agent_id,
        item.agent_name,
      );
    }

    return Array.from(map.entries()).sort(
      (left, right) =>
        left[1].localeCompare(
          right[1],
          "ar",
        ),
    );
  }, [directory]);

  const visibleConversations = useMemo(() => {
    const normalizedSearch =
      search.trim().toLocaleLowerCase();

    return (directory?.items ?? []).filter(
      (item) => {
        const matchesAgent =
          agentFilter === "all" ||
          item.agent_id === agentFilter;

        const searchable = [
          item.id,
          item.agent_id,
          item.agent_name,
          item.user_identifier ?? "",
          item.last_message_preview ?? "",
        ]
          .join(" ")
          .toLocaleLowerCase();

        return (
          matchesAgent &&
          (
            !normalizedSearch ||
            searchable.includes(
              normalizedSearch,
            )
          )
        );
      },
    );
  }, [
    agentFilter,
    directory,
    search,
  ]);

  const totals = useMemo(() => {
    return (directory?.items ?? []).reduce(
      (current, item) => ({
        messages:
          current.messages +
          item.message_count,
        user:
          current.user +
          item.user_message_count,
        assistant:
          current.assistant +
          item.assistant_message_count,
      }),
      {
        messages: 0,
        user: 0,
        assistant: 0,
      },
    );
  }, [directory]);

  function selectTenant(
    tenantId: string,
  ): void {
    setSelectedTenantId(tenantId);
    setDirectory(null);
    setSelectedConversationId("");
    setConversation(null);
    setMessages([]);
    setSearch("");
    setAgentFilter("all");
    setDirectoryError(null);
    setDetailsError(null);
    setIsLoadingDirectory(
      Boolean(tenantId),
    );
    setIsLoadingDetails(false);
  }

  function selectConversation(
    conversationId: string,
  ): void {
    if (
      conversationId ===
      selectedConversationId
    ) {
      return;
    }

    setSelectedConversationId(
      conversationId,
    );
    setConversation(null);
    setMessages([]);
    setDetailsError(null);
    setIsLoadingDetails(true);
  }

  function refreshDirectory(): void {
    if (!selectedTenantId) {
      return;
    }

    setDirectoryError(null);
    setDetailsError(null);
    setIsLoadingDirectory(true);
    setRefreshVersion(
      (current) => current + 1,
    );
  }

  function retryDetails(): void {
    setDetailsError(null);
    setIsLoadingDetails(true);
    setDetailRefreshVersion(
      (current) => current + 1,
    );
  }

  return (
    <main
      className={styles.view}
      dir="rtl"
    >
      <section className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>
            <MessagesSquare
              aria-hidden="true"
            />
            {copy.eyebrow}
          </div>

          <h1>{copy.title}</h1>
          <p>{copy.description}</p>
        </div>

        <button
          type="button"
          className={styles.primaryButton}
          disabled={
            !selectedTenantId ||
            isLoadingDirectory
          }
          onClick={refreshDirectory}
        >
          <RefreshCw
            className={
              isLoadingDirectory
                ? styles.spinning
                : undefined
            }
            aria-hidden="true"
          />
          {copy.refresh}
        </button>
      </section>

      <section className={styles.controls}>
        <label className={styles.field}>
          <span>
            <UsersRound aria-hidden="true" />
            {copy.tenant}
          </span>

          <select
            value={selectedTenantId}
            disabled={isLoadingTenants}
            onChange={(event) => {
              selectTenant(
                event.target.value,
              );
            }}
          >
            <option value="">
              {isLoadingTenants
                ? copy.loadingTenants
                : copy.chooseTenant}
            </option>

            {tenants.map((tenant) => (
              <option
                key={tenant.id}
                value={tenant.id}
              >
                {tenant.name}
                {!tenant.is_active
                  ? " — متوقف"
                  : ""}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>
            <Search aria-hidden="true" />
            {copy.searchLabel}
          </span>

          <input
            type="search"
            value={search}
            placeholder={copy.search}
            onChange={(event) => {
              setSearch(
                event.target.value,
              );
            }}
          />
        </label>

        <label className={styles.field}>
          <span>
            <Bot aria-hidden="true" />
            {copy.agent}
          </span>

          <select
            value={agentFilter}
            onChange={(event) => {
              setAgentFilter(
                event.target.value,
              );
            }}
          >
            <option value="all">
              {copy.allAgents}
            </option>

            {agentOptions.map(
              ([
                agentId,
                agentName,
              ]) => (
                <option
                  key={agentId}
                  value={agentId}
                >
                  {agentName}
                </option>
              ),
            )}
          </select>
        </label>
      </section>

      {tenantsError && (
        <section className={styles.errorBanner}>
          <span>{tenantsError}</span>
          <button
            type="button"
            onClick={() => {
              window.location.reload();
            }}
          >
            {copy.retry}
          </button>
        </section>
      )}

      {directoryError && (
        <section className={styles.errorBanner}>
          <span>{directoryError}</span>
          <button
            type="button"
            onClick={refreshDirectory}
          >
            {copy.retry}
          </button>
        </section>
      )}

      <section className={styles.stats}>
        <article>
          <MessagesSquare aria-hidden="true" />
          <span>{copy.conversations}</span>
          <strong>
            {numberFormatter.format(
              directory?.total ?? 0,
            )}
          </strong>
        </article>

        <article>
          <MessageSquareText aria-hidden="true" />
          <span>{copy.messages}</span>
          <strong>
            {numberFormatter.format(
              totals.messages,
            )}
          </strong>
        </article>

        <article>
          <UserRound aria-hidden="true" />
          <span>{copy.userMessages}</span>
          <strong>
            {numberFormatter.format(
              totals.user,
            )}
          </strong>
        </article>

        <article>
          <Sparkles aria-hidden="true" />
          <span>{copy.assistantMessages}</span>
          <strong>
            {numberFormatter.format(
              totals.assistant,
            )}
          </strong>
        </article>
      </section>

      <section className={styles.workspace}>
        <aside className={styles.directory}>
          <header>
            <div>
              <strong>{copy.directory}</strong>
              <small>
                {selectedTenant?.name ??
                  copy.chooseTenant}
              </small>
            </div>

            <span>
              {numberFormatter.format(
                visibleConversations.length,
              )}
              {" "}
              {copy.conversationCount}
            </span>
          </header>

          <div className={styles.directoryBody}>
            {isLoadingDirectory ? (
              <div className={styles.centerState}>
                <LoaderCircle
                  className={styles.spinning}
                  aria-hidden="true"
                />
                <span>
                  {copy.loadingConversations}
                </span>
              </div>
            ) : visibleConversations.length > 0 ? (
              visibleConversations.map(
                (item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`${styles.conversationCard} ${
                      item.id ===
                      selectedConversationId
                        ? styles.selectedCard
                        : ""
                    }`}
                    onClick={() => {
                      selectConversation(
                        item.id,
                      );
                    }}
                  >
                    <div className={styles.cardTop}>
                      <span className={styles.avatar}>
                        <Bot aria-hidden="true" />
                      </span>

                      <div>
                        <strong>
                          {item.agent_name}
                        </strong>
                        <small>
                          {item.user_identifier ??
                            copy.anonymous}
                        </small>
                      </div>

                      <time>
                        {formatDate(
                          item.updated_at,
                        )}
                      </time>
                    </div>

                    <p>
                      {item.last_message_preview ??
                        copy.noMessages}
                    </p>

                    <div className={styles.cardMeta}>
                      <span>
                        <MessageSquareText
                          aria-hidden="true"
                        />
                        {numberFormatter.format(
                          item.message_count,
                        )}
                      </span>

                      <code>{item.id}</code>
                    </div>
                  </button>
                ),
              )
            ) : (
              <div className={styles.centerState}>
                <MessagesSquare aria-hidden="true" />
                <span>
                  {directory?.items.length
                    ? copy.noSearchResult
                    : copy.noConversation}
                </span>
              </div>
            )}
          </div>
        </aside>

        <section className={styles.detail}>
          {!selectedConversationId ? (
            <div className={styles.detailState}>
              <MessageSquareText aria-hidden="true" />
              <h2>{copy.selectConversation}</h2>
            </div>
          ) : isLoadingDetails ? (
            <div className={styles.detailState}>
              <LoaderCircle
                className={styles.spinning}
                aria-hidden="true"
              />
              <h2>{copy.loadingMessages}</h2>
            </div>
          ) : detailsError ? (
            <div className={styles.detailState}>
              <MessageSquareText aria-hidden="true" />
              <h2>{detailsError}</h2>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={retryDetails}
              >
                {copy.retry}
              </button>
            </div>
          ) : conversation ? (
            <>
              <header className={styles.detailHeader}>
                <div>
                  <span className={styles.largeAvatar}>
                    <Bot aria-hidden="true" />
                  </span>

                  <div>
                    <span>{copy.agent}</span>
                    <h2>
                      {conversation.agent_name}
                    </h2>
                    <code>
                      {conversation.agent_id}
                    </code>
                  </div>
                </div>

                <div className={styles.lastActivity}>
                  <span>
                    <Clock3 aria-hidden="true" />
                    {copy.updatedAt}
                  </span>
                  <strong>
                    {formatDate(
                      conversation.updated_at,
                    )}
                  </strong>
                </div>
              </header>

              <div className={styles.infoGrid}>
                <article>
                  <span>{copy.userIdentifier}</span>
                  <strong>
                    {conversation.user_identifier ??
                      copy.anonymous}
                  </strong>
                </article>

                <article>
                  <span>{copy.conversationId}</span>
                  <code>{conversation.id}</code>
                </article>

                <article>
                  <span>{copy.createdAt}</span>
                  <strong>
                    {formatDate(
                      conversation.created_at,
                    )}
                  </strong>
                </article>

                <article>
                  <span>{copy.messageCount}</span>
                  <strong>
                    {numberFormatter.format(
                      conversation.message_count,
                    )}
                  </strong>
                </article>
              </div>

              <div className={styles.transcript}>
                {messages.length > 0 ? (
                  messages.map((message) => {
                    const status =
                      answerStatusLabel(
                        message.metadata?.answer_status,
                      );

                    const sourceCount =
                      Array.isArray(
                        message.metadata?.sources,
                      )
                        ? message.metadata.sources.length
                        : 0;

                    return (
                      <article
                        key={message.id}
                        className={`${styles.message} ${messageClass(
                          message.role,
                        )}`}
                      >
                        <header>
                          <span>
                            <MessageRoleIcon
                              role={message.role}
                            />
                            {roleLabel(
                              message.role,
                            )}
                          </span>

                          <time>
                            {formatDate(
                              message.created_at,
                            )}
                          </time>
                        </header>

                        <p>{message.content}</p>

                        {(status ||
                          sourceCount > 0) && (
                          <footer>
                            {status && (
                              <span>
                                <CheckCircle2
                                  aria-hidden="true"
                                />
                                {copy.answerStatus}:{" "}
                                {status}
                              </span>
                            )}

                            {sourceCount > 0 && (
                              <span>
                                <MessagesSquare
                                  aria-hidden="true"
                                />
                                {copy.sources}:{" "}
                                {numberFormatter.format(
                                  sourceCount,
                                )}
                              </span>
                            )}
                          </footer>
                        )}
                      </article>
                    );
                  })
                ) : (
                  <div className={styles.centerState}>
                    <MessageSquareText aria-hidden="true" />
                    <span>{copy.noMessages}</span>
                  </div>
                )}
              </div>

              <details className={styles.metadata}>
                <summary>
                  {copy.metadata}
                </summary>
                <pre>
                  {conversation.metadata
                    ? JSON.stringify(
                        conversation.metadata,
                        null,
                        2,
                      )
                    : copy.noMetadata}
                </pre>
              </details>
            </>
          ) : null}
        </section>
      </section>
    </main>
  );
}
