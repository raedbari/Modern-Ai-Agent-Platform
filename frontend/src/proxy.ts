import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  ADMIN_ACCESS_COOKIE,
  ADMIN_REFRESH_COOKIE,
} from "@/lib/auth/session-constants";
import { TENANT_ACCESS_COOKIE } from "@/lib/auth/tenant-session-constants";

export function proxy(
  request: NextRequest,
): NextResponse {
  const { pathname } = request.nextUrl;

  // Admin route protection (/dashboard/*)
  if (pathname.startsWith("/dashboard")) {
    const hasAccessToken = request.cookies.has(ADMIN_ACCESS_COOKIE);
    const hasRefreshToken = request.cookies.has(ADMIN_REFRESH_COOKIE);

    if (!hasAccessToken && !hasRefreshToken) {
      const loginUrl = new URL("/", request.url);
      loginUrl.searchParams.set(
        "next",
        `${request.nextUrl.pathname}${request.nextUrl.search}`,
      );
      return NextResponse.redirect(loginUrl);
    }
  }

  // Tenant route protection (/app/*)
  if (pathname.startsWith("/app")) {
    const tenantToken = request.cookies.get(TENANT_ACCESS_COOKIE);
    if (!tenantToken) {
      const loginUrl = new URL("/saas/login", request.url);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect /saas/login if tenant already authenticated
  if (pathname === "/saas/login" || pathname.startsWith("/saas/login")) {
    const tenantToken = request.cookies.get(TENANT_ACCESS_COOKIE);
    if (tenantToken) {
      const overviewUrl = new URL("/app/overview", request.url);
      return NextResponse.redirect(overviewUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/app/:path*", "/saas/login"],
};
