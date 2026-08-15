"use client";

import type {
  PropsWithChildren,
} from "react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import Link from "next/link";
import {
  usePathname,
  useRouter,
} from "next/navigation";
import type {
  LucideIcon,
} from "lucide-react";
import {
  Bell,
  Bot,
  BookOpenCheck,
  ChevronLeft,
  CircleAlert,
  ClipboardList,
  Database,
  KeyRound,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquareText,
  RefreshCw,
  ScrollText,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  UsersRound,
  X,
} from "lucide-react";

import type {
  components,
} from "@/lib/api/generated/admin-api";

import { AthkaLogo } from "@/components/brand/athka-logo";

type AdminProfile =
  components["schemas"]["AdminProfileResponse"];

type SessionStatus =
  | "loading"
  | "ready"
  | "error";

type NavigationItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

const copy = {
  overview:
    "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629",
  tenants:
    "\u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  agents:
    "\u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  knowledgeBases:
    "\u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0645\u0639\u0631\u0641\u0629",
  conversations:
    "\u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0627\u062a",
  widgetSettings:
    "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a",
  apiKeys:
    "\u0645\u0641\u0627\u062a\u064a\u062d API",
  adminUsers:
    "\u0645\u0633\u0624\u0648\u0644\u0648 \u0627\u0644\u0645\u0646\u0635\u0629",
  auditLogs:
    "\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u062a\u062f\u0642\u064a\u0642",
  settings:
    "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645",
  platform:
    "\u0627\u0644\u0645\u0646\u0635\u0629",
  administration:
    "\u0627\u0644\u0625\u062f\u0627\u0631\u0629 \u0648\u0627\u0644\u0623\u0645\u0627\u0646",
  openMenu:
    "\u0641\u062a\u062d \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062a\u0646\u0642\u0644",
  closeMenu:
    "\u0625\u063a\u0644\u0627\u0642 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062a\u0646\u0642\u0644",
  notifications:
    "\u0627\u0644\u0625\u0634\u0639\u0627\u0631\u0627\u062a",
  secureSession:
    "\u062c\u0644\u0633\u0629 \u0625\u062f\u0627\u0631\u064a\u0629 \u0622\u0645\u0646\u0629",
  logout:
    "\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062e\u0631\u0648\u062c",
  loggingOut:
    "\u062c\u0627\u0631\u064a \u0627\u0644\u062e\u0631\u0648\u062c",
  logoutFailed:
    "\u062a\u0639\u0630\u0631 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062e\u0631\u0648\u062c. \u062d\u0627\u0648\u0644 \u0645\u062c\u062f\u062f\u064b\u0627.",
  loadingSession:
    "\u062c\u0627\u0631\u064a \u062a\u062d\u0642\u0642 \u0627\u0644\u062c\u0644\u0633\u0629",
  loadingDescription:
    "\u0646\u062a\u062d\u0642\u0642 \u0645\u0646 \u0635\u0644\u0627\u062d\u064a\u0627\u062a\u0643 \u0648\u0646\u062c\u0647\u0632 \u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u0639\u0645\u0644.",
  sessionError:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u062c\u0644\u0633\u0629",
  sessionErrorDescription:
    "\u0644\u0645 \u0646\u062a\u0645\u0643\u0646 \u0645\u0646 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u062e\u062f\u0645\u0629 \u0627\u0644\u0645\u0635\u0627\u062f\u0642\u0629.",
  retry:
    "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629",
  superAdmin:
    "\u0645\u0633\u0624\u0648\u0644 \u0623\u0639\u0644\u0649",
  admin:
    "\u0645\u0633\u0624\u0648\u0644",
  currentSection:
    "\u0627\u0644\u0642\u0633\u0645 \u0627\u0644\u062d\u0627\u0644\u064a",
  workspace:
    "\u0645\u0633\u0627\u062d\u0629 Athkachatbots",
} as const;

const platformNavigation: NavigationItem[] = [
  {
    label: copy.overview,
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: copy.tenants,
    href: "/dashboard/tenants",
    icon: UsersRound,
  },
  {
    label: "طلبات الاشتراك",
    href: "/dashboard/applications",
    icon: ClipboardList,
  },
  {
    label: copy.agents,
    href: "/dashboard/agents",
    icon: Bot,
  },
  {
    label: copy.knowledgeBases,
    href: "/dashboard/knowledge-bases",
    icon: BookOpenCheck,
  },
  {
    label: copy.conversations,
    href: "/dashboard/conversations",
    icon: MessageSquareText,
  },
  {
    label: copy.widgetSettings,
    href: "/dashboard/widget-settings",
    icon: SlidersHorizontal,
  },
  {
    label: copy.apiKeys,
    href: "/dashboard/api-keys",
    icon: KeyRound,
  },
];

