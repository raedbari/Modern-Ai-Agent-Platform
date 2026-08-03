import "server-only";

import { cookies } from "next/headers";

import {
  AdminApiError,
  getAdminProfile,
  refreshAdminTokens,
  type AdminProfile,
  type LoginResponse,
} from "./admin-api";

import { shouldUseSecureCookies } from "./config";

export const ADMIN_ACCESS_COOKIE =
  "athka_admin_access";

export const ADMIN_REFRESH_COOKIE =
  "athka_admin_refresh";

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

export async function readAdminSessionCookies(): Promise<{
  accessToken: string | null;
  refreshToken: string | null;
}> {
  const cookieStore = await cookies();

  return {
    accessToken:
      cookieStore.get(ADMIN_ACCESS_COOKIE)?.value ?? null,
    refreshToken:
      cookieStore.get(ADMIN_REFRESH_COOKIE)?.value ?? null,
  };
}

export async function writeAdminSessionCookies(
  tokens: LoginResponse,
): Promise<void> {
  const cookieStore = await cookies();

  cookieStore.set(
    ADMIN_ACCESS_COOKIE,
    tokens.access_token,
    cookieOptions(
      Math.max(1, tokens.expires_in),
    ),
  );

  cookieStore.set(
    ADMIN_REFRESH_COOKIE,
    tokens.refresh_token,
    cookieOptions(REFRESH_COOKIE_MAX_AGE),
  );
}

export async function clearAdminSessionCookies(): Promise<void> {
  const cookieStore = await cookies();

  cookieStore.set(
    ADMIN_ACCESS_COOKIE,
    "",
    cookieOptions(0),
  );

  cookieStore.set(
    ADMIN_REFRESH_COOKIE,
    "",
    cookieOptions(0),
  );
}

export async function rotateAdminSession(): Promise<LoginResponse> {
  const {
    refreshToken,
  } = await readAdminSessionCookies();

  if (!refreshToken) {
    throw new AdminApiError(
      401,
      "No active admin session.",
    );
  }

  try {
    const tokens = await refreshAdminTokens(
      refreshToken,
    );

    await writeAdminSessionCookies(tokens);

    return tokens;
  } catch (error) {
    await clearAdminSessionCookies();
    throw error;
  }
}

export async function getCurrentAdminProfile(): Promise<AdminProfile> {
  let {
    accessToken,
    refreshToken,
  } = await readAdminSessionCookies();

  if (!accessToken && !refreshToken) {
    throw new AdminApiError(
      401,
      "No active admin session.",
    );
  }

  if (!accessToken) {
    const tokens = await rotateAdminSession();
    accessToken = tokens.access_token;
    refreshToken = tokens.refresh_token;
  }

  try {
    return await getAdminProfile(accessToken);
  } catch (error) {
    if (
      !(error instanceof AdminApiError) ||
      error.status !== 401 ||
      !refreshToken
    ) {
      if (
        error instanceof AdminApiError &&
        error.status === 401
      ) {
        await clearAdminSessionCookies();
      }

      throw error;
    }
  }

  const tokens = await rotateAdminSession();

  try {
    return await getAdminProfile(
      tokens.access_token,
    );
  } catch (error) {
    await clearAdminSessionCookies();
    throw error;
  }
}
