import { z } from "zod";

import {
  saasApiErrorResponse,
  submitSignup,
} from "@/lib/server/saas-api";

const signupSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
  company_name: z.string().min(1),
  password: z.string().min(12),
  plan: z.string().min(1),
  legal_accepted: z.literal(true),
});

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

  const parsed = signupSchema.safeParse(body);

  if (!parsed.success) {
    return Response.json(
      {
        detail: parsed.error.flatten().fieldErrors,
      },
      {
        status: 422,
      },
    );
  }

  try {
    const result = await submitSignup({
      name: parsed.data.name,
      email: parsed.data.email,
      company_name: parsed.data.company_name,
      password: parsed.data.password,
      requested_plan: parsed.data.plan,
      legal_accepted: parsed.data.legal_accepted,
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
