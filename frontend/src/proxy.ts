import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  ADMIN_ACCESS_COOKIE,
  ADMIN_REFRESH_COOKIE,
} from "@/lib/auth/session-constants";

export function proxy(
  request: NextRequest,
): NextResponse {
  const hasAccessToken = request.cookies.has(
    ADMIN_ACCESS_COOKIE,
  );

  const hasRefreshToken = request.cookies.has(
    ADMIN_REFRESH_COOKIE,
  );

  if (!hasAccessToken && !hasRefreshToken) {
    const loginUrl = new URL("/", request.url);

    loginUrl.searchParams.set(
      "next",
      `${request.nextUrl.pathname}${request.nextUrl.search}`,
    );

    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
