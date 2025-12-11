import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
        screen.getByText("Get notified when a seat opens up."),
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

    it("renders view plans link", () => {
      renderAnonymous(<Home />);

      expect(screen.getByText("View plans")).toBeInTheDocument();
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

    it("handles empty colleges array gracefully", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, data: [] }),
      } as Response);

      renderAnonymous(<Home />);

      // Page should still render with empty colleges
      await waitFor(() => {
        expect(screen.getByText("Course full?")).toBeInTheDocument();
        expect(screen.getByText("FAQs")).toBeInTheDocument();
      });
    });
  });

  describe("External Links", () => {
    it("Request early access button has correct external link attributes", () => {
      renderAnonymous(<Home />);

      const earlyAccessLink = screen.getByRole("link", {
        name: /Request early access/i,
      });
      expect(earlyAccessLink).toHaveAttribute("target", "_blank");
      expect(earlyAccessLink).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("Request a college button has correct external link attributes", () => {
      renderAnonymous(<Home />);

      const requestCollegeLink = screen.getByRole("link", {
        name: /Request a college/i,
      });
      expect(requestCollegeLink).toHaveAttribute("target", "_blank");
      expect(requestCollegeLink).toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  describe("Smooth Scroll", () => {
    it("View plans button triggers scroll to plans section", async () => {
      const user = userEvent.setup();
      const scrollIntoViewMock = vi.fn();

      // Mock getElementById to return an element with scrollIntoView
      const mockElement = { scrollIntoView: scrollIntoViewMock };
      vi.spyOn(document, "getElementById").mockReturnValue(
        mockElement as unknown as HTMLElement,
      );

      renderAnonymous(<Home />);

      const viewPlansButton = screen.getByRole("button", {
        name: /View plans/i,
      });
      await user.click(viewPlansButton);

      expect(document.getElementById).toHaveBeenCalledWith("plans");
      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: "smooth",
        block: "start",
      });
    });
  });
});
