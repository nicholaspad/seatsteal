import { describe, it, expect } from "vitest";
import {
  getCollegeDataStatus,
  isCollegeDataStale,
} from "../college-data-status";

describe("college-data-status", () => {
  it("treats missing status as ok", () => {
    expect(isCollegeDataStale(undefined)).toBe(false);
    expect(isCollegeDataStale({ dataStatus: "ok" })).toBe(false);
    expect(getCollegeDataStatus(undefined)).toBe("ok");
  });

  it("detects stale colleges", () => {
    expect(isCollegeDataStale({ dataStatus: "stale" })).toBe(true);
    expect(getCollegeDataStatus({ dataStatus: "stale" })).toBe("stale");
  });
});
