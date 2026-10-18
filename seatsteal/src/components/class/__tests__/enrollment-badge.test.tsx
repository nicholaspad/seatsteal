import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EnrollmentBadge } from "../enrollment-badge";
import type { ClassWithEnrollment } from "@/types/api";

const openClass: ClassWithEnrollment = {
  classId: 1,
  courseId: 1,
  classNumber: "12345",
  sectionCode: "001",
  createdAt: "2024-01-01",
  updatedAt: "2024-01-01",
  isActive: true,
  currentEnrollment: {
    enrollmentStatus: "open",
    scrapedAt: "2024-01-01",
  },
};

describe("EnrollmentBadge", () => {
  it("shows live open status by default", () => {
    render(<EnrollmentBadge class={openClass} />);
    expect(screen.getByText("OPEN")).toBeInTheDocument();
  });

  it("hides stale seat counts instead of presenting them as live", () => {
    render(<EnrollmentBadge class={openClass} dataStale />);
    expect(screen.getByText("UNAVAILABLE")).toBeInTheDocument();
    expect(screen.queryByText("OPEN")).not.toBeInTheDocument();
  });
});
