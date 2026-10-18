import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AuthCallback from "../AuthCallback";

// Mock modules
const mockHistoryReplace = vi.fn();
const mockFetchWithToasts = vi.fn();
const mockLogError = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockRefreshSubscriptionTier = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return {
    ...actual,
    useHistory: () => ({
      replace: mockHistoryReplace,
      push: vi.fn(),
    }),
  };
});

vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

vi.mock("@/lib/logger", () => ({
  logError: (...args: unknown[]) => mockLogError(...args),
}));

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

// Mock Supabase
const mockGetSession = vi.fn();
const mockGetUser = vi.fn();

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      getUser: () => mockGetUser(),
    },
  },
}));

vi.mock("@/components/providers/SessionProvider", () => ({
  useSession: () => ({
    refreshSubscriptionTier: mockRefreshSubscriptionTier,
    user: null,
    profile: null,
    loading: false,
    profileLoading: false,
    subscriptionTier: "free",
    tierLoading: false,
    subscriptionStatus: null,
    subscriptionStatusLoading: false,
    refreshSubscriptionStatus: vi.fn(),
  }),
}));

describe("AuthCallback Page", () => {
  // Helper to create mock session/user responses
  const mockSession = {
    access_token: "test-token",
    refresh_token: "test-refresh",
    user: {
      id: "test-user-id",
      email: "test@example.edu",
    },
  };

  const mockUser = {
    id: "test-user-id",
    email: "test@example.edu",
    user_metadata: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();

    // Default mock implementations
    mockGetSession.mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });

    mockGetUser.mockResolvedValue({
      data: { user: mockUser },
      error: null,
    });
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe("Referral Code Handling", () => {
    it("does not call /api/referrals/apply when no referral code in localStorage", async () => {
      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockHistoryReplace).toHaveBeenCalled();
      });

      // Verify referrals API was NOT called
      expect(mockFetchWithToasts).not.toHaveBeenCalledWith(
        expect.stringContaining("/api/referrals/apply"),
        expect.any(Object),
      );

      // Should still redirect successfully
      expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");
    });

    it("calls /api/referrals/apply with correct payload when referral code exists", async () => {
      // Set referral code in localStorage
      localStorage.setItem("referral_code", "TESTCODE");

      // Mock successful API response
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            data: { message: "Referral applied successfully" },
          }),
      } as Response);

      // Mock successful tier refresh
      mockRefreshSubscriptionTier.mockResolvedValue(undefined);

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockFetchWithToasts).toHaveBeenCalledWith(
          "/api/referrals/apply",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ referral_code: "TESTCODE" }),
          },
        );
      });

      // Should show success toast
      expect(mockToastSuccess).toHaveBeenCalledWith(
        expect.stringContaining("Your referral has been applied"),
      );

      // Should refresh subscription tier after successful referral
      expect(mockRefreshSubscriptionTier).toHaveBeenCalled();

      // Should remove referral code from localStorage
      expect(localStorage.getItem("referral_code")).toBeNull();

      // Should still redirect to dashboard
      expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");
    });

    it("continues auth flow and keeps localStorage when referral API throws", async () => {
      // Set referral code in localStorage
      localStorage.setItem("referral_code", "TESTCODE");

      // Mock API failure
      mockFetchWithToasts.mockRejectedValue(new Error("API Error"));

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockHistoryReplace).toHaveBeenCalled();
      });

      // Should log error
      expect(mockLogError).toHaveBeenCalledWith(
        "Failed to apply referral code",
        expect.any(Error),
      );

      // Should NOT show success toast
      expect(mockToastSuccess).not.toHaveBeenCalled();

      // Transient errors keep the code so we can retry
      expect(localStorage.getItem("referral_code")).toBe("TESTCODE");

      // Should still redirect successfully (non-blocking)
      expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");
    });

    it("cleans up localStorage on successful referral application", async () => {
      localStorage.setItem("referral_code", "TESTCODE");

      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      } as Response);

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(localStorage.getItem("referral_code")).toBeNull();
      });
    });

    it("cleans up localStorage on terminal 400 referral errors", async () => {
      localStorage.setItem("referral_code", "TESTCODE");

      mockFetchWithToasts.mockResolvedValue({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            detail: "You have already claimed a referral code",
          }),
      } as Response);

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(localStorage.getItem("referral_code")).toBeNull();
      });
      expect(mockToastError).toHaveBeenCalledWith(
        "You have already claimed a referral code",
      );
    });

    it("keeps the referral code on past_due 409, opens the billing portal from Update card, and retries quietly in the same session", async () => {
      localStorage.setItem("referral_code", "TESTCODE");

      const portalUrl = "https://billing.stripe.com/session/test";
      mockFetchWithToasts.mockImplementation((url: unknown) => {
        if (url === "/api/referrals/apply") {
          return Promise.resolve({
            ok: false,
            status: 409,
            json: () =>
              Promise.resolve({
                detail: "Update your card to claim your free Pro week.",
              }),
          } as Response);
        }
        if (url === "/api/stripe/create-portal-session") {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: { sessionUrl: portalUrl },
              }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as Response);
      });

      const locationStub = { href: "http://localhost/", search: "" };
      const originalLocation = window.location;
      Object.defineProperty(window, "location", {
        configurable: true,
        value: locationStub,
      });

      const { unmount } = render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalled();
      });

      expect(mockToastError).toHaveBeenCalledTimes(1);
      expect(mockToastError).toHaveBeenCalledWith(
        "Update your card to claim your free Pro week.",
        expect.objectContaining({
          action: expect.objectContaining({
            label: "Update card",
          }),
        }),
      );
      const toastAction = mockToastError.mock.calls[0]?.[1] as {
        action: { label: string; onClick: () => void };
      };
      expect(localStorage.getItem("referral_code")).toBe("TESTCODE");
      expect(sessionStorage.getItem("referral_past_due_toast_shown")).toBe("1");
      expect(mockToastSuccess).not.toHaveBeenCalled();
      expect(mockLogError).not.toHaveBeenCalledWith(
        "Failed to apply referral code",
        expect.anything(),
      );
      expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");

      await toastAction.action.onClick();
      await waitFor(() => {
        expect(mockFetchWithToasts).toHaveBeenCalledWith(
          "/api/stripe/create-portal-session",
          expect.objectContaining({ method: "POST" }),
        );
      });
      expect(locationStub.href).toBe(portalUrl);

      mockToastError.mockClear();
      mockHistoryReplace.mockClear();
      unmount();

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");
      });

      const applyCalls = mockFetchWithToasts.mock.calls.filter(
        (call) => call[0] === "/api/referrals/apply",
      );
      expect(applyCalls.length).toBeGreaterThanOrEqual(2);
      expect(mockToastError).not.toHaveBeenCalled();
      expect(localStorage.getItem("referral_code")).toBe("TESTCODE");

      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    });
  });

  describe("Redirect Behavior", () => {
    it("redirects to /admin when admin query param is true", async () => {
      // Mock URL with admin=true query parameter
      Object.defineProperty(window, "location", {
        value: {
          ...window.location,
          search: "?admin=true",
        },
        writable: true,
      });

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockHistoryReplace).toHaveBeenCalledWith("/admin");
      });
    });

    it("redirects to /dashboard by default when no admin param", async () => {
      Object.defineProperty(window, "location", {
        value: {
          ...window.location,
          search: "",
        },
        writable: true,
      });

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");
      });
    });
  });

  describe("Error Handling", () => {
    it("displays error when session retrieval fails", async () => {
      mockGetSession.mockResolvedValue({
        data: { session: null },
        error: new Error("Session error"),
      });

      const { getByText } = render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(getByText(/Session error/i)).toBeInTheDocument();
      });

      expect(mockHistoryReplace).not.toHaveBeenCalled();
    });

    it("displays error when no session is found", async () => {
      mockGetSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });

      const { getByText } = render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          getByText(/No authentication session found/i),
        ).toBeInTheDocument();
      });

      expect(mockHistoryReplace).not.toHaveBeenCalled();
    });

    it("displays error when user retrieval fails", async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      });

      const { getByText } = render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          getByText(/Failed to get user information/i),
        ).toBeInTheDocument();
      });

      expect(mockHistoryReplace).not.toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("displays loading spinner while processing", () => {
      const { getByText } = render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      expect(getByText("Signing you in...")).toBeInTheDocument();
    });
  });
});
