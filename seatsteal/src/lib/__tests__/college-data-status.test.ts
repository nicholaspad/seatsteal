import { describe, it, expect } from "vitest";
import {
  getCollegeDataStatus,
  isCheckoutBlocked,
  isCollegeDataStale,
  isCollegeInactive,
} from "../college-data-status";

describe("college-data-status", () => {
  it("treats missing status as ok", () => {
    expect(isCollegeDataStale(undefined)).toBe(false);
    expect(isCollegeDataStale({ dataStatus: "ok" })).toBe(false);
    expect(getCollegeDataStatus(undefined)).toBe("ok");
    expect(isCheckoutBlocked(undefined)).toBe(false);
    expect(isCheckoutBlocked({ checkoutBlocked: false })).toBe(false);
  });

  it("detects stale colleges", () => {
    expect(isCollegeDataStale({ dataStatus: "stale" })).toBe(true);
    expect(getCollegeDataStatus({ dataStatus: "stale" })).toBe("stale");
  });

  it("blocks checkout only when checkoutBlocked is true", () => {
    expect(
      isCheckoutBlocked({ checkoutBlocked: true, dataStatus: "stale" }),
    ).toBe(true);
    expect(
      isCheckoutBlocked({ checkoutBlocked: false, dataStatus: "stale" }),
    ).toBe(false);
  });

  it("detects inactive colleges", () => {
    expect(isCollegeInactive(undefined)).toBe(false);
    expect(isCollegeInactive({ isActive: true })).toBe(false);
    expect(isCollegeInactive({ isActive: false })).toBe(true);
  });
});
