import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockFetch = vi.fn();

const setupSupabaseMock = (
  getSessionMock: ReturnType<typeof vi.fn>,
) => {
  vi.doMock("../supabase", () => ({
    supabase: {
      auth: {
        getSession: getSessionMock,
      },
    },
  }));
};

beforeEach(() => {
  vi.resetModules();
  mockFetch.mockReset();
  global.fetch = mockFetch as unknown as typeof fetch;
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
});
