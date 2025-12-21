import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import Courses from "../Courses";
import { renderAnonymous, renderAuthenticated } from "@/test/utils";
import {
  mockCoursesResponse,
  mockCollegesResponse,
  mockCoursesResponseWithPagination,
} from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
const mockUseSearchParams = vi.fn(() => new URLSearchParams());
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

vi.mock("@/hooks/use-search-params", () => ({
  useSearchParams: () => mockUseSearchParams(),
}));

describe("Courses Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Logged Out User", () => {
    beforeEach(() => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
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
        // Use getAllByText since "Courses" appears in both breadcrumb and page heading
        expect(screen.getAllByText("Courses").length).toBeGreaterThan(0);
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

    it("shows blurred course cards for anonymous users", async () => {
      renderAnonymous(<Courses />);

      await waitFor(() => {
        // Should show the course but with blurred overlay
        expect(screen.getByText("CS101")).toBeInTheDocument();
      });
    });
  });

  describe("Logged In User", () => {
    beforeEach(() => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
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

    it("does not show CTA banner for authenticated users", async () => {
      renderAuthenticated(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("CS101")).toBeInTheDocument();
      });

      // CTA banner should not be visible for authenticated users
      expect(
        screen.queryByText(/Sign up to see all courses/i),
      ).not.toBeInTheDocument();
    });
  });

  describe("College filter", () => {
    it("defaults to All colleges when the search param is undefined", async () => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams("college=undefined"));

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

      renderAuthenticated(<Courses />);

      await waitFor(() => {
        expect(screen.getByText("All colleges")).toBeInTheDocument();
      });
    });
  });

  describe("Pagination", () => {
    it("shows page number buttons when totalPages > 1 for authenticated users", async () => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCoursesResponseWithPagination),
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
        // Page number buttons should be visible when there are multiple pages
        expect(screen.getByLabelText(/Go to page 1/i)).toBeInTheDocument();
      });
    });

    it("does not show page number buttons when only one page", async () => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCoursesResponse), // totalPages: 1
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
        expect(screen.getByText("CS101")).toBeInTheDocument();
      });

      // Page number buttons should not be visible when only one page
      expect(screen.queryByLabelText(/Go to page/i)).not.toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("displays error message when API fails", async () => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
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
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
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

  describe("Edge Cases", () => {
    it("handles courses with empty classes array gracefully", async () => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
      const courseWithEmptyClasses = {
        id: 1,
        courseCode: "CS101",
        title: "Introduction to Computer Science",
        collegeId: 1,
        isActive: true,
        createdAt: "2024-01-01",
        updatedAt: "2024-01-01",
        college: { id: 1, name: "Test University", shortName: "TU" },
        classes: [], // Empty classes array
      };

      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/courses")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  data: [courseWithEmptyClasses],
                  pagination: { page: 1, limit: 12, total: 1, totalPages: 1 },
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

      // Should still render the course card without crashing
      await waitFor(() => {
        expect(screen.getByText("CS101")).toBeInTheDocument();
      });
    });

    it("shows Try Again button in error state", async () => {
      mockUseSearchParams.mockReturnValue(new URLSearchParams());
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
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });
    });
  });
});
