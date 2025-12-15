import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { EnrollmentAnalysisModal } from "../enrollment-analysis-modal";
import { customRender, mockUser, mockProfile } from "@/test/utils";
import type { ClassWithEnrollment } from "@/types/api";

// Mock the API module
vi.mock("@/lib/api", () => ({
  fetchWithToasts: vi.fn(),
}));

import { fetchWithToasts } from "@/lib/api";

const mockClassData: ClassWithEnrollment = {
  classId: 1,
  courseId: 1,
  classNumber: "12345",
  sectionCode: "001",
  isActive: true,
  currentEnrollment: {
    enrollmentStatus: "closed",
    scrapedAt: "2024-01-01",
  },
};

const mockAnalysisData = {
  classId: 1,
  timesOpenedLast30Days: 5,
  avgDaysToOpenLast30Days: 3,
  mostRecentOpening: "2024-01-10T10:00:00Z",
  subscriptionsCount: 10,
  notificationsSent: 25,
  competitionLevel: "medium" as const,
  generatedAt: "2024-01-15T12:00:00Z",
};

describe("EnrollmentAnalysisModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Statistics Display", () => {
    it("displays statistics without icons in labels", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockAnalysisData),
      } as Response);

      customRender(
        <EnrollmentAnalysisModal
          isOpen={true}
          onClose={() => {}}
          classData={mockClassData}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText("Times opened (30 days)")).toBeInTheDocument();
      });

      // Verify statistics labels are displayed (text only, no icons)
      expect(screen.getByText("Times opened (30 days)")).toBeInTheDocument();
      expect(screen.getByText("Avg days to open (30 days)")).toBeInTheDocument();
      expect(screen.getByText("Most recent open seat")).toBeInTheDocument();
      expect(screen.getByText("# subscriptions")).toBeInTheDocument();
      expect(screen.getByText("# notifications sent")).toBeInTheDocument();
      expect(screen.getByText("Competition level")).toBeInTheDocument();

      // Verify statistics values are displayed
      expect(screen.getByText("5")).toBeInTheDocument(); // timesOpenedLast30Days
      expect(screen.getByText("3")).toBeInTheDocument(); // avgDaysToOpenLast30Days
      expect(screen.getByText("10")).toBeInTheDocument(); // subscriptionsCount
      expect(screen.getByText("25")).toBeInTheDocument(); // notificationsSent
      expect(screen.getByText("MEDIUM")).toBeInTheDocument(); // competitionLevel
    });

    it("does not display competition level explanation text", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockAnalysisData),
      } as Response);

      customRender(
        <EnrollmentAnalysisModal
          isOpen={true}
          onClose={() => {}}
          classData={mockClassData}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText("Times opened (30 days)")).toBeInTheDocument();
      });

      // Verify competition level explanation card is not displayed
      expect(
        screen.queryByText(/Competition level is calculated based on/),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Few subscribers, good chance of success"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Moderate competition, be prepared"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Many watchers, very competitive"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when fetching data", () => {
      vi.mocked(fetchWithToasts).mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      customRender(
        <EnrollmentAnalysisModal
          isOpen={true}
          onClose={() => {}}
          classData={mockClassData}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      expect(screen.getByText("Loading analysis...")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("shows error message when fetch fails", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: false,
      } as Response);

      customRender(
        <EnrollmentAnalysisModal
          isOpen={true}
          onClose={() => {}}
          classData={mockClassData}
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

  describe("Competition Level Display", () => {
    it("displays low competition level correctly", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ ...mockAnalysisData, competitionLevel: "low" }),
      } as Response);

      customRender(
        <EnrollmentAnalysisModal
          isOpen={true}
          onClose={() => {}}
          classData={mockClassData}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText("LOW")).toBeInTheDocument();
      });
    });

    it("displays high competition level correctly", async () => {
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ ...mockAnalysisData, competitionLevel: "high" }),
      } as Response);

      customRender(
        <EnrollmentAnalysisModal
          isOpen={true}
          onClose={() => {}}
          classData={mockClassData}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionTier: "pro",
        },
      );

      await waitFor(() => {
        expect(screen.getByText("HIGH")).toBeInTheDocument();
      });
    });
  });
});
