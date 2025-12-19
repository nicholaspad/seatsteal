import { describe, it, expect } from "vitest";
import { isValidStripeUrl, getErrorMessage } from "../security";

describe("Security Utilities", () => {
  describe("isValidStripeUrl", () => {
    describe("valid Stripe URLs", () => {
      it("returns true for checkout.stripe.com with HTTPS", () => {
        expect(
          isValidStripeUrl("https://checkout.stripe.com/pay/cs_test_123"),
        ).toBe(true);
      });

      it("returns true for billing.stripe.com with HTTPS", () => {
        expect(
          isValidStripeUrl("https://billing.stripe.com/portal/session/123"),
        ).toBe(true);
      });

      it("returns true for buy.stripe.com with HTTPS", () => {
        expect(isValidStripeUrl("https://buy.stripe.com/test/123")).toBe(true);
      });

      it("returns true for Stripe URLs with query parameters", () => {
        expect(
          isValidStripeUrl(
            "https://checkout.stripe.com/pay?session_id=cs_test_123",
          ),
        ).toBe(true);
      });

      it("returns true for Stripe URLs with hash fragments", () => {
        expect(
          isValidStripeUrl(
            "https://checkout.stripe.com/pay/cs_test_123#success",
          ),
        ).toBe(true);
      });
    });

    describe("invalid Stripe URLs", () => {
      it("returns false for HTTP (non-HTTPS) Stripe URLs", () => {
        expect(isValidStripeUrl("http://checkout.stripe.com/pay")).toBe(false);
      });

      it("returns false for non-Stripe domains", () => {
        expect(isValidStripeUrl("https://evil.com/stripe")).toBe(false);
      });

      it("returns false for stripe.com (main domain)", () => {
        expect(isValidStripeUrl("https://stripe.com")).toBe(false);
      });

      it("returns false for subdomain spoofing attempts", () => {
        expect(
          isValidStripeUrl("https://checkout.stripe.com.evil.com"),
        ).toBe(false);
      });

      it("returns false for malformed URLs", () => {
        expect(isValidStripeUrl("not a url")).toBe(false);
      });

      it("returns false for empty string", () => {
        expect(isValidStripeUrl("")).toBe(false);
      });

      it("returns false for URLs with stripe in path but wrong domain", () => {
        expect(isValidStripeUrl("https://evil.com/checkout.stripe.com")).toBe(
          false,
        );
      });

      it("returns false for javascript: protocol", () => {
        expect(isValidStripeUrl("javascript:alert(1)")).toBe(false);
      });

      it("returns false for data: protocol", () => {
        expect(isValidStripeUrl("data:text/html,<script>alert(1)</script>")).toBe(
          false,
        );
      });

      it("returns false for relative URLs", () => {
        expect(isValidStripeUrl("/checkout/session")).toBe(false);
      });
    });
  });

  describe("getErrorMessage", () => {
    describe("known error codes", () => {
      it("returns correct message for auth_failed", () => {
        const result = getErrorMessage("auth_failed");
        expect(result.title).toBe("Authentication Failed");
        expect(result.message).toBe("Please try signing in again.");
      });

      it("returns correct message for session_expired", () => {
        const result = getErrorMessage("session_expired");
        expect(result.title).toBe("Session Expired");
        expect(result.message).toBe(
          "Your session has expired. Please sign in again.",
        );
      });

      it("returns correct message for access_denied", () => {
        const result = getErrorMessage("access_denied");
        expect(result.title).toBe("Access Denied");
        expect(result.message).toBe(
          "You don't have permission to access this resource.",
        );
      });

      it("returns correct message for payment_failed", () => {
        const result = getErrorMessage("payment_failed");
        expect(result.title).toBe("Payment Failed");
        expect(result.message).toBe(
          "There was an issue processing your payment. Please try again.",
        );
      });

      it("returns correct message for not_found", () => {
        const result = getErrorMessage("not_found");
        expect(result.title).toBe("Not Found");
        expect(result.message).toBe("The requested resource was not found.");
      });

      it("returns correct message for server_error", () => {
        const result = getErrorMessage("server_error");
        expect(result.title).toBe("Server Error");
        expect(result.message).toBe(
          "An internal error occurred. Please try again later.",
        );
      });

      it("returns correct message for network_error", () => {
        const result = getErrorMessage("network_error");
        expect(result.title).toBe("Network Error");
        expect(result.message).toBe(
          "Please check your internet connection and try again.",
        );
      });

      it("returns correct message for rate_limited", () => {
        const result = getErrorMessage("rate_limited");
        expect(result.title).toBe("Too Many Requests");
        expect(result.message).toBe("Please wait a moment before trying again.");
      });
    });

    describe("unknown or invalid error codes", () => {
      it("returns default message for null", () => {
        const result = getErrorMessage(null);
        expect(result.title).toBe("An Error Occurred");
        expect(result.message).toBe("Please try again later.");
      });

      it("returns default message for unknown error code", () => {
        const result = getErrorMessage("unknown_error");
        expect(result.title).toBe("An Error Occurred");
        expect(result.message).toBe("Please try again later.");
      });

      it("returns default message for empty string", () => {
        const result = getErrorMessage("");
        expect(result.title).toBe("An Error Occurred");
        expect(result.message).toBe("Please try again later.");
      });

      it("returns default message for XSS attempt", () => {
        const result = getErrorMessage("<script>alert(1)</script>");
        expect(result.title).toBe("An Error Occurred");
        expect(result.message).toBe("Please try again later.");
      });

      it("returns default message for SQL injection attempt", () => {
        const result = getErrorMessage("'; DROP TABLE users; --");
        expect(result.title).toBe("An Error Occurred");
        expect(result.message).toBe("Please try again later.");
      });
    });

    describe("security - prevents information disclosure", () => {
      it("does not include raw error code in message", () => {
        const errorCode = "secret_internal_error";
        const result = getErrorMessage(errorCode);
        expect(result.title).not.toContain(errorCode);
        expect(result.message).not.toContain(errorCode);
      });

      it("sanitizes by returning safe default for arbitrary input", () => {
        const result = getErrorMessage("../../../etc/passwd");
        expect(result.title).toBe("An Error Occurred");
        expect(result.message).toBe("Please try again later.");
      });
    });
  });
});
