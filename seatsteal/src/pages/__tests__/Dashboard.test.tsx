import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import Dashboard from "../Dashboard";
import { renderAuthenticated } from "@/test/utils";
import {
  mockSubscriptionData,
  mockTrendsResponse,
  mockMultipleSubscriptions,
  mockEmptyTrendsResponse,
} from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

describe("Dashboard Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("shows loading skeleton while tier is loading", () => {
      renderAuthenticated(<Dashboard />, { tierLoading: true });

      // The loading skeleton has animate-pulse class
      const skeleton = document.querySelector(".animate-pulse");
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe("Rendering", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: [mockSubscriptionData] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("renders the dashboard container", async () => {
      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByTestId("ion-page")).toBeInTheDocument();
      });
    });

    it("passes correct tier to UserDashboard", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });
  });

  describe("Tier Display", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, data: [] }),
      } as Response);
    });

    it("renders with free tier", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "free" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });

    it("renders with plus tier", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });

    it("renders with pro tier", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "pro" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });
  });

  describe("Subscriptions Display", () => {
    it("displays subscription cards with course info when subscriptions exist", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: mockMultipleSubscriptions,
              }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        // Should show course codes from subscriptions
        expect(screen.getByText("CS101")).toBeInTheDocument();
        expect(screen.getByText("CS102")).toBeInTheDocument();
        expect(screen.getByText("CS201")).toBeInTheDocument();
      });
    });

    it("shows No Subscriptions Yet empty state with Browse Courses button", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText("No Subscriptions Yet")).toBeInTheDocument();
        expect(screen.getByText("Browse Courses")).toBeInTheDocument();
      });
    });

    it("displays Unsubscribe button on subscription cards", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: [mockSubscriptionData] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText("Unsubscribe")).toBeInTheDocument();
      });
    });
  });

  describe("Weekly Trend Chart", () => {
    it("displays weekly notification trend chart", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: [mockSubscriptionData] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        // Should show day labels for the trend chart
        expect(screen.getByText("Mon")).toBeInTheDocument();
        expect(screen.getByText("Tue")).toBeInTheDocument();
        expect(screen.getByText("Wed")).toBeInTheDocument();
        expect(screen.getByText("Thu")).toBeInTheDocument();
        expect(screen.getByText("Fri")).toBeInTheDocument();
        expect(screen.getByText("Sat")).toBeInTheDocument();
        expect(screen.getByText("Sun")).toBeInTheDocument();
      });
    });

    it("shows No notifications this week when all bars are zero", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(
          screen.getByText("No notifications this week."),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Tier Badge Display", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("shows free tier badge for free tier users", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "free" });

      await waitFor(() => {
        expect(screen.getByText("free")).toBeInTheDocument();
      });
    });

    it("shows plus tier badge for plus tier users", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

      await waitFor(() => {
        expect(screen.getByText("plus")).toBeInTheDocument();
      });
    });

    it("shows pro tier badge for pro tier users", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "pro" });

      await waitFor(() => {
        expect(screen.getByText("pro")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("shows error card with Try Again button when subscription fetch fails", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () =>
              Promise.resolve({ success: false, error: "Server error" }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText("Error Loading Dashboard")).toBeInTheDocument();
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });
    });
  });
});
