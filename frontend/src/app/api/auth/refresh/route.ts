import {
  adminApiErrorResponse,
} from "@/lib/server/admin-api";

import {
  rotateAdminSession,
} from "@/lib/server/admin-session";

export async function POST(): Promise<Response> {
  try {
    const tokens = await rotateAdminSession();

    return Response.json(
      {
        admin_id: tokens.admin_id,
        role: tokens.role,
        expires_in: tokens.expires_in,
      },
      {
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
