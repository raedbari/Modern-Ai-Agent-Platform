import {
  saasApiErrorResponse,
  verifyEmail,
} from "@/lib/server/saas-api";

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
        detail: "Token is required.",
      },
      {
        status: 422,
      },
    );
  }

  const { token } = body as Record<string, unknown>;

  if (
    typeof token !== "string" ||
    token.trim().length === 0
  ) {
    return Response.json(
      {
        detail: "Token is required.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    const result = await verifyEmail({
      token: token.trim(),
    });

    return Response.json(
      result,
      {
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  } catch (error) {
    return saasApiErrorResponse(error);
  }
}
