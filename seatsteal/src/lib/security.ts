/**
 * Security utilities for frontend validation
 */

/**
 * Validates that a URL is a legitimate Stripe checkout or portal URL.
 * This helps prevent phishing attacks if the backend is compromised.
 *
 * @param url - The URL to validate
 * @returns true if the URL is a valid Stripe URL, false otherwise
 */
export function isValidStripeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    // Allow only HTTPS Stripe domains
    const validHostnames = [
      "checkout.stripe.com",
      "billing.stripe.com",
      "buy.stripe.com",
    ];
    return (
      parsed.protocol === "https:" && validHostnames.includes(parsed.hostname)
    );
  } catch {
    return false;
  }
}

/**
 * Validates and sanitizes an error message parameter from URL.
 * Only allows predefined error codes to prevent XSS or information disclosure.
 *
 * @param errorCode - The error code from URL parameter
 * @returns A safe, user-friendly error message
 */
export function getErrorMessage(errorCode: string | null): {
  title: string;
  message: string;
} {
  const errorMessages: Record<string, { title: string; message: string }> = {
    auth_failed: {
      title: "Authentication Failed",
      message: "Please try signing in again.",
    },
    session_expired: {
      title: "Session Expired",
      message: "Your session has expired. Please sign in again.",
    },
    access_denied: {
      title: "Access Denied",
      message: "You don't have permission to access this resource.",
    },
    payment_failed: {
      title: "Payment Failed",
      message: "There was an issue processing your payment. Please try again.",
    },
    not_found: {
      title: "Not Found",
      message: "The requested resource was not found.",
    },
    server_error: {
      title: "Server Error",
      message: "An internal error occurred. Please try again later.",
    },
    network_error: {
      title: "Network Error",
      message: "Please check your internet connection and try again.",
    },
    rate_limited: {
      title: "Too Many Requests",
      message: "Please wait a moment before trying again.",
    },
  };

  const defaultError = {
    title: "An Error Occurred",
    message: "Please try again later.",
  };

  if (!errorCode) {
    return defaultError;
  }

  return errorMessages[errorCode] || defaultError;
}
