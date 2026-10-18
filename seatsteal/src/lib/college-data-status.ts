import type { College, CollegeDataStatus } from "@/types/api";

export function isCollegeDataStale(
  college?: Pick<College, "dataStatus"> | null,
): boolean {
  return college?.dataStatus === "stale";
}

export function getCollegeDataStatus(
  college?: Pick<College, "dataStatus"> | null,
): CollegeDataStatus {
  return college?.dataStatus === "stale" ? "stale" : "ok";
}
