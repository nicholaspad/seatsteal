import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AuthCallback from "../AuthCallback";

// Mock modules
const mockHistoryReplace = vi.fn();
const mockFetchWithToasts = vi.fn();
const mockLogError = vi.fn();
const mockToastSuccess = vi.fn();

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
    error: vi.fn(),
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

      // Should remove referral code from localStorage
      expect(localStorage.getItem("referral_code")).toBeNull();

      // Should still redirect to dashboard
      expect(mockHistoryReplace).toHaveBeenCalledWith("/dashboard");
    });

    it("continues auth flow and cleans up localStorage when referral API fails", async () => {
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

      // Should still remove referral code from localStorage
      expect(localStorage.getItem("referral_code")).toBeNull();

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

    it("cleans up localStorage on failed referral application", async () => {
      localStorage.setItem("referral_code", "TESTCODE");

      mockFetchWithToasts.mockRejectedValue(new Error("API Error"));

      render(
        <MemoryRouter>
          <AuthCallback />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(localStorage.getItem("referral_code")).toBeNull();
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
      expect(
        getByText(/Please wait while we complete your authentication/i),
      ).toBeInTheDocument();
    });
  });
});
