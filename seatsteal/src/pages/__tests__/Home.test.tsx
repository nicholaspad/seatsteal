import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import Home from "../Home";
import { renderAnonymous } from "@/test/utils";
import { mockCollegesResponse } from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

describe("Home Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchWithToasts.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCollegesResponse),
    } as Response);
  });

  describe("Rendering", () => {
    it("renders hero section with main headline", () => {
      renderAnonymous(<Home />);

      expect(screen.getByText("Course full?")).toBeInTheDocument();
      expect(
        screen.getByText("Get notified when a spot opens."),
      ).toBeInTheDocument();
    });

    it("renders call-to-action buttons", () => {
      renderAnonymous(<Home />);

      expect(screen.getByText("Request early access")).toBeInTheDocument();
      expect(screen.getByText("Request a college")).toBeInTheDocument();
    });

    it("renders pricing section", () => {
      renderAnonymous(<Home />);

      expect(screen.getByText("Plans")).toBeInTheDocument();
    });

    it("renders FAQ section", () => {
      renderAnonymous(<Home />);

      expect(screen.getByText("FAQs")).toBeInTheDocument();
    });

    it("renders view pricing link", () => {
      renderAnonymous(<Home />);

      expect(screen.getByText("View pricing")).toBeInTheDocument();
    });
  });

  describe("Colleges Loading", () => {
    it("fetches colleges on mount", async () => {
      renderAnonymous(<Home />);

      await waitFor(() => {
        expect(mockFetchWithToasts).toHaveBeenCalledWith(
          "/api/colleges?active=true",
        );
      });
    });

    it("handles API errors gracefully", () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ success: false }),
      } as Response);

      renderAnonymous(<Home />);

      // Page should still render even if API fails
      expect(screen.getByText("Course full?")).toBeInTheDocument();
    });
  });
});
