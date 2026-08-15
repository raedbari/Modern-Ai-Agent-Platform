import {
  adminApiErrorResponse,
  loginAdmin,
  type LoginRequest,
} from "@/lib/server/admin-api";

import {
  writeAdminSessionCookies,
} from "@/lib/server/admin-session";

export async function POST(
  request: Request,
): Promise<Response> {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return Response.json(
      {
        detail: "Request body must be valid JSON.",
      },
      {
        status: 400,
      },
    );
  }

  if (
    body === null ||
    typeof body !== "object"
  ) {
    return Response.json(
      {
        detail: "Username and password are required.",
      },
      {
        status: 422,
      },
    );
  }

  const {
    username,
    password,
  } = body as Partial<LoginRequest>;

  if (
    typeof username !== "string" ||
    username.trim().length === 0 ||
    typeof password !== "string" ||
    password.length === 0
  ) {
    return Response.json(
      {
        detail: "Username and password are required.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    const tokens = await loginAdmin({
      username: username.trim(),
      password,
    });

    await writeAdminSessionCookies(tokens);

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
