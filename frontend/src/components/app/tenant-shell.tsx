"use client";

import type { PropsWithChildren } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  Bell,
  BookOpenCheck,
  Bot,
  Building2,
  ChevronLeft,
  CircleAlert,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquareText,
  RefreshCw,
  User,
  UsersRound,
  X,
} from "lucide-react";

import { AthkaLogo } from "@/components/brand/athka-logo";
import type { TenantProfile } from "@/lib/server/tenant-auth-api";

type SessionStatus = "loading" | "ready" | "error";

type NavigationItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

const copy = {
  overview: "نظرة عامة",
  chatbots: "الوكلاء الذكية",
  knowledge: "قواعد المعرفة",
  conversations: "المحادثات",
  team: "فريق العمل",
  account: "الحساب والإعدادات",
  logout: "تسجيل الخروج",
  loggingOut: "جاري الخروج…",
  logoutFailed: "تعذر تسجيل الخروج. حاول مجددًا.",
  loadingSession: "جاري التحقق من الجلسة",
  loadingDescription: "نتحقق من بيانات الحساب وحالة الاشتراك…",
  sessionError: "تعذر تحميل الجلسة",
  sessionErrorDescription: "لم نتمكن من الاتصال بخدمة التحقق.",
  retry: "إعادة المحاولة",
  tenantWorkspace: "مساحة العميل",
  openMenu: "فتح القائمة",
  closeMenu: "إغلاق القائمة",
} as const;

const tenantNavigation: NavigationItem[] = [
  {
    label: copy.overview,
    href: "/app/overview",
    icon: LayoutDashboard,
  },
  {
    label: copy.chatbots,
    href: "/app/chatbots",
    icon: Bot,
  },
  {
    label: copy.knowledge,
    href: "/app/knowledge",
    icon: BookOpenCheck,
  },
  {
    label: copy.conversations,
    href: "/app/conversations",
    icon: MessageSquareText,
  },
  {
    label: copy.team,
    href: "/app/team",
    icon: UsersRound,
  },
  {
    label: copy.account,
    href: "/app/account",
    icon: User,
  },
];

