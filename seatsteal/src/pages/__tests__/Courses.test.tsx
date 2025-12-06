import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import Courses from "../Courses";
import { renderAnonymous, renderAuthenticated } from "@/test/utils";
import { mockCoursesResponse, mockCollegesResponse } from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

vi.mock("@/hooks/use-search-params", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

describe("Courses Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Logged Out User", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  data: mockCoursesResponse.data.data.slice(0, 3),
                  pagination: { page: 1, limit: 3, total: 10, totalPages: 4 },
                },
              }),
          } as Response);
        }
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: [] }),
        } as Response);
      });
    });

    it("renders breadcrumb navigation", async () => {
      renderAnonymous(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("Home")).toBeInTheDocument();
        expect(screen.getByText("Courses")).toBeInTheDocument();
      });
    });

    it("fetches courses with limit of 3 for anonymous users", async () => {
      renderAnonymous(<Courses />);

      await waitFor(() => {
        const calls = mockFetchWithToasts.mock.calls;
        const coursesCall = calls.find((call) =>
          (call[0] as string).includes("/api/courses"),
        );
        expect(coursesCall).toBeDefined();
        expect(coursesCall?.[0]).toContain("limit=3");
      });
    });

    it("shows course cards when data loads", async () => {
      renderAnonymous(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("CS101")).toBeInTheDocument();
      });
    });
  });

  describe("Logged In User", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCoursesResponse),
          } as Response);
        }
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: [] }),
        } as Response);
      });
    });

    it("fetches courses with limit of 12 for authenticated users", async () => {
      renderAuthenticated(<Courses />);

      await waitFor(() => {
        const calls = mockFetchWithToasts.mock.calls;
        const coursesCall = calls.find((call) =>
          (call[0] as string).includes("/api/courses"),
        );
        expect(coursesCall).toBeDefined();
        expect(coursesCall?.[0]).toContain("limit=12");
      });
    });

    it("shows course cards when data loads", async () => {
      renderAuthenticated(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("CS101")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("displays error message when API fails", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () =>
              Promise.resolve({ success: false, error: "Server error" }),
          } as Response);
        }
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: [] }),
        } as Response);
      });

      renderAuthenticated(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("Error Loading Courses")).toBeInTheDocument();
      });
    });
  });

  describe("Empty State", () => {
    it("shows empty state when no courses found", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  data: [],
                  pagination: { page: 1, limit: 12, total: 0, totalPages: 0 },
                },
              }),
          } as Response);
        }
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: [] }),
        } as Response);
      });

      renderAuthenticated(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("No Courses Found")).toBeInTheDocument();
      });
    });
  });
});
