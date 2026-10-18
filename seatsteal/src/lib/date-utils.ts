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
 * Format a timestamp as a short relative phrase, e.g. "3 hours ago".
 */
export function formatRelativeTime(date: Date | string | null): string {
  if (!date) return "unknown";

  const dateObj = typeof date === "string" ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return "unknown";

  const diffMs = Date.now() - dateObj.getTime();
  if (diffMs < 0) return "just now";

  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes === 1) return "1 minute ago";
  if (minutes < 60) return `${minutes} minutes ago`;

  const hours = Math.floor(minutes / 60);
  if (hours === 1) return "1 hour ago";
  if (hours < 24) return `${hours} hours ago`;

  const days = Math.floor(hours / 24);
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;

  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  if (months < 12) return `${months} months ago`;

  const years = Math.floor(days / 365);
  return years === 1 ? "1 year ago" : `${years} years ago`;
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
