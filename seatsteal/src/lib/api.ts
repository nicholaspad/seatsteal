import { config } from "./config";
import { supabase } from "./supabase";
import { toast } from "sonner";

/**
 * Custom error class for server errors that have already shown a toast.
 * Callers can check for this error type to avoid showing duplicate toasts.
 */
export class ServerErrorWithToast extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ServerErrorWithToast";
  }
}

/**
 * Helper function to convert relative API URLs to absolute URLs.
 * - Relative URLs starting with /api/ → prepend base URL
 * - Absolute URLs (http://, https://) → return as-is
 * - Other URLs → return as-is
 */
function resolveApiUrl(url: string): string {
  let resolvedUrl: string;

  // If already absolute, use as-is
  if (url.startsWith("http://") || url.startsWith("https://")) {
    resolvedUrl = url;
  } else if (url.startsWith("/api/")) {
    // If relative API path and a base URL is configured, prepend it.
    // Otherwise rely on same-origin routing (e.g., Vercel middleware/proxy).
    const trimmedBaseUrl = config.api.baseUrl.replace(/\/$/, "");
    resolvedUrl = trimmedBaseUrl ? `${trimmedBaseUrl}${url}` : url;
  } else {
    // Otherwise return as-is
    resolvedUrl = url;
  }

  return resolvedUrl;
}

/**
 * Enhanced fetch wrapper that handles rate limiting (429 responses)
 * and server errors (5xx responses) with automatic toast messages.
 * Throws ServerErrorWithToast for any error to prevent duplicate toasts.
 * Automatically resolves relative /api/ URLs to the configured backend.
 * Automatically adds Authorization header with Supabase access token.
 */
export async function fetchWithToasts(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const resolvedUrl = resolveApiUrl(url);

  // Get auth token from Supabase session
  const {
    data: { session },
  } = await supabase.auth.getSession();

  // Merge headers with auth token
  const headers: HeadersInit = {
    ...options?.headers,
    ...(session?.access_token && {
      Authorization: `Bearer ${session.access_token}`,
    }),
  };

  const response = await fetch(resolvedUrl, {
    ...options,
    headers,
  });

  // Handle rate limiting (429) - return response without throwing
  // This allows calling code to read the detailed error message and show
  // user-friendly messages like "Please try again in 59 seconds"
  if (response.status === 429) {
    return response;
  }

  // Handle server errors (5xx)
  if (response.status >= 500) {
    toast.error("An error has occurred. Please try again later.");
    throw new ServerErrorWithToast("Server error");
  }

  return response;
}

/**
 * @deprecated Use fetchWithToasts instead
 * Legacy function for backwards compatibility
 */
export const fetchWithRateLimit = fetchWithToasts;

/**
 * Alternative fetch wrapper that handles rate limiting silently
 * for cases where you want to handle the error differently.
 * Automatically resolves relative /api/ URLs to the configured backend.
 */
export async function fetchWithRateLimitSilent(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const resolvedUrl = resolveApiUrl(url);
  const response = await fetch(resolvedUrl, options);

  // Handle rate limiting without toast (for custom error handling)
  if (response.status === 429) {
    throw new Error("Rate limited");
  }

  return response;
}

class ApiClient {
  private async getHeaders(): Promise<HeadersInit> {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    return {
      "Content-Type": "application/json",
      ...(session?.access_token && {
        Authorization: `Bearer ${session.access_token}`,
      }),
    };
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(resolveApiUrl(endpoint), {
      method: "GET",
      headers: await this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(resolveApiUrl(endpoint), {
      method: "POST",
      headers: await this.getHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(resolveApiUrl(endpoint), {
      method: "PUT",
      headers: await this.getHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(resolveApiUrl(endpoint), {
      method: "DELETE",
      headers: await this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(resolveApiUrl(endpoint), {
      method: "PATCH",
      headers: await this.getHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }
}

export const api = new ApiClient();
