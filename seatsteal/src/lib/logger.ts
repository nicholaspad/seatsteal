/**
 * Logging utility that prevents information leakage in production.
 *
 * In production:
 * - Logs to console only in development mode
 * - Errors are logged without sensitive details
 *
 * In development:
 * - Full error details are logged to console
 */

const isDevelopment = import.meta.env.DEV;

/**
 * Log an error with context. Safe for production as it doesn't log sensitive details.
 *
 * @param context - A brief description of where the error occurred
 * @param error - The error object (only logged in development)
 */
export function logError(context: string, error: unknown): void {
  if (isDevelopment) {
    console.error(`${context}:`, error);
  } else {
    // In production, only log the context without error details
    // This prevents sensitive information from being exposed in browser console
    console.error(`Error: ${context}`);

    // In a real production app, you would send this to a secure logging service
    // Example: sendToLoggingService(context, error);
  }
}

/**
 * Log a warning message. Safe for production.
 *
 * @param message - The warning message
 * @param data - Additional data (only logged in development)
 */
export function logWarning(message: string, data?: unknown): void {
  if (isDevelopment) {
    console.warn(message, data);
  }
}

/**
 * Log an info message. Only logs in development.
 *
 * @param message - The info message
 * @param data - Additional data
 */
export function logInfo(message: string, data?: unknown): void {
  if (isDevelopment) {
    console.info(message, data);
  }
}

/**
 * Log a debug message. Only logs in development.
 *
 * @param message - The debug message
 * @param data - Additional data
 */
export function logDebug(message: string, data?: unknown): void {
  if (isDevelopment) {
    console.debug(message, data);
  }
}

/**
 * Logger object that provides a unified logging interface.
 * Safe for production as it prevents information leakage.
 */
export const logger = {
  error: logError,
  warn: logWarning,
  warning: logWarning,
  info: logInfo,
  debug: logDebug,
};
