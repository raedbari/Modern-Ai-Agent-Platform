"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Bot,
  MessageSquareText,
  LoaderCircle,
  ArrowRight,
  Search,
  UserRound,
  Sparkles,
  Wrench,
} from "lucide-react";

import styles from "./customer-conversations.module.css";
import type {
  ConversationRecord,
  ConversationMessageRecord,
} from "@/lib/conversations/contracts";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffSeconds = Math.floor((now - then) / 1000);
  const rtf = new Intl.RelativeTimeFormat("ar", { numeric: "auto" });
  if (diffSeconds < 60) return rtf.format(-diffSeconds, "second");
  if (diffSeconds < 3600) return rtf.format(-Math.floor(diffSeconds / 60), "minute");
  if (diffSeconds < 86400) return rtf.format(-Math.floor(diffSeconds / 3600), "hour");
  return rtf.format(-Math.floor(diffSeconds / 86400), "day");
}

const arabicDateFormatter = new Intl.DateTimeFormat("ar", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return Number.isNaN(date.getTime()) ? isoString : arabicDateFormatter.format(date);
}

function roleLabel(role: ConversationMessageRecord["role"]): string {
  if (role === "user") return "المستخدم";
  if (role === "assistant") return "الوكيل";
  if (role === "system") return "النظام";
  return "أداة";
}

function RoleIcon({ role }: { role: ConversationMessageRecord["role"] }) {
  if (role === "user") return <UserRound size={14} aria-hidden="true" />;
  if (role === "assistant") return <Sparkles size={14} aria-hidden="true" />;
  if (role === "tool") return <Wrench size={14} aria-hidden="true" />;
  return <MessageSquareText size={14} aria-hidden="true" />;
}

// ─── Sub-Components ───────────────────────────────────────────────────────────

interface ConversationListPanelProps {
  conversations: ConversationRecord[];
  allConversations: ConversationRecord[];
  total: number;
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  search: string;
  agentFilter: string;
  agentOptions: [string, string][];
  onSearchChange: (value: string) => void;
  onAgentFilterChange: (value: string) => void;
  onSelect: (id: string) => void;
  onRetry: () => void;
}

function ConversationListPanel({
  conversations,
  allConversations,
  total,
  selectedId,
  loading,
  error,
  search,
  agentFilter,
  agentOptions,
  onSearchChange,
  onAgentFilterChange,
  onSelect,
  onRetry,
}: ConversationListPanelProps) {
  return (
    <>
      {/* Header */}
      <div className={styles.panelHeader}>
        <h2 className={styles.panelTitle}>المحادثات</h2>
        <span className={styles.badge} aria-label={`${total} محادثة`}>
          {total}
        </span>
      </div>

      {/* Search + Filter */}
      <div className={styles.searchRow}>
        <div className={styles.searchInputWrapper}>
          <Search size={15} aria-hidden="true" className={styles.searchIcon} />
          <input
            type="search"
            placeholder="بحث..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className={styles.searchInput}
            aria-label="بحث في المحادثات"
          />
        </div>
        <select
          value={agentFilter}
          onChange={(e) => onAgentFilterChange(e.target.value)}
          className={styles.agentSelect}
          aria-label="تصفية حسب الوكيل"
        >
          <option value="all">جميع الوكلاء</option>
          {agentOptions.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {/* Body */}
      <div className={styles.listScroll} role="list" aria-label="قائمة المحادثات">
        {loading ? (
          <>
            {[0, 1, 2].map((i) => (
              <div key={i} className={styles.skeleton} aria-hidden="true" />
            ))}
          </>
        ) : error ? (
          <div className={styles.centerState}>
            <MessageSquareText size={40} aria-hidden="true" />
            <p>{error}</p>
            <button
              type="button"
              className={styles.retryButton}
              onClick={onRetry}
            >
              إعادة المحاولة
            </button>
          </div>
        ) : conversations.length === 0 ? (
          <div className={styles.centerState}>
            <MessageSquareText size={40} aria-hidden="true" />
            <p>
              {allConversations.length === 0
                ? "لا توجد محادثات حتى الآن"
                : "لا توجد نتائج مطابقة"}
            </p>
          </div>
        ) : (
          conversations.map((conv) => (
            <button
              key={conv.id}
              type="button"
              role="listitem"
              className={`${styles.card} ${selectedId === conv.id ? styles.selectedCard : ""}`}
              onClick={() => onSelect(conv.id)}
              aria-current={selectedId === conv.id ? "true" : undefined}
              aria-label={`محادثة مع ${conv.agent_name}`}
            >
              <div className={styles.cardTop}>
                <span className={styles.cardAvatar} aria-hidden="true">
                  <Bot size={18} />
                </span>
                <div className={styles.cardInfo}>
                  <strong className={styles.cardAgentName}>{conv.agent_name}</strong>
                  <small className={styles.cardUserIdentifier}>
                    {conv.user_identifier ?? "زائر مجهول"}
                  </small>
                </div>
                <time className={styles.cardTime} dateTime={conv.updated_at}>
                  {formatRelativeTime(conv.updated_at)}
                </time>
              </div>
              <p className={styles.preview} dir="auto">
                {conv.last_message_preview ?? "لا توجد رسائل"}
              </p>
              <div className={styles.cardMeta}>
                <span className={styles.cardMessageCount} aria-label={`${conv.message_count} رسالة`}>
                  <MessageSquareText size={13} aria-hidden="true" />
                  {conv.message_count}
                </span>
                <code className={styles.cardId}>{conv.id.slice(0, 8)}…</code>
              </div>
            </button>
          ))
        )}
      </div>
    </>
  );
}

// ─── Message Bubble ────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: ConversationMessageRecord }) {
  const bubbleClass =
    message.role === "user"
      ? styles.bubbleUser
      : message.role === "assistant"
        ? styles.bubbleAssistant
        : message.role === "system"
          ? styles.bubbleSystem
          : styles.bubbleTool;

  return (
    <article
      className={`${styles.bubble} ${bubbleClass}`}
      aria-label={`رسالة ${roleLabel(message.role)}`}
    >
      <header className={styles.bubbleHeader}>
        <span className={styles.bubbleRole}>
          <RoleIcon role={message.role} />
          {roleLabel(message.role)}
        </span>
        <time className={styles.bubbleTime} dateTime={message.created_at}>
          {formatRelativeTime(message.created_at)}
        </time>
      </header>
      <p dir="auto" className={styles.bubbleContent}>
        {message.content}
      </p>
    </article>
  );
}

