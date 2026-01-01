import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { Header } from "../Header";
import {
  renderAuthenticated,
  renderAnonymous,
  mockProfile,
} from "@/test/utils";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

describe("Header", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Admin Nav Item", () => {
    it("shows Admin nav item when user is admin", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, isAdmin: true }),
      } as Response);

      renderAuthenticated(<Header />);

      await waitFor(() => {
        expect(screen.getByText("Admin")).toBeInTheDocument();
      });
    });

    it("does not show Admin nav item when user is not admin", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, isAdmin: false }),
      } as Response);

      renderAuthenticated(<Header />);

      // Wait for the API call to complete
      await waitFor(() => {
        expect(mockFetchWithToasts).toHaveBeenCalledWith("/api/auth/is-admin");
      });

      // Admin should not be present
      expect(screen.queryByText("Admin")).not.toBeInTheDocument();
    });

    it("does not show Admin nav item for unauthenticated users", async () => {
      renderAnonymous(<Header />);

      // Admin should not be present and no API call should be made
      expect(screen.queryByText("Admin")).not.toBeInTheDocument();
      expect(mockFetchWithToasts).not.toHaveBeenCalled();
    });

    it("does not show Admin nav item when API call fails", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ success: false }),
      } as Response);

      renderAuthenticated(<Header />);

      // Wait for the API call to complete
      await waitFor(() => {
        expect(mockFetchWithToasts).toHaveBeenCalledWith("/api/auth/is-admin");
      });

      // Admin should not be present
      expect(screen.queryByText("Admin")).not.toBeInTheDocument();
    });

    it("does not show Admin nav item when API throws error", async () => {
      mockFetchWithToasts.mockRejectedValue(new Error("Network error"));

      renderAuthenticated(<Header />);

      // Wait for the API call to complete
      await waitFor(() => {
        expect(mockFetchWithToasts).toHaveBeenCalledWith("/api/auth/is-admin");
      });

      // Admin should not be present (graceful failure)
      expect(screen.queryByText("Admin")).not.toBeInTheDocument();
    });
  });

  describe("Standard Navigation", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, isAdmin: false }),
      } as Response);
    });

    it("shows Home nav item", () => {
      renderAnonymous(<Header />);

      expect(screen.getByText("Home")).toBeInTheDocument();
    });

    it("shows Courses nav item", () => {
      renderAnonymous(<Header />);

      expect(screen.getByText("Courses")).toBeInTheDocument();
    });

    it("shows Dashboard nav item for authenticated users", () => {
      renderAuthenticated(<Header />);

      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });

    it("does not show Dashboard nav item for anonymous users", () => {
      renderAnonymous(<Header />);

      expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
    });
  });

  describe("Admin nav item position", () => {
    it("Admin appears after Dashboard in navigation", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, isAdmin: true }),
      } as Response);

      renderAuthenticated(<Header />);

      await waitFor(() => {
        expect(screen.getByText("Admin")).toBeInTheDocument();
      });

      // Get all nav links in the desktop navigation
      const desktopNav = document.querySelector("nav.hidden.md\\:flex");
      const links = desktopNav?.querySelectorAll("a");

      // Find Dashboard and Admin positions
      let dashboardIndex = -1;
      let adminIndex = -1;

      links?.forEach((link, index) => {
        if (link.textContent?.includes("Dashboard")) dashboardIndex = index;
        if (link.textContent?.includes("Admin")) adminIndex = index;
      });

      // Admin should come after Dashboard
      expect(dashboardIndex).toBeGreaterThan(-1);
      expect(adminIndex).toBeGreaterThan(-1);
      expect(adminIndex).toBeGreaterThan(dashboardIndex);
    });
  });
});
