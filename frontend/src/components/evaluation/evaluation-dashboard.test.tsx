import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvaluationDashboard } from "./evaluation-dashboard";

const builtin = {
  name: "golden-questions",
  owner: "agent-runtime-evaluation",
  domain: "controlled-pilot-rag",
  version: "v1",
  status: "active" as const,
  classification: "synthetic-test-data",
  records: [{
    case_id: "gq-1",
    tenant_id: "source-tenant",
    agent_id: "source-agent",
    user_input: "Question",
    category: "general",
    difficulty: "medium" as const,
    language: "en" as const,
    dialect: null,
    expectations: {
      expected_language: "en" as const,
      required_substrings: [],
      forbidden_substrings: [],
      expected_answer: null,
      expected_facts: [],
      expected_source_ids: [],
      allowed_variations: [],
      forbidden_claims: [],
      answerable: null,
      max_latency_ms: null,
    },
    tags: [],
  }],
};

const uploaded = {
  ...builtin,
  name: "arabic-support",
  owner: "operator",
  domain: "uploaded",
  version: "v2",
  classification: "admin-provided",
  records: [{ ...builtin.records[0], case_id: "uploaded-1", user_input: "مرحبا" }],
};

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFetch(uploadResponse: Response = json(uploaded, 201)) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/evaluation/datasets" && init?.method === "POST") {
      return uploadResponse;
    }
    if (path === "/api/evaluation/datasets") {
      return json([{
        name: builtin.name,
        owner: builtin.owner,
        domain: builtin.domain,
        version: builtin.version,
        status: builtin.status,
        classification: builtin.classification,
        case_count: builtin.records.length,
      }]);
    }
    if (path === "/api/evaluation/runs") return json([]);
    if (path === "/api/agents") {
      return json({
        generated_at: "2026-08-19T00:00:00Z",
        status: "healthy",
        summary: { total: 1, active: 1, inactive: 0, required: 1, preferred: 0, disabled: 0 },
        items: [{
          id: "agent-1",
          tenant_id: "tenant-1",
          tenant_name: "Tenant",
          name: "Agent",
          is_active: true,
          knowledge_mode: "required",
          created_at: "2026-08-19T00:00:00Z",
          updated_at: "2026-08-19T00:00:00Z",
        }],
        warnings: [],
      });
    }
    if (path.includes("arabic-support")) return json(uploaded);
    if (path.includes("golden-questions")) return json(builtin);
    throw new Error(`Unexpected fetch: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Evaluation dataset upload", () => {
  it("uploads a real file and immediately selects the persisted response", async () => {
    const fetchMock = installFetch();
    render(<EvaluationDashboard />);

    const openButton = await screen.findByRole("button", { name: "رفع Dataset" });
    fireEvent.click(openButton);
    fireEvent.change(screen.getByLabelText("اسم Dataset"), { target: { value: "arabic-support" } });
    fireEvent.change(screen.getByLabelText("النسخة"), { target: { value: "v2" } });
    const file = new File([JSON.stringify(uploaded.records)], "cases.json", { type: "application/json" });
    fireEvent.change(screen.getByLabelText("الملف"), { target: { files: [file] } });
    fireEvent.submit(screen.getByRole("button", { name: "رفع واستيراد" }).closest("form")!);

    expect(await screen.findByRole("status")).toHaveTextContent("تم رفع arabic-support · v2 بنجاح");
    expect(screen.getByRole("option", { name: /arabic-support · v2/ })).toBeDefined();

    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(postCall).toBeDefined();
    const body = postCall?.[1]?.body as FormData;
    expect(body.get("name")).toBe("arabic-support");
    expect(body.get("version")).toBe("v2");
    expect(body.get("file")).toBe(file);
  });

  it("shows the backend validation error and does not claim success", async () => {
    installFetch(json({ detail: "Invalid evaluation case at item 1 field 'tenant_id': Field required" }, 422));
    render(<EvaluationDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "رفع Dataset" }));
    fireEvent.change(screen.getByLabelText("اسم Dataset"), { target: { value: "invalid" } });
    fireEvent.change(screen.getByLabelText("النسخة"), { target: { value: "v1" } });
    fireEvent.change(screen.getByLabelText("الملف"), {
      target: { files: [new File(["[]"], "cases.json", { type: "application/json" })] },
    });
    fireEvent.submit(screen.getByRole("button", { name: "رفع واستيراد" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent("tenant_id");
    expect(screen.queryByRole("status")).toBeNull();
  });
});
