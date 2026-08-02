/**
 * Widget API Client
 * BROWSER-SAFE
 */

export const WIDGET_API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const WidgetPaths = {
  "/api/chat": "/api/chat",
  "/api/widget/bootstrap": "/api/widget/bootstrap",
  "/health": "/health",
} as const;
