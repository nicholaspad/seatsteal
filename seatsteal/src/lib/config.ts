/**
 * Get the API base URL, automatically detecting Vercel preview deployments.
 * Defaults to same-origin /api routes so middleware/proxy layers can handle
 * environment-specific routing and protection.
 */
const getApiBaseUrl = (): string => {
  return import.meta.env.VITE_API_BASE_URL || "";
};

/**
 * Get the terminal server WebSocket URL.
 * Terminal requires a dedicated server with WebSocket support (not available on Vercel).
 * Falls back to the main API URL for local development.
 */
const getTerminalServerUrl = (): string | undefined => {
  return import.meta.env.VITE_TERMINAL_SERVER_URL || undefined;
};

export const config = {
  supabase: {
    url: import.meta.env.VITE_SUPABASE_URL || "",
    anonKey: import.meta.env.VITE_SUPABASE_ANON_KEY || "",
  },
  api: {
    baseUrl: getApiBaseUrl(),
  },
  terminal: {
    /** Dedicated terminal server URL (WebSocket-enabled) */
    serverUrl: getTerminalServerUrl(),
  },
} as const;
