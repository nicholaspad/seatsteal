import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, HelpCircle } from "lucide-react";
import type { ClassWithEnrollment } from "@/types/api";

interface EnrollmentBadgeProps {
  class: ClassWithEnrollment;
  className?: string;
}

export function EnrollmentBadge({
  class: classData,
  className,
}: EnrollmentBadgeProps) {
  const enrollment = classData.currentEnrollment;

  if (!enrollment) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <Badge
          variant="outline"
          className="text-muted-foreground font-medium min-w-[32px] sm:min-w-[90px] justify-center"
        >
          <HelpCircle className="h-3 w-3 sm:mr-1" />
          <span className="hidden sm:inline">NO DATA</span>
        </Badge>
      </div>
    );
  }

  const status = enrollment.enrollmentStatus.toUpperCase();

  // Determine status and styling
  let badgeVariant: "default" | "secondary" | "destructive" | "outline";
  let statusColor: string;
  let StatusIcon: React.ComponentType<{ className?: string }>;

  if (status === "OPEN") {
    badgeVariant = "default";
    statusColor = "text-green-700 bg-green-100 border-green-200";
    StatusIcon = CheckCircle;
  } else if (status === "CLOSED") {
    badgeVariant = "destructive";
    statusColor = "text-red-700 bg-red-100 border-red-200";
    StatusIcon = XCircle;
  } else {
    badgeVariant = "outline";
    statusColor = "text-gray-700 bg-gray-100 border-gray-200";
    StatusIcon = HelpCircle;
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Badge
        variant={badgeVariant}
        className={cn(
          statusColor,
          "font-medium min-w-[32px] sm:min-w-[90px] justify-center",
        )}
      >
        <StatusIcon className="h-3 w-3 sm:mr-1" />
        <span className="hidden sm:inline">{status}</span>
      </Badge>
    </div>
  );
}
