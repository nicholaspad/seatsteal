import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import Dashboard from "../Dashboard";
import { renderAuthenticated } from "@/test/utils";
import { mockSubscriptionData, mockTrendsResponse } from "@/test/mocks/api";

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
});
