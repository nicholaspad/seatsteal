import { useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ClassWithEnrollment } from "@/types/api";

interface ClassSectionsHeaderProps {
  classes: ClassWithEnrollment[];
  filter: FilterType;
  onFilterChange: (filter: FilterType) => void;
  filteredCount: number;
  className?: string;
}

export type FilterType = "all" | "open" | "closed";

export function ClassSectionsHeader({
  classes,
  filter,
  onFilterChange,
  filteredCount,
  className,
}: ClassSectionsHeaderProps) {
  // Calculate summary stats
  const summary = useMemo(() => {
    const total = classes.length;
    const open = classes.filter(
      (c) => c.currentEnrollment?.enrollmentStatus.toLowerCase() === "open",
    ).length;
    const closed = classes.filter(
      (c) => c.currentEnrollment?.enrollmentStatus.toLowerCase() === "closed",
    ).length;
    return { total, open, closed };
  }, [classes]);

  return (
    <div className={cn("space-y-4", className)}>
      {/* Summary badges */}
      <div className="flex flex-wrap gap-1">
        <Badge variant="outline" className="text-xs">
          {summary.total} total
        </Badge>
        {summary.open > 0 && (
          <Badge className="bg-green-100 text-green-700 hover:bg-green-200 text-xs">
            {summary.open} open
          </Badge>
        )}
        {summary.closed > 0 && (
          <Badge className="bg-red-100 text-red-700 hover:bg-red-200 text-xs">
            {summary.closed} closed
          </Badge>
        )}
      </div>

      {/* Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Filter Classes</label>
        <Select
          value={filter}
          onValueChange={(value: string) => onFilterChange(value as FilterType)}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Classes</SelectItem>
            <SelectItem value="open">Open Only</SelectItem>
            <SelectItem value="closed">Closed Only</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground">
          Showing {filteredCount} of {classes.length} classes
        </p>
      </div>
    </div>
  );
}
