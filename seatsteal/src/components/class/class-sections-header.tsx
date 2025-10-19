import { useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Filter, SortAsc, Users, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ClassWithEnrollment } from "@/types/api";

interface ClassSectionsHeaderProps {
  classes: ClassWithEnrollment[];
  filter: FilterType;
  sort: SortType;
  onFilterChange: (filter: FilterType) => void;
  onSortChange: (sort: SortType) => void;
  filteredCount: number;
  className?: string;
}

export type FilterType = "all" | "open" | "closed";
export type SortType = "number" | "status";

export function ClassSectionsHeader({
  classes,
  filter,
  sort,
  onFilterChange,
  onSortChange,
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
      {/* Header with title and badges */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4" />
          <h3 className="font-semibold text-sm">Class Sections</h3>
        </div>

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
      </div>

      {/* Filters */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Filter className="h-3 w-3 text-muted-foreground" />
          <Select
            value={filter}
            onValueChange={(value: string) =>
              onFilterChange(value as FilterType)
            }
          >
            <SelectTrigger className="w-full text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Classes</SelectItem>
              <SelectItem value="open">Open Only</SelectItem>
              <SelectItem value="closed">Closed Only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <SortAsc className="h-3 w-3 text-muted-foreground" />
          <Select
            value={sort}
            onValueChange={(value: string) => onSortChange(value as SortType)}
          >
            <SelectTrigger className="w-full text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="number">Class Number</SelectItem>
              <SelectItem value="status">Status</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Count display */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground pt-1">
          <Calendar className="h-3 w-3" />
          <span>
            Showing {filteredCount} of {classes.length} classes
          </span>
        </div>
      </div>
    </div>
  );
}
