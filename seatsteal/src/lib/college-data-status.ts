import type { College, CollegeDataStatus } from "@/types/api";

export function isCollegeDataStale(
  college?: Pick<College, "dataStatus"> | null,
): boolean {
  return college?.dataStatus === "stale";
}

export function isCheckoutBlocked(
  college?: Pick<College, "checkoutBlocked"> | null,
): boolean {
  return college?.checkoutBlocked === true;
}

export function getCollegeDataStatus(
  college?: Pick<College, "dataStatus"> | null,
): CollegeDataStatus {
  return college?.dataStatus === "stale" ? "stale" : "ok";
}
