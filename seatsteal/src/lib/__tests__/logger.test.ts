import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { logError, logWarning, logInfo } from "../logger";

describe("Logger", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
  let consoleInfoSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    consoleInfoSpy = vi.spyOn(console, "info").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleInfoSpy.mockRestore();
  });

  describe("logError", () => {
    it("logs full error details", () => {
      const error = new Error("Test error");
      logError("Test context", error);

      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining("Test context"),
        expect.anything(),
      );
    });

    it("handles non-Error objects", () => {
      logError("String error", "Something went wrong");

      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it("handles null and undefined errors", () => {
      logError("Null error", null);
      logError("Undefined error", undefined);

      expect(consoleErrorSpy).toHaveBeenCalledTimes(2);
    });

    it("logs with context string", () => {
      const error = new Error("Database error");
      logError("DB connection failed", error);

      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe("logWarning", () => {
    it("logs warning with data", () => {
      const data = { userId: 123, action: "test" };
      logWarning("Deprecated API used", data);

      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it("works without optional data parameter", () => {
      logWarning("Simple warning");

      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it("handles complex data objects", () => {
      const complexData = {
        nested: { value: 123 },
        array: [1, 2, 3],
      };
      logWarning("Complex warning", complexData);

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Complex warning",
        complexData,
      );
    });
  });

  describe("logInfo", () => {
    it("logs info message with data", () => {
      const data = { count: 5, items: ["a", "b"] };
      logInfo("Items processed", data);

      expect(consoleInfoSpy).toHaveBeenCalledWith("Items processed", data);
    });

    it("works without optional data parameter", () => {
      logInfo("Simple info");

      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it("handles various data types", () => {
      logInfo("Number", 42);
      logInfo("Boolean", true);
      logInfo("Array", [1, 2, 3]);
      logInfo("Object", { key: "value" });

      expect(consoleInfoSpy).toHaveBeenCalledWith("Number", 42);
      expect(consoleInfoSpy).toHaveBeenCalledWith("Boolean", true);
      expect(consoleInfoSpy).toHaveBeenCalledWith("Array", [1, 2, 3]);
      expect(consoleInfoSpy).toHaveBeenCalledWith("Object", { key: "value" });
    });
  });

  describe("Logging behavior", () => {
    it("calls console.error for logError", () => {
      logError("Error context", new Error("test"));

      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it("calls console.warn for logWarning", () => {
      logWarning("Warning message");

      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it("calls console.info for logInfo", () => {
      logInfo("Info message");

      expect(consoleInfoSpy).toHaveBeenCalled();
    });
  });
});
