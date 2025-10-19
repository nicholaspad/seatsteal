/**
 * Centralized date utility functions for timezone-aware date formatting.
 * All times are stored in UTC in the database and converted to user's local timezone for display.
 */

/**
 * Gets the user's timezone from the browser
 */
export function getUserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    // Fallback to UTC if timezone detection fails
    return "UTC";
  }
}

/**
 * Format a date to a localized date string in the user's timezone
 */
export function formatLocalDate(date: Date | string | null): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid Date";

  return dateObj.toLocaleDateString(undefined, {
    timeZone: getUserTimezone(),
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format a date to a localized time string in the user's timezone
 */
export function formatLocalTime(date: Date | string | null): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid Time";

  return dateObj.toLocaleTimeString(undefined, {
    timeZone: getUserTimezone(),
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a date to a complete localized date and time string in the user's timezone
 */
export function formatLocalDateTime(date: Date | string | null): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid DateTime";

  return dateObj.toLocaleString(undefined, {
    timeZone: getUserTimezone(),
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a date for display in the format "Date at Time"
 */
export function formatLocalDateTimeWithAt(date: Date | string | null): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid DateTime";

  const dateStr = formatLocalDate(dateObj);
  const timeStr = formatLocalTime(dateObj);

  return `${dateStr} at ${timeStr}`;
}

/**
 * Format a date for chart/tooltip display (shorter format)
 */
export function formatChartDate(date: Date | string): string {
  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid Date";

  return dateObj.toLocaleDateString(undefined, {
    timeZone: getUserTimezone(),
    month: "short",
    day: "numeric",
  });
}

/**
 * Format a date for detailed tooltips and admin interfaces
 */
export function formatDetailedDateTime(date: Date | string | null): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid DateTime";

  return dateObj.toLocaleString(undefined, {
    timeZone: getUserTimezone(),
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Format a date for compact display (month/day, time)
 */
export function formatCompactDateTime(date: Date | string | null): string {
  if (!date) return "N/A";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "Invalid DateTime";

  return dateObj.toLocaleString(undefined, {
    timeZone: getUserTimezone(),
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
