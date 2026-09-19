import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { IPhoneMockup } from "../iphone-mockup";

describe("IPhoneMockup", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the phone frame before the notification drops", () => {
    render(<IPhoneMockup />);

    const banner = screen.getByTestId("iphone-notification");
    expect(banner).toHaveAttribute("aria-hidden", "true");
    expect(banner).not.toHaveClass("iphone-banner-dropping");
    expect(banner).not.toHaveClass("iphone-banner-settled");
  });

  it("pulses the Dynamic Island then drops a Messages banner", () => {
    render(<IPhoneMockup />);

    act(() => {
      vi.advanceTimersByTime(900);
    });

    const banner = screen.getByTestId("iphone-notification");
    expect(banner).toHaveAttribute("aria-hidden", "true");

    act(() => {
      vi.advanceTimersByTime(220);
    });

    expect(banner).toHaveClass("iphone-banner-dropping");
    expect(banner).toHaveAttribute("aria-hidden", "false");
    expect(screen.getByText("MESSAGES")).toBeInTheDocument();
    expect(screen.getByText("SeatSteal")).toBeInTheDocument();
    expect(
      screen.getByText("Seat available in Intro to CS (CS 103) at Rutgers"),
    ).toBeInTheDocument();
  });

  it("settles the banner after the spring finishes", () => {
    render(<IPhoneMockup />);

    act(() => {
      vi.advanceTimersByTime(1120 + 720);
    });

    const banner = screen.getByTestId("iphone-notification");
    expect(banner).toHaveClass("iphone-banner-settled");
    expect(banner).toHaveAttribute("aria-hidden", "false");
  });
});
