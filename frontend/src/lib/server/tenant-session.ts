import "server-only";

import { cookies } from "next/headers";

import {
  TENANT_ACCESS_COOKIE,
  TENANT_REFRESH_COOKIE,
} from "@/lib/auth/tenant-session-constants";

export {
  TENANT_ACCESS_COOKIE,
  TENANT_REFRESH_COOKIE,
};

import {
  TenantApiError,
  getTenantProfile,
  refreshTenantTokens,
  type TenantProfile,
  type TenantLoginResponse,
} from "./tenant-auth-api";

import { shouldUseSecureCookies } from "./config";

const REFRESH_COOKIE_MAX_AGE =
  7 * 24 * 60 * 60;

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: shouldUseSecureCookies(),
    sameSite: "strict" as const,
    path: "/",
    maxAge,
  };
}

export async function readTenantSessionCookies(): Promise<{
  accessToken: string | null;
  refreshToken: string | null;
}> {
  const cookieStore = await cookies();

  return {
    accessToken:
      cookieStore.get(TENANT_ACCESS_COOKIE)?.value ?? null,
    refreshToken:
      cookieStore.get(TENANT_REFRESH_COOKIE)?.value ?? null,
  };
}

export async function writeTenantSessionCookies(
  tokens: TenantLoginResponse,
): Promise<void> {
  const cookieStore = await cookies();

  cookieStore.set(
    TENANT_ACCESS_COOKIE,
    tokens.access_token,
    cookieOptions(
      Math.max(1, tokens.expires_in),
    ),
  );

  cookieStore.set(
    TENANT_REFRESH_COOKIE,
    tokens.refresh_token,
    cookieOptions(REFRESH_COOKIE_MAX_AGE),
  );
}

export async function clearTenantSessionCookies(): Promise<void> {
  const cookieStore = await cookies();

  cookieStore.set(
    TENANT_ACCESS_COOKIE,
    "",
    cookieOptions(0),
  );

  cookieStore.set(
    TENANT_REFRESH_COOKIE,
    "",
    cookieOptions(0),
  );
}

export async function rotateTenantSession(): Promise<TenantLoginResponse> {
  const {
    refreshToken,
  } = await readTenantSessionCookies();

  if (!refreshToken) {
    throw new TenantApiError(
      401,
      "No active tenant session.",
    );
  }

  try {
    const tokens = await refreshTenantTokens(
      refreshToken,
    );

    await writeTenantSessionCookies(tokens);

    return tokens;
  } catch (error) {
    await clearTenantSessionCookies();
    throw error;
  }
}

export async function withTenantAccessToken<T>(
  operation: (
    accessToken: string,
  ) => Promise<T>,
): Promise<T> {
  let {
    accessToken,
    refreshToken,
  } = await readTenantSessionCookies();

  if (!accessToken && !refreshToken) {
    throw new TenantApiError(
      401,
      "No active tenant session.",
    );
  }

  if (!accessToken) {
    const tokens = await rotateTenantSession();

    accessToken = tokens.access_token;
    refreshToken = tokens.refresh_token;
  }

  try {
    return await operation(accessToken);
  } catch (error) {
    if (
      !(error instanceof TenantApiError) ||
      error.status !== 401 ||
      !refreshToken
    ) {
      if (
        error instanceof TenantApiError &&
        error.status === 401
      ) {
        await clearTenantSessionCookies();
      }

      throw error;
    }
  }

  const tokens = await rotateTenantSession();

  try {
    return await operation(
      tokens.access_token,
    );
  } catch (error) {
    if (
      error instanceof TenantApiError &&
      error.status === 401
    ) {
      await clearTenantSessionCookies();
    }

    throw error;
  }
}

export async function getCurrentTenantProfile(): Promise<TenantProfile> {
  return withTenantAccessToken(
    getTenantProfile,
  );
}