// ─── Detail Panel ──────────────────────────────────────────────────────────────

interface ConversationDetailPanelProps {
  conversation: ConversationRecord | null;
  messages: ConversationMessageRecord[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onBack: () => void;
  isMobile: boolean;
}

function ConversationDetailPanel({
  conversation,
  messages,
  loading,
  error,
  onRetry,
  onBack,
  isMobile,
}: ConversationDetailPanelProps) {
  // No selection state
  if (!conversation && !loading && !error) {
    return (
      <div className={styles.centerState} style={{ flex: 1 }}>
        <MessageSquareText size={48} aria-hidden="true" />
        <p>اختر محادثة للاطلاع على تفاصيلها</p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className={styles.centerState} style={{ flex: 1 }}>
        <LoaderCircle size={40} className={styles.spinning} aria-label="جاري التحميل" />
        <p>جاري تحميل الرسائل…</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={styles.centerState} style={{ flex: 1 }}>
        <MessageSquareText size={48} aria-hidden="true" />
        <p>{error}</p>
        <button type="button" className={styles.retryButton} onClick={onRetry}>
          إعادة المحاولة
        </button>
      </div>
    );
  }

  // Content view
  if (!conversation) return null;

  return (
    <>
      {/* Back button — mobile only */}
      {isMobile && (
        <button
          type="button"
          className={styles.backButton}
          onClick={onBack}
          aria-label="العودة إلى قائمة المحادثات"
        >
          <ArrowRight size={18} aria-hidden="true" />
          رجوع
        </button>
      )}

      {/* Conversation header */}
      <div className={styles.detailHeader}>
        <span className={styles.detailAvatar} aria-hidden="true">
          <Bot size={22} />
        </span>
        <div className={styles.detailHeaderInfo}>
          <strong className={styles.detailAgentName}>{conversation.agent_name}</strong>
          <span className={styles.detailUserIdentifier}>
            {conversation.user_identifier ?? "زائر مجهول"}
          </span>
        </div>
      </div>

      {/* Info grid */}
      <div className={styles.infoGrid}>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>معرف المحادثة</span>
          <code className={styles.infoValue}>{conversation.id}</code>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>تاريخ الإنشاء</span>
          <strong className={styles.infoValue}>{formatDate(conversation.created_at)}</strong>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>عدد الرسائل</span>
          <strong className={styles.infoValue}>{conversation.message_count}</strong>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>رسائل المستخدم</span>
          <strong className={styles.infoValue}>{conversation.user_message_count}</strong>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>ردود الوكيل</span>
          <strong className={styles.infoValue}>{conversation.assistant_message_count}</strong>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>آخر تحديث</span>
          <strong className={styles.infoValue}>{formatDate(conversation.updated_at)}</strong>
        </div>
      </div>

      {/* Message transcript */}
      <div className={styles.transcript} aria-label="سجل الرسائل">
        {messages.length === 0 ? (
          <div className={styles.centerState}>
            <MessageSquareText size={36} aria-hidden="true" />
            <p>لا توجد رسائل في هذه المحادثة</p>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
      </div>
    </>
  );
}

// ─── Root Component ────────────────────────────────────────────────────────────

export default function CustomerConversations() {
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [listRefreshKey, setListRefreshKey] = useState(0);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessageRecord[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [errorMessages, setErrorMessages] = useState<string | null>(null);
  const [messagesRefreshKey, setMessagesRefreshKey] = useState(0);

  const [search, setSearch] = useState("");
  const [agentFilter, setAgentFilter] = useState("all");
  const [showDetail, setShowDetail] = useState(false); // mobile nav state

  // Fetch conversation list
  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    fetch("/api/tenant/conversations?limit=100&offset=0", {
      signal: controller.signal,
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(async (res) => {
        if (ignore) return;
        if (res.status === 401) {
          window.location.assign("/saas/login");
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { items?: ConversationRecord[]; total?: number };
        setConversations(data.items ?? []);
        setTotal(data.total ?? 0);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (ignore) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError("تعذر تحميل المحادثات. حاول مرة أخرى.");
        setLoading(false);
      });

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [listRefreshKey]);

  // Fetch messages when a conversation is selected
  useEffect(() => {
    if (!selectedId) return;

    let ignore = false;
    const controller = new AbortController();

    // Reset state synchronously via the selectConversation handler instead
    fetch(
      `/api/tenant/conversations/${encodeURIComponent(selectedId)}/messages?limit=200&offset=0`,
      {
        signal: controller.signal,
        credentials: "same-origin",
        cache: "no-store",
      },
    )
      .then(async (res) => {
        if (ignore) return;
        if (res.status === 401) {
          window.location.assign("/saas/login");
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { items?: ConversationMessageRecord[] };
        setMessages(data.items ?? []);
        setLoadingMessages(false);
      })
      .catch((err: unknown) => {
        if (ignore) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMessages("تعذر تحميل الرسائل. حاول مرة أخرى.");
        setLoadingMessages(false);
      });

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [selectedId, messagesRefreshKey]);

  // Derived state
  const agentOptions: [string, string][] = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of conversations) {
      map.set(c.agent_id, c.agent_name);
    }
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1], "ar"));
  }, [conversations]);

  const visibleConversations: ConversationRecord[] = useMemo(() => {
    const q = search.trim().toLocaleLowerCase();
    return conversations.filter((c) => {
      const matchesAgent = agentFilter === "all" || c.agent_id === agentFilter;
      if (!matchesAgent) return false;
      if (!q) return true;
      const haystack = [c.id, c.agent_name, c.user_identifier ?? "", c.last_message_preview ?? ""]
        .join(" ")
        .toLocaleLowerCase();
      return haystack.includes(q);
    });
  }, [conversations, search, agentFilter]);

  const selectedConversation: ConversationRecord | undefined = useMemo(
    () => conversations.find((c) => c.id === selectedId),
    [conversations, selectedId],
  );

  // Handlers
  const selectConversation = useCallback(
    (id: string) => {
      if (id === selectedId) return;
      setSelectedId(id);
      setMessages([]);
      setErrorMessages(null);
      setShowDetail(true);
    },
    [selectedId],
  );

  const goBackToList = useCallback(() => {
    setShowDetail(false);
  }, []);

  const retryList = useCallback(() => {
    setListRefreshKey((k) => k + 1);
  }, []);

  const retryMessages = useCallback(() => {
    setMessagesRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className={styles.workspace} dir="rtl">
      {/* List Panel */}
      <div
        className={`${styles.listPanel} ${showDetail ? styles.hiddenOnMobile : ""}`}
      >
        <ConversationListPanel
          conversations={visibleConversations}
          allConversations={conversations}
          total={total}
          selectedId={selectedId}
          loading={loading}
          error={error}
          search={search}
          agentFilter={agentFilter}
          agentOptions={agentOptions}
          onSearchChange={setSearch}
          onAgentFilterChange={setAgentFilter}
          onSelect={selectConversation}
          onRetry={retryList}
        />
      </div>

      {/* Detail Panel */}
      <div
        className={`${styles.detailPanel} ${!showDetail ? styles.hiddenOnMobile : ""}`}
      >
        <ConversationDetailPanel
          conversation={selectedConversation ?? null}
          messages={messages}
          loading={loadingMessages}
          error={errorMessages}
          onRetry={retryMessages}
          onBack={goBackToList}
          isMobile={showDetail}
        />
      </div>
    </div>
  );
}
