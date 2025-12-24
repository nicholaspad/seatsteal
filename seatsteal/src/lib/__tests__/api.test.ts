import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

const mockFetch = vi.fn();
const mockToast = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

const setupConfigMock = (vercelBypassSecret?: string) => {
  vi.doMock("../config", () => ({
    config: {
      api: {
        baseUrl: "https://api.example.com",
        vercelBypassSecret: vercelBypassSecret ?? "",
      },
    },
  }));
};

const setupSupabaseMock = (
  getSessionMock: ReturnType<typeof vi.fn>,
  onAuthStateChangeMock?: ReturnType<typeof vi.fn>,
) => {
  vi.doMock("../supabase", () => ({
    supabase: {
      auth: {
        getSession: getSessionMock,
        onAuthStateChange:
          onAuthStateChangeMock ??
          vi.fn(() => ({
            data: { subscription: { unsubscribe: vi.fn() } },
          })),
      },
    },
  }));
};

beforeEach(() => {
  vi.resetModules();
  mockFetch.mockReset();
  vi.clearAllMocks();
  global.fetch = mockFetch as unknown as typeof fetch;
  setupConfigMock(); // Default config without bypass secret
});

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("fetchWithToasts", () => {
  it("reuses cached tokens across multiple calls", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("/api/test");
    await fetchWithToasts("/api/other");

    expect(getSessionMock).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockFetch.mock.calls[0]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-123",
    });
    expect(mockFetch.mock.calls[1]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-123",
    });
  });

  it("refreshes expired tokens with minimal duplication", async () => {
    vi.useFakeTimers();
    const now = Date.now();
    vi.setSystemTime(now);

    const getSessionMock = vi
      .fn()
      .mockResolvedValueOnce({
        data: {
          session: {
            access_token: "token-old",
            expires_at: Math.floor(now / 1000) + 1,
          },
        },
        error: null,
      })
      .mockResolvedValueOnce({
        data: {
          session: {
            access_token: "token-new",
            expires_at: Math.floor(now / 1000) + 120,
          },
        },
        error: null,
      });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("/api/test");
    vi.advanceTimersByTime(2_000);

    await Promise.all([
      fetchWithToasts("/api/first"),
      fetchWithToasts("/api/second"),
    ]);

    expect(getSessionMock).toHaveBeenCalledTimes(2);
    expect(mockFetch.mock.calls[0]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-old",
    });
    expect(mockFetch.mock.calls[1]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-new",
    });
    expect(mockFetch.mock.calls[2]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-new",
    });
  });

  it("clears cached tokens when the user signs out", async () => {
    const authStateListeners: Array<
      (event: string, session: { access_token?: string | null } | null) => void
    > = [];

    const getSessionMock = vi
      .fn()
      .mockResolvedValueOnce({
        data: {
          session: {
            access_token: "token-abc",
            expires_at: Math.floor(Date.now() / 1000) + 120,
          },
        },
        error: null,
      })
      .mockResolvedValueOnce({
        data: { session: null },
        error: null,
      });

    const onAuthStateChangeMock = vi.fn((callback) => {
      authStateListeners.push(callback);
      return { data: { subscription: { unsubscribe: vi.fn() } } };
    });

    setupSupabaseMock(getSessionMock, onAuthStateChangeMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("/api/with-token");

    authStateListeners.forEach((listener) => listener("SIGNED_OUT", null));

    await fetchWithToasts("/api/after-logout");

    expect(getSessionMock).toHaveBeenCalledTimes(2);
    expect(mockFetch.mock.calls[0]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-abc",
    });
    expect(mockFetch.mock.calls[1]?.[1]?.headers).not.toHaveProperty(
      "Authorization",
    );
  });

  it("handles 500 server errors with toast", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts, ServerErrorWithToast } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 500 }));

    await expect(fetchWithToasts("/api/test")).rejects.toThrow(
      ServerErrorWithToast,
    );
    expect(toast.error).toHaveBeenCalledWith(
      "An error has occurred. Please try again later.",
    );
  });

  it("handles 503 server errors with toast", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 503 }));

    await expect(fetchWithToasts("/api/test")).rejects.toThrow("Server error");
    expect(toast.error).toHaveBeenCalled();
  });

  it("returns 429 response without throwing", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    const rateLimitResponse = new Response(
      JSON.stringify({ error: "Rate limited" }),
      { status: 429 },
    );
    mockFetch.mockResolvedValue(rateLimitResponse);

    const response = await fetchWithToasts("/api/test");

    expect(response.status).toBe(429);
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("resolves relative /api/ URLs to base URL", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("/api/courses");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/api/courses",
      expect.any(Object),
    );
  });

  it("keeps absolute URLs as-is", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("https://external.com/api/data");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://external.com/api/data",
      expect.any(Object),
    );
  });

  it("appends Vercel bypass secret when configured", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupConfigMock("secret-123");
    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("/api/courses");

    const calledUrl = mockFetch.mock.calls[0]?.[0];
    expect(calledUrl).toContain("x-vercel-protection-bypass=secret-123");
  });

  it("handles URLs with existing query params when adding bypass secret", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupConfigMock("secret-456");
    setupSupabaseMock(getSessionMock);
    const { fetchWithToasts } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithToasts("/api/courses?page=1");

    const calledUrl = mockFetch.mock.calls[0]?.[0];
    expect(calledUrl).toContain("page=1");
    expect(calledUrl).toContain("&x-vercel-protection-bypass=secret-456");
  });
});

