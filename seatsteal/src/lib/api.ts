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
  // If already absolute, return as-is
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }

  // If relative API path, prepend base URL
  if (url.startsWith("/api/")) {
    return `${config.api.baseUrl}${url}`;
  }

  // Otherwise return as-is
  return url;
}

/**
 * Enhanced fetch wrapper that handles rate limiting (429 responses)
 * and server errors (5xx responses) with automatic toast messages.
 * Throws ServerErrorWithToast for any error to prevent duplicate toasts.
 * Automatically resolves relative /api/ URLs to the configured backend.
 */
export async function fetchWithToasts(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const resolvedUrl = resolveApiUrl(url);
  const response = await fetch(resolvedUrl, options);

  // Handle rate limiting specifically
  if (response.status === 429) {
    toast.error("Too many requests. Try again later.");
    throw new ServerErrorWithToast("Rate limited");
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
  private baseUrl: string;

  constructor() {
    this.baseUrl = config.api.baseUrl;
  }

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
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "GET",
      headers: await this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
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
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
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
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "DELETE",
      headers: await this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
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
