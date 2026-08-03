import {
  AdminApiError,
  adminApiErrorResponse,
  logoutAdmin,
  refreshAdminTokens,
} from "@/lib/server/admin-api";

import {
  clearAdminSessionCookies,
  readAdminSessionCookies,
} from "@/lib/server/admin-session";

export async function POST(): Promise<Response> {
  const {
    accessToken,
    refreshToken,
  } = await readAdminSessionCookies();

  let upstreamError: unknown;

  try {
    if (accessToken && refreshToken) {
      try {
        await logoutAdmin(
          accessToken,
          refreshToken,
        );
      } catch (error) {
        if (
          !(error instanceof AdminApiError) ||
          error.status !== 401
        ) {
          throw error;
        }

        const rotated =
          await refreshAdminTokens(refreshToken);

        await logoutAdmin(
          rotated.access_token,
          rotated.refresh_token,
        );
      }
    } else if (refreshToken) {
      const rotated =
        await refreshAdminTokens(refreshToken);

      await logoutAdmin(
        rotated.access_token,
        rotated.refresh_token,
      );
    }
  } catch (error) {
    if (
      !(
        error instanceof AdminApiError &&
        error.status === 401
      )
    ) {
      upstreamError = error;
    }
  } finally {
    await clearAdminSessionCookies();
  }

  if (upstreamError) {
    return adminApiErrorResponse(upstreamError);
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