describe("ServerErrorWithToast", () => {
  it("creates an error with correct name and message", async () => {
    setupSupabaseMock(vi.fn());
    const { ServerErrorWithToast } = await import("../api");

    const error = new ServerErrorWithToast("Test error message");

    expect(error.name).toBe("ServerErrorWithToast");
    expect(error.message).toBe("Test error message");
    expect(error).toBeInstanceOf(Error);
  });

  it("can be caught and identified", async () => {
    setupSupabaseMock(vi.fn());
    const { ServerErrorWithToast } = await import("../api");

    try {
      throw new ServerErrorWithToast("Test");
    } catch (err) {
      expect(err).toBeInstanceOf(ServerErrorWithToast);
      expect((err as ServerErrorWithToast).name).toBe("ServerErrorWithToast");
    }
  });
});

describe("fetchWithRateLimitSilent", () => {
  it("throws error on 429 without toast", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: { session: null },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithRateLimitSilent } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 429 }));

    await expect(fetchWithRateLimitSilent("/api/test")).rejects.toThrow(
      "Rate limited",
    );
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("resolves URLs correctly", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: { session: null },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { fetchWithRateLimitSilent } = await import("../api");

    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithRateLimitSilent("/api/test");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/api/test",
      undefined,
    );
  });
});

describe("ApiClient", () => {
  it("GET request with authorization header", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { api } = await import("../api");

    const mockData = { id: 1, name: "Test" };
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify(mockData), { status: 200 }),
    );

    const result = await api.get("/api/test");

    expect(result).toEqual(mockData);
    expect(mockFetch.mock.calls[0]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer token-123",
      "Content-Type": "application/json",
    });
  });

  it("POST request with data", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-456",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { api } = await import("../api");

    const postData = { name: "New Item" };
    const responseData = { id: 2, ...postData };

    mockFetch.mockResolvedValue(
      new Response(JSON.stringify(responseData), { status: 200 }),
    );

    const result = await api.post("/api/items", postData);

    expect(result).toEqual(responseData);
    expect(mockFetch.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(mockFetch.mock.calls[0]?.[1]?.body).toBe(JSON.stringify(postData));
  });

  it("PUT request with data", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-789",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { api } = await import("../api");

    const putData = { name: "Updated Item" };
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify(putData), { status: 200 }),
    );

    const result = await api.put("/api/items/1", putData);

    expect(result).toEqual(putData);
    expect(mockFetch.mock.calls[0]?.[1]?.method).toBe("PUT");
  });

  it("DELETE request", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-delete",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { api } = await import("../api");

    const deleteResponse = { success: true };
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify(deleteResponse), { status: 200 }),
    );

    const result = await api.delete("/api/items/1");

    expect(result).toEqual(deleteResponse);
    expect(mockFetch.mock.calls[0]?.[1]?.method).toBe("DELETE");
  });

  it("PATCH request with data", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-patch",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { api } = await import("../api");

    const patchData = { status: "active" };
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify(patchData), { status: 200 }),
    );

    const result = await api.patch("/api/items/1", patchData);

    expect(result).toEqual(patchData);
    expect(mockFetch.mock.calls[0]?.[1]?.method).toBe("PATCH");
  });

  it("throws error on non-ok responses", async () => {
    const getSessionMock = vi.fn().mockResolvedValue({
      data: {
        session: {
          access_token: "token-error",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        },
      },
      error: null,
    });

    setupSupabaseMock(getSessionMock);
    const { api } = await import("../api");

    mockFetch.mockResolvedValue(
      new Response(null, { status: 404, statusText: "Not Found" }),
    );

    await expect(api.get("/api/missing")).rejects.toThrow(
      "API Error: Not Found",
    );
  });
});
