import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SchoolDataUnavailableBanner } from "../school-data-unavailable-banner";
import { resetMockSessionState } from "@/test/setup";

const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

describe("SchoolDataUnavailableBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetMockSessionState();
    mockFetchWithToasts.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    resetMockSessionState();
  });

  it("shows a friendly unavailable message with relative last-updated time", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-18T12:00:00Z"));

    render(
      <SchoolDataUnavailableBanner
        collegeId={1}
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
    expect(
      screen.getByRole("button", { name: /notify me when it's back/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/text/i)).not.toBeInTheDocument();
  });

  it("says last updated unknown when no timestamp is provided", () => {
    render(<SchoolDataUnavailableBanner collegeId={2} schoolName="Purdue" />);

    expect(screen.getByText(/Last updated unknown/)).toBeInTheDocument();
  });

  it("registers a signed-in user with one click", async () => {
    const user = userEvent.setup();
    globalThis.__mockSessionState.user = {
      id: "user-1",
      email: "student@school.edu",
    } as never;

    render(<SchoolDataUnavailableBanner collegeId={7} schoolName="Purdue" />);

    expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /notify me when it's back/i }),
    );

    await waitFor(() => {
      expect(mockFetchWithToasts).toHaveBeenCalledWith(
        "/api/colleges/7/data-waitlist",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({}),
        }),
      );
    });
    expect(
      screen.getByText("We'll let you know when it's back"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/text/i)).not.toBeInTheDocument();
  });

  it("collects and validates email for signed-out visitors", async () => {
    const user = userEvent.setup();

    render(<SchoolDataUnavailableBanner collegeId={7} schoolName="Purdue" />);

    await user.click(
      screen.getByRole("button", { name: /notify me when it's back/i }),
    );
    expect(screen.getByText("Enter a valid email")).toBeInTheDocument();
    expect(mockFetchWithToasts).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.click(
      screen.getByRole("button", { name: /notify me when it's back/i }),
    );
    expect(screen.getByText("Enter a valid email")).toBeInTheDocument();
    expect(mockFetchWithToasts).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText(/email/i));
    await user.type(screen.getByLabelText(/email/i), "visitor@example.com");
    await user.click(
      screen.getByRole("button", { name: /notify me when it's back/i }),
    );

    await waitFor(() => {
      expect(mockFetchWithToasts).toHaveBeenCalledWith(
        "/api/colleges/7/data-waitlist",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ email: "visitor@example.com" }),
        }),
      );
    });
    expect(
      screen.getByText("We'll let you know when it's back"),
    ).toBeInTheDocument();
  });
});