const administrationNavigation: NavigationItem[] = [
  {
    label: copy.adminUsers,
    href: "/dashboard/admin-users",
    icon: ShieldCheck,
  },
  {
    label: copy.auditLogs,
    href: "/dashboard/audit-logs",
    icon: ScrollText,
  },
  {
    label: copy.settings,
    href: "/dashboard/system-settings",
    icon: Settings,
  },
];

function isNavigationItemActive(
  pathname: string,
  href: string,
): boolean {
  if (href === "/dashboard") {
    return pathname === href;
  }

  return (
    pathname === href ||
    pathname.startsWith(`${href}/`)
  );
}

function resolveRoleLabel(
  role: string,
): string {
  if (role === "super_admin") {
    return copy.superAdmin;
  }

  if (role === "admin") {
    return copy.admin;
  }

  return role.replaceAll("_", " ");
}

function NavigationGroup({
  title,
  items,
  pathname,
  onNavigate,
}: {
  title: string;
  items: NavigationItem[];
  pathname: string;
  onNavigate: () => void;
}) {
  return (
    <div className="admin-navigation__group">
      <p>{title}</p>

      <nav aria-label={title}>
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            isNavigationItemActive(
              pathname,
              item.href,
            );

          return (
            <Link
              key={item.href}
              className={
                active
                  ? "admin-navigation__item is-active"
                  : "admin-navigation__item"
              }
              href={item.href}
              aria-current={
                active
                  ? "page"
                  : undefined
              }
              onClick={onNavigate}
            >
              <Icon aria-hidden="true" />
              <span>{item.label}</span>
              <ChevronLeft
                className="admin-navigation__chevron"
                aria-hidden="true"
              />
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function SessionLoading() {
  return (
    <main className="admin-session-state">
      <div className="admin-session-state__card">
        <div className="admin-session-state__icon">
          <LoaderCircle
            className="admin-session-state__spinner"
            aria-hidden="true"
          />
        </div>

        <h1>{copy.loadingSession}</h1>
        <p>{copy.loadingDescription}</p>
      </div>
    </main>
  );
}

function SessionError({
  onRetry,
}: {
  onRetry: () => void;
}) {
  return (
    <main className="admin-session-state">
      <div className="admin-session-state__card">
        <div className="admin-session-state__icon is-error">
          <CircleAlert aria-hidden="true" />
        </div>

        <h1>{copy.sessionError}</h1>
        <p>{copy.sessionErrorDescription}</p>

        <button
          type="button"
          onClick={onRetry}
        >
          <RefreshCw aria-hidden="true" />
          {copy.retry}
        </button>
      </div>
    </main>
  );
}

export function DashboardShell({
  children,
}: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();

  const [profile, setProfile] =
    useState<AdminProfile | null>(null);
  const [status, setStatus] =
    useState<SessionStatus>("loading");
  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);
  const [loggingOut, setLoggingOut] =
    useState(false);
  const [logoutError, setLogoutError] =
    useState<string | null>(null);

  const currentSection = useMemo(() => {
    const items = [
      ...platformNavigation,
      ...administrationNavigation,
    ];

    return (
      items.find((item) =>
        isNavigationItemActive(
          pathname,
          item.href,
        ),
      )?.label ?? copy.overview
    );
  }, [pathname]);

  const fetchSession = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<AdminProfile | null> => {
      const response = await fetch(
        "/api/auth/session",
        {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
          signal,
        },
      );

      if (response.status === 401) {
        router.replace("/");
        router.refresh();

        return null;
      }

      if (!response.ok) {
        throw new Error(
          `Session request failed: ${response.status}`,
        );
      }

      return await response.json() as AdminProfile;
    },
    [router],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    void fetchSession(controller.signal)
      .then((sessionProfile) => {
        if (
          sessionProfile === null ||
          controller.signal.aborted
        ) {
          return;
        }

        setProfile(sessionProfile);
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        if (
          error instanceof DOMException &&
          error.name === "AbortError"
        ) {
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
      const sessionProfile =
        await fetchSession();

      if (sessionProfile === null) {
        return;
      }

      setProfile(sessionProfile);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }

  useEffect(() => {
    if (!mobileMenuOpen) {
      return;
    }

    const previousOverflow =
      document.body.style.overflow;

    document.body.style.overflow = "hidden";

    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (event.key === "Escape") {
        setMobileMenuOpen(false);
      }
    }

    window.addEventListener(
      "keydown",
      handleKeyDown,
    );

    return () => {
      document.body.style.overflow =
        previousOverflow;

      window.removeEventListener(
        "keydown",
        handleKeyDown,
      );
    };
  }, [mobileMenuOpen]);

  async function handleLogout() {
    setLoggingOut(true);
    setLogoutError(null);

    try {
      const response = await fetch(
        "/api/auth/logout",
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (!response.ok) {
        throw new Error(
          `Logout failed: ${response.status}`,
        );
      }

      router.replace("/");
      router.refresh();
    } catch {
      setLogoutError(copy.logoutFailed);
      setLoggingOut(false);
    }
  }

  if (status === "loading") {
    return <SessionLoading />;
  }

  if (
    status === "error" ||
    profile === null
  ) {
    return (
      <SessionError
        onRetry={() => {
          void handleRetry();
        }}
      />
    );
  }

  const initials = profile.username
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="admin-shell">
      <button
        className={
          mobileMenuOpen
            ? "admin-shell__overlay is-visible"
            : "admin-shell__overlay"
        }
        type="button"
        aria-label={copy.closeMenu}
        tabIndex={
          mobileMenuOpen
            ? 0
            : -1
        }
        onClick={() => {
          setMobileMenuOpen(false);
        }}
      />

      <aside
        className={
          mobileMenuOpen
            ? "admin-sidebar is-open"
            : "admin-sidebar"
        }
      >
        <div className="admin-sidebar__header">
          <AthkaLogo />

          <button
            className="admin-sidebar__close"
            type="button"
            aria-label={copy.closeMenu}
            onClick={() => {
              setMobileMenuOpen(false);
            }}
          >
            <X aria-hidden="true" />
          </button>
        </div>

        <div className="admin-sidebar__workspace">
          <Database aria-hidden="true" />

          <div>
            <strong>{copy.workspace}</strong>
            <span>{copy.secureSession}</span>
          </div>
        </div>

        <div className="admin-navigation">
          <NavigationGroup
            title={copy.platform}
            items={platformNavigation}
            pathname={pathname}
            onNavigate={() => {
              setMobileMenuOpen(false);
            }}
          />

          <NavigationGroup
            title={copy.administration}
            items={administrationNavigation}
            pathname={pathname}
            onNavigate={() => {
              setMobileMenuOpen(false);
            }}
          />
        </div>

        <div className="admin-sidebar__footer">
          <div className="admin-profile-card">
            <span className="admin-profile-card__avatar">
              {initials}
            </span>

            <div>
              <strong>{profile.username}</strong>
              <span>
                {resolveRoleLabel(profile.role)}
              </span>
            </div>

            <ShieldCheck
              className="admin-profile-card__verified"
              aria-hidden="true"
            />
          </div>

          {logoutError && (
            <p
              className="admin-sidebar__logout-error"
              role="alert"
            >
              {logoutError}
            </p>
          )}

          <button
            className="admin-sidebar__logout"
            type="button"
            disabled={loggingOut}
            onClick={() => {
              void handleLogout();
            }}
          >
            {loggingOut ? (
              <LoaderCircle
                className="admin-session-state__spinner"
                aria-hidden="true"
              />
            ) : (
              <LogOut aria-hidden="true" />
            )}

            <span>
              {loggingOut
                ? copy.loggingOut
                : copy.logout}
            </span>
          </button>
        </div>
      </aside>

      <div className="admin-main">
        <header className="admin-topbar">
          <div className="admin-topbar__heading">
            <button
              className="admin-topbar__menu"
              type="button"
              aria-label={copy.openMenu}
              aria-expanded={mobileMenuOpen}
              onClick={() => {
                setMobileMenuOpen(true);
              }}
            >
              <Menu aria-hidden="true" />
            </button>

            <div>
              <span>{copy.currentSection}</span>
              <h1>{currentSection}</h1>
            </div>
          </div>

          <div className="admin-topbar__actions">
            <button
              className="admin-topbar__notification"
              type="button"
              aria-label={copy.notifications}
            >
              <Bell aria-hidden="true" />
              <span aria-hidden="true" />
            </button>

            <div className="admin-topbar__profile">
              <span className="admin-topbar__avatar">
                {initials}
              </span>

              <div>
                <strong>{profile.username}</strong>
                <span>
                  {resolveRoleLabel(profile.role)}
                </span>
              </div>
            </div>
          </div>
        </header>

        <div className="admin-content">
          {children}
        </div>
      </div>
    </div>
  );
}
