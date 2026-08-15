import {
  adminApiErrorResponse,
} from "@/lib/server/admin-api";

import {
  getCurrentAdminProfile,
} from "@/lib/server/admin-session";

export async function GET(): Promise<Response> {
  try {
    const profile =
      await getCurrentAdminProfile();

    return Response.json(
      profile,
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
