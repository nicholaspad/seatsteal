import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatRelativeTime } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

interface SchoolDataUnavailableBannerProps {
  schoolName: string;
  lastUpdatedAt?: string | null;
  className?: string;
}

export function SchoolDataUnavailableBanner({
  schoolName,
  lastUpdatedAt,
  className,
}: SchoolDataUnavailableBannerProps) {
  const relativeTime = formatRelativeTime(lastUpdatedAt ?? null);

  return (
    <Alert
      className={cn(
        "border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-50",
        className,
      )}
      data-testid="school-data-unavailable-banner"
    >
      <AlertTriangle className="text-amber-600 dark:text-amber-400" />
      <AlertTitle>Seat data temporarily unavailable</AlertTitle>
      <AlertDescription>
        Seat data for {schoolName} is temporarily unavailable. We&apos;re
        working on it. Last updated {relativeTime}.
      </AlertDescription>
    </Alert>
  );
}
