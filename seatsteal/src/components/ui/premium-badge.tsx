import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface PremiumBadgeProps {
  className?: string;
  variant?: "default" | "small";
}

export function PremiumBadge({
  className,
  variant = "default",
}: PremiumBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "bg-gradient-to-r from-red-500 to-purple-500 text-white border-none",
        variant === "small" ? "text-xs" : "text-sm",
        className,
      )}
    >
      Premium
    </Badge>
  );
}
