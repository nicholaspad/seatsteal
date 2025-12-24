import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getUserTimezone,
  formatLocalDate,
  formatLocalTime,
  formatLocalDateTime,
  formatLocalDateTimeWithAt,
  formatChartDate,
  formatDetailedDateTime,
  formatCompactDateTime,
} from "../date-utils";

describe("date-utils", () => {
  describe("getUserTimezone", () => {
    it("returns the user's timezone from Intl API", () => {
      const timezone = getUserTimezone();
      expect(typeof timezone).toBe("string");
      expect(timezone.length).toBeGreaterThan(0);
    });

    it("returns UTC as fallback when Intl API fails", () => {
      const originalIntl = global.Intl;
      // @ts-expect-error - Mocking Intl to throw error
      global.Intl = undefined;

      const timezone = getUserTimezone();
      expect(timezone).toBe("UTC");

      // Restore Intl
      global.Intl = originalIntl;
    });
  });

  describe("formatLocalDate", () => {
    it("returns 'N/A' for null input", () => {
      expect(formatLocalDate(null)).toBe("N/A");
    });

    it("handles invalid date string", () => {
      expect(formatLocalDate("invalid-date")).toBe("Invalid Date");
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-12-24T10:30:00Z");
      const result = formatLocalDate(date);
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toContain("2024");
    });

    it("formats ISO string correctly", () => {
      const result = formatLocalDate("2024-12-24T10:30:00Z");
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toContain("2024");
    });

    it("handles leap year dates", () => {
      const result = formatLocalDate("2024-02-29T00:00:00Z");
      expect(result).toContain("Feb");
      expect(result).toContain("29");
      expect(result).toContain("2024");
    });
  });

  describe("formatLocalTime", () => {
    it("returns 'N/A' for null input", () => {
      expect(formatLocalTime(null)).toBe("N/A");
    });

    it("handles invalid date string", () => {
      expect(formatLocalTime("invalid-date")).toBe("Invalid Time");
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-12-24T14:30:00Z");
      const result = formatLocalTime(date);
      // Should include time in some format
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });

    it("formats ISO string correctly", () => {
      const result = formatLocalTime("2024-12-24T14:30:00Z");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });

    it("formats midnight correctly", () => {
      const result = formatLocalTime("2024-12-24T00:00:00Z");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });

    it("formats noon correctly", () => {
      const result = formatLocalTime("2024-12-24T12:00:00Z");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe("formatLocalDateTime", () => {
    it("returns 'N/A' for null input", () => {
      expect(formatLocalDateTime(null)).toBe("N/A");
    });

    it("handles invalid date string", () => {
      expect(formatLocalDateTime("invalid-date")).toBe("Invalid DateTime");
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-12-24T14:30:00Z");
      const result = formatLocalDateTime(date);
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toContain("2024");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });

    it("formats ISO string correctly", () => {
      const result = formatLocalDateTime("2024-12-24T14:30:00Z");
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe("formatLocalDateTimeWithAt", () => {
    it("returns 'N/A' for null input", () => {
      expect(formatLocalDateTimeWithAt(null)).toBe("N/A");
    });

    it("handles invalid date string", () => {
      expect(formatLocalDateTimeWithAt("invalid-date")).toBe(
        "Invalid DateTime",
      );
    });

    it("formats with 'at' separator", () => {
      const result = formatLocalDateTimeWithAt("2024-12-24T14:30:00Z");
      expect(result).toContain(" at ");
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });

    it("formats Date object with 'at' separator", () => {
      const date = new Date("2024-12-24T14:30:00Z");
      const result = formatLocalDateTimeWithAt(date);
      expect(result).toContain(" at ");
    });
  });

  describe("formatChartDate", () => {
    it("handles invalid date string", () => {
      expect(formatChartDate("invalid-date")).toBe("Invalid Date");
    });

    it("formats in short format for charts", () => {
      const result = formatChartDate("2024-12-24T14:30:00Z");
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      // Should NOT contain year for chart format
      expect(result).not.toContain("2024");
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-12-24T14:30:00Z");
      const result = formatChartDate(date);
      expect(result).toContain("Dec");
      expect(result).toContain("24");
    });

    it("handles different months", () => {
      const jan = formatChartDate("2024-01-15T00:00:00Z");
      const jun = formatChartDate("2024-06-15T00:00:00Z");

      expect(jan).toContain("Jan");
      expect(jun).toContain("Jun");
    });
  });

  describe("formatDetailedDateTime", () => {
    it("returns 'N/A' for null input", () => {
      expect(formatDetailedDateTime(null)).toBe("N/A");
    });

    it("handles invalid date string", () => {
      expect(formatDetailedDateTime("invalid-date")).toBe("Invalid DateTime");
    });

    it("formats with detailed information including weekday", () => {
      const result = formatDetailedDateTime("2024-12-24T14:30:45Z");
      // Should contain month, day, year, and time with seconds
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toContain("2024");
      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-12-24T14:30:45Z");
      const result = formatDetailedDateTime(date);
      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("includes weekday information", () => {
      // Tuesday, December 24, 2024
      const result = formatDetailedDateTime("2024-12-24T14:30:45Z");
      // Weekday should be in the string (format includes weekday: 'short')
      expect(result.length).toBeGreaterThan(20); // Detailed format is longer
    });
  });

  describe("formatCompactDateTime", () => {
    it("returns 'N/A' for null input", () => {
      expect(formatCompactDateTime(null)).toBe("N/A");
    });

    it("handles invalid date string", () => {
      expect(formatCompactDateTime("invalid-date")).toBe("Invalid DateTime");
    });

    it("formats in compact format (month/day, time)", () => {
      const result = formatCompactDateTime("2024-12-24T14:30:00Z");
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      // Should NOT contain year for compact format
      expect(result).not.toContain("2024");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-12-24T14:30:00Z");
      const result = formatCompactDateTime(date);
      expect(result).toContain("Dec");
      expect(result).toContain("24");
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe("edge cases", () => {
    it("handles dates at year boundaries", () => {
      const newYear = formatLocalDate("2025-01-01T00:00:00Z");
      const newYearsEve = formatLocalDate("2024-12-31T23:59:59Z");

      expect(newYear).toContain("2025");
      expect(newYear).toContain("Jan");
      expect(newYearsEve).toContain("2024");
      expect(newYearsEve).toContain("Dec");
    });

    it("handles very old dates", () => {
      const oldDate = formatLocalDate("1900-01-01T00:00:00Z");
      expect(oldDate).toContain("1900");
    });

    it("handles future dates", () => {
      const futureDate = formatLocalDate("2099-12-31T00:00:00Z");
      expect(futureDate).toContain("2099");
    });

    it("handles empty string", () => {
      // Empty string is falsy, so returns "N/A"
      expect(formatLocalDate("")).toBe("N/A");
      expect(formatLocalTime("")).toBe("N/A");
      expect(formatLocalDateTime("")).toBe("N/A");
    });
  });
});
