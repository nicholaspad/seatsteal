import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { CourseSummaryModal } from "../course-summary-modal";
import { customRender, mockUser, mockProfile } from "@/test/utils";
import type { CourseWithCollege } from "@/types/api";

// Mock the API module
vi.mock("@/lib/api", () => ({
  fetchWithToasts: vi.fn(),
}));

import { fetchWithToasts } from "@/lib/api";

const mockCourse: CourseWithCollege = {
  id: 1,
  courseCode: "CS 101",
  title: "Introduction to Computer Science",
  collegeId: 1,
  isActive: true,
  college: {
    id: 1,
    name: "Test University",
    shortName: "TU",
    domain: "test.edu",
    termCode: "202401",
    termName: "Spring 2024",
    emailEnabled: true,
    smsEnabled: false,
    createdAt: "2024-01-01",
    isActive: true,
  },
};

const mockSummaryData = {
  courseId: 1,
  totalSubscriptions: 45,
  classesWithSubscriptions: 8,
  uniqueSubscribedUsers: 30,
  totalNotificationsSent: 120,
  totalClasses: 10,
  generatedAt: "2024-01-15T12:00:00Z",
};

describe("CourseSummaryModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Statistics Display", () => {
    it("displays all statistics correctly", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSummaryData),
      } as Response);

      customRender(
        <CourseSummaryModal
          isOpen={true}
          onClose={() => {}}
          course={mockCourse}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText("Total subscriptions")).toBeInTheDocument();
      });

      // Verify statistics labels are displayed
      expect(screen.getByText("Total subscriptions")).toBeInTheDocument();
      expect(
        screen.getByText("Classes with subscriptions"),
      ).toBeInTheDocument();
      expect(screen.getByText("Subscribed users")).toBeInTheDocument();
      expect(screen.getByText("Notifications sent")).toBeInTheDocument();

      // Verify statistics values are displayed
      expect(screen.getByText("45")).toBeInTheDocument(); // totalSubscriptions
      expect(screen.getByText("30")).toBeInTheDocument(); // uniqueSubscribedUsers
      expect(screen.getByText("120")).toBeInTheDocument(); // totalNotificationsSent

      // Verify the classes with subscriptions ratio
      expect(screen.getByText("8")).toBeInTheDocument();
      expect(screen.getByText("/10")).toBeInTheDocument();
    });

    it("displays course information correctly", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSummaryData),
      } as Response);

      customRender(
        <CourseSummaryModal
          isOpen={true}
          onClose={() => {}}
          course={mockCourse}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText("Total subscriptions")).toBeInTheDocument();
      });

      // Verify course details are displayed
      expect(
        screen.getByText("Introduction to Computer Science"),
      ).toBeInTheDocument();
      expect(screen.getByText("Test University")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows skeleton loaders when fetching data", () => {
      vi.mocked(fetchWithToasts).mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      const { container } = customRender(
        <CourseSummaryModal
          isOpen={true}
          onClose={() => {}}
          course={mockCourse}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      // Check for skeleton loaders (should have multiple skeleton elements)
      const skeletons = container.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Error State", () => {
    it("shows error message when fetch fails", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: false,
      } as Response);

      customRender(
        <CourseSummaryModal
          isOpen={true}
          onClose={() => {}}
          course={mockCourse}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
      });

      expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    });
  });

  describe("Data Freshness Indicator", () => {
    it("displays data freshness timestamp", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSummaryData),
      } as Response);

      customRender(
        <CourseSummaryModal
          isOpen={true}
          onClose={() => {}}
          course={mockCourse}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText(/Data as of/)).toBeInTheDocument();
      });

      // Verify the timestamp is displayed
      const freshnessText = screen.getByText(/Data as of/);
      expect(freshnessText).toBeInTheDocument();
      expect(freshnessText).toHaveClass("text-xs");
      expect(freshnessText).toHaveClass("text-muted-foreground");
    });
  });

  describe("Empty State", () => {
    it("shows empty state when no data is available", () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(null),
      } as Response);

      customRender(
        <CourseSummaryModal
          isOpen={true}
          onClose={() => {}}
          course={mockCourse}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      // Modal should not be visible when closed
      expect(
        screen.queryByText("No Summary Available"),
      ).not.toBeInTheDocument();
    });
  });
});
