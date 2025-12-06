import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import CourseDetails from "../CourseDetails";
import { renderAuthenticated } from "@/test/utils";
import { mockCourseData } from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ id: "1" }),
  };
});

describe("CourseDetails Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("shows loading spinner initially", () => {
      // Never resolve to keep in loading state
      mockFetchWithToasts.mockImplementation(
        () =>
          new Promise(() => {
            // Never resolve
          }),
      );

      renderAuthenticated(<CourseDetails />, {
        routerEntries: ["/courses/1"],
      });

      expect(screen.getByText("Loading course details...")).toBeInTheDocument();
    });
  });

  describe("Course Display", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses/1")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: mockCourseData }),
          } as Response);
        }
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("displays course content after loading", async () => {
      renderAuthenticated(<CourseDetails />, {
        routerEntries: ["/courses/1"],
      });

      await waitFor(() => {
        expect(
          screen.queryByText("Loading course details..."),
        ).not.toBeInTheDocument();
      });

      // CourseDetailsClient will be rendered with the course data
      expect(screen.getByTestId("ion-content")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("shows error when course not found", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: false,
        status: 404,
        json: () =>
          Promise.resolve({ success: false, error: "Course not found" }),
      } as Response);

      renderAuthenticated(<CourseDetails />, {
        routerEntries: ["/courses/999"],
      });

      await waitFor(() => {
        expect(screen.getByText("Course not found")).toBeInTheDocument();
      });
    });

    it("shows generic error message on API failure", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ success: false, error: "Server error" }),
      } as Response);

      renderAuthenticated(<CourseDetails />, {
        routerEntries: ["/courses/1"],
      });

      await waitFor(() => {
        expect(
          screen.getByText(
            "The course you're looking for could not be loaded.",
          ),
        ).toBeInTheDocument();
      });
    });

    it("shows Go Back button on error", async () => {
      mockFetchWithToasts.mockResolvedValue({
        ok: false,
        status: 404,
        json: () =>
          Promise.resolve({ success: false, error: "Course not found" }),
      } as Response);

      renderAuthenticated(<CourseDetails />, {
        routerEntries: ["/courses/999"],
      });

      await waitFor(() => {
        expect(screen.getByText("Go Back")).toBeInTheDocument();
      });
    });
  });
});
