import { Badge } from "@/components/ui/badge";
import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { College } from "@/types/api";

interface CollegeBadgeProps {
  college: College;
  showIcon?: boolean;
  className?: string;
}

export function CollegeBadge({
  college,
  showIcon = false,
  className,
}: CollegeBadgeProps) {
  return (
    <Badge variant="secondary" className={cn("text-xs", className)}>
      {showIcon && <Building2 className="mr-1 h-3 w-3" />}
      {college.shortName}
    </Badge>
  );
}
