import "server-only";

const DEFAULT_LOCAL_API_URL = "http://127.0.0.1:8000";

function normalizeApiBaseUrl(value: string): string {
  const url = new URL(value);

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(
      "API_BASE_URL must use the http or https protocol.",
    );
  }

  if (url.username || url.password) {
    throw new Error(
      "API_BASE_URL must not contain credentials.",
    );
  }

  if (url.search || url.hash) {
    throw new Error(
      "API_BASE_URL must not contain a query string or fragment.",
    );
  }

  url.pathname = url.pathname.replace(/\/+$/, "");

  return url.toString().replace(/\/$/, "");
}

export function getApiBaseUrl(): string {
  const configuredUrl = process.env.API_BASE_URL?.trim();

  if (configuredUrl) {
    return normalizeApiBaseUrl(configuredUrl);
  }

  if (process.env.NODE_ENV !== "production") {
    return DEFAULT_LOCAL_API_URL;
  }

  throw new Error(
    "API_BASE_URL is required in production.",
  );
}

export function shouldUseSecureCookies(): boolean {
  return process.env.NODE_ENV === "production";
}
