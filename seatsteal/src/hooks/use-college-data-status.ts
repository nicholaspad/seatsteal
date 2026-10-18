import { useEffect, useState } from "react";
import type { College } from "@/types/api";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import {
  isCheckoutBlocked,
  isCollegeDataStale,
} from "@/lib/college-data-status";
import { logError } from "@/lib/logger";

export function useCollegeDataStatus(collegeId?: number | null) {
  const [college, setCollege] = useState<College | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!collegeId) {
      setCollege(null);
      return;
    }

    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const response = await fetchWithToasts(`/api/colleges/${collegeId}`);
        if (!response.ok) return;
        const result = await response.json();
        if (!cancelled && result.success && result.data) {
          setCollege(result.data);
        }
      } catch (error) {
        if (!(error instanceof ServerErrorWithToast)) {
          logError("Failed to load college data status", error);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [collegeId]);

  return {
    college,
    loading,
    isStale: isCollegeDataStale(college),
    checkoutBlocked: isCheckoutBlocked(college),
  };
}
