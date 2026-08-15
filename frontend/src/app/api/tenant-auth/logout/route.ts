import {
  TenantApiError,
  logoutTenant,
  refreshTenantTokens,
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  clearTenantSessionCookies,
  readTenantSessionCookies,
} from "@/lib/server/tenant-session";

export async function POST(): Promise<Response> {
  const {
    accessToken,
    refreshToken,
  } = await readTenantSessionCookies();

  let upstreamError: unknown;

  try {
    if (accessToken && refreshToken) {
      try {
        await logoutTenant(
          accessToken,
          refreshToken,
        );
      } catch (error) {
        if (
          !(error instanceof TenantApiError) ||
          error.status !== 401
        ) {
          throw error;
        }

        const rotated =
          await refreshTenantTokens(refreshToken);

        await logoutTenant(
          rotated.access_token,
          rotated.refresh_token,
        );
      }
    } else if (refreshToken) {
      const rotated =
        await refreshTenantTokens(refreshToken);

      await logoutTenant(
        rotated.access_token,
        rotated.refresh_token,
      );
    }
  } catch (error) {
    if (
      !(
        error instanceof TenantApiError &&
        error.status === 401
      )
    ) {
      upstreamError = error;
    }
  } finally {
    await clearTenantSessionCookies();
  }

  if (upstreamError) {
    return tenantApiErrorResponse(upstreamError);
  }

  return Response.json(
    {
      detail: "Logged out successfully.",
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
