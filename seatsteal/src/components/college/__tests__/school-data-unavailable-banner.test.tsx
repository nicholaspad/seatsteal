import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { SchoolDataUnavailableBanner } from "../school-data-unavailable-banner";

describe("SchoolDataUnavailableBanner", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-18T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a friendly unavailable message with relative last-updated time", () => {
    render(
      <SchoolDataUnavailableBanner
        schoolName="University of Illinois"
        lastUpdatedAt="2026-10-16T12:00:00Z"
      />,
    );

    expect(
      screen.getByTestId("school-data-unavailable-banner"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Seat data for University of Illinois is temporarily unavailable/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Last updated 2 days ago/)).toBeInTheDocument();
  });

  it("says last updated unknown when no timestamp is provided", () => {
    render(<SchoolDataUnavailableBanner schoolName="Purdue" />);

    expect(screen.getByText(/Last updated unknown/)).toBeInTheDocument();
  });
});