function isNavigationItemActive(pathname: string, href: string): boolean {
  if (href === "/app/overview") {
    return pathname === href || pathname === "/app";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function SessionLoading() {
  return (
    <main className="tenant-session-state">
      <div className="tenant-session-state__card">
        <div className="tenant-session-state__icon">
          <LoaderCircle
            className="tenant-session-state__spinner"
            aria-hidden="true"
          />
        </div>
        <h1>{copy.loadingSession}</h1>
        <p>{copy.loadingDescription}</p>
      </div>
    </main>
  );
}

function SessionError({ onRetry }: { onRetry: () => void }) {
  return (
    <main className="tenant-session-state">
      <div className="tenant-session-state__card">
        <div className="tenant-session-state__icon is-error">
          <CircleAlert aria-hidden="true" />
        </div>
        <h1>{copy.sessionError}</h1>
        <p>{copy.sessionErrorDescription}</p>
        <button type="button" onClick={onRetry}>
          <RefreshCw aria-hidden="true" />
          {copy.retry}
        </button>
      </div>
    </main>
  );
}

export function TenantShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();

  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  const currentSection = useMemo(() => {
    return (
      tenantNavigation.find((item) =>
        isNavigationItemActive(pathname, item.href)
      )?.label ?? copy.overview
    );
  }, [pathname]);

  const fetchSession = useCallback(
    async (signal?: AbortSignal): Promise<TenantProfile | null> => {
      const response = await fetch("/api/tenant-auth/session", {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          Accept: "application/json",
        },
        signal,
      });

      if (response.status === 401) {
        router.replace("/saas/login");
        router.refresh();
        return null;
      }

      if (!response.ok) {
        throw new Error(`Session request failed: ${response.status}`);
      }

      const data = (await response.json()) as TenantProfile;

      if (
        data.application_status !== "approved" ||
        !data.tenant_id
      ) {
        router.replace("/saas/application-status");
        router.refresh();
        return null;
      }

      return data;
    },
    [router]
  );

  useEffect(() => {
    const controller = new AbortController();

    void fetchSession(controller.signal)
      .then((sessionProfile) => {
        if (sessionProfile === null || controller.signal.aborted) {
          return;
        }
        setProfile(sessionProfile);
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setStatus("error");
      });

    return () => {
      controller.abort();
    };
  }, [fetchSession]);

  async function handleRetry(): Promise<void> {
    setStatus("loading");
    try {
      const sessionProfile = await fetchSession();
      if (sessionProfile === null) return;
      setProfile(sessionProfile);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileMenuOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileMenuOpen]);

  async function handleLogout() {
    setLoggingOut(true);
    setLogoutError(null);

    try {
      const response = await fetch("/api/tenant-auth/logout", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Logout failed: ${response.status}`);
      }

      router.replace("/saas/login");
      router.refresh();
    } catch {
      setLogoutError(copy.logoutFailed);
      setLoggingOut(false);
    }
  }

  if (status === "loading") {
    return <SessionLoading />;
  }

  if (status === "error" || profile === null) {
    return (
      <SessionError
        onRetry={() => {
          void handleRetry();
        }}
      />
    );
  }

  const companyInitial = profile.company_name
    ? profile.company_name.slice(0, 2).toUpperCase()
    : "AT";

  return (
    <div className="tenant-shell" dir="rtl">
      <button
        className={
          mobileMenuOpen
            ? "tenant-shell__overlay is-visible"
            : "tenant-shell__overlay"
        }
        type="button"
        aria-label={copy.closeMenu}
        tabIndex={mobileMenuOpen ? 0 : -1}
        onClick={() => setMobileMenuOpen(false)}
      />

      <aside
        className={
          mobileMenuOpen ? "tenant-sidebar is-open" : "tenant-sidebar"
        }
      >
        <div className="tenant-sidebar__header">
          <AthkaLogo />
          <button
            className="tenant-sidebar__close"
            type="button"
            aria-label={copy.closeMenu}
            onClick={() => setMobileMenuOpen(false)}
          >
            <X aria-hidden="true" />
          </button>
        </div>

        <div className="tenant-sidebar__workspace">
          <Building2 aria-hidden="true" />
          <div>
            <strong>{profile.company_name || copy.tenantWorkspace}</strong>
            <span>{profile.email}</span>
          </div>
        </div>

        <nav className="tenant-navigation" aria-label="تنقل البوابة">
          {tenantNavigation.map((item) => {
            const Icon = item.icon;
            const active = isNavigationItemActive(pathname, item.href);

            return (
              <Link
                key={item.href}
                className={
                  active
                    ? "tenant-navigation__item is-active"
                    : "tenant-navigation__item"
                }
                href={item.href}
                aria-current={active ? "page" : undefined}
                onClick={() => setMobileMenuOpen(false)}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
                <ChevronLeft
                  className="tenant-navigation__chevron"
                  aria-hidden="true"
                />
              </Link>
            );
          })}
        </nav>

        <div className="tenant-sidebar__footer">
          {logoutError && (
            <p className="tenant-sidebar__logout-error" role="alert">
              {logoutError}
            </p>
          )}

          <button
            className="tenant-sidebar__logout"
            type="button"
            disabled={loggingOut}
            onClick={() => {
              void handleLogout();
            }}
          >
            {loggingOut ? (
              <LoaderCircle
                className="tenant-session-state__spinner"
                aria-hidden="true"
              />
            ) : (
              <LogOut aria-hidden="true" />
            )}
            <span>{loggingOut ? copy.loggingOut : copy.logout}</span>
          </button>
        </div>
      </aside>

      <div className="tenant-main">
        <header className="tenant-topbar">
          <div className="tenant-topbar__heading">
            <button
              className="tenant-topbar__menu"
              type="button"
              aria-label={copy.openMenu}
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu aria-hidden="true" />
            </button>
            <div>
              <span>بوابة العميل</span>
              <h1>{currentSection}</h1>
            </div>
          </div>

          <div className="tenant-topbar__actions">
            <button
              className="tenant-topbar__notification"
              type="button"
              aria-label="الإشعارات"
            >
              <Bell aria-hidden="true" />
            </button>

            <div className="tenant-topbar__profile">
              <span className="tenant-topbar__avatar">{companyInitial}</span>
              <div>
                <strong>{profile.company_name}</strong>
                <span>{profile.email}</span>
              </div>
            </div>
          </div>
        </header>

        <div className="tenant-content">{children}</div>
      </div>
    </div>
  );
}
