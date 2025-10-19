import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CollegesApiResponse, College } from "@/types/api";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

interface CollegeFilterProps {
  value?: number;
  onValueChange: (collegeId: number | undefined) => void;
  placeholder?: string;
  className?: string;
  showAllOption?: boolean;
}

export function CollegeFilter({
  value,
  onValueChange,
  placeholder = "Select college...",
  className,
  showAllOption = true,
}: CollegeFilterProps) {
  const [colleges, setColleges] = useState<College[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchColleges() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetchWithToasts("/api/colleges");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: CollegesApiResponse = await response.json();

        if (!data.success) {
          throw new Error(data.error || "Failed to fetch colleges");
        }

        if (data.data) {
          // Filter only active colleges and sort by name
          const activeColleges = data.data
            .filter((college) => college.isActive)
            .sort((a, b) => a.name.localeCompare(b.name));
          setColleges(activeColleges);
        }
      } catch (err) {
        if (err instanceof ServerErrorWithToast) {
          return;
        }
        setError(
          err instanceof Error ? err.message : "Failed to load colleges",
        );
      } finally {
        setLoading(false);
      }
    }

    fetchColleges();
  }, []);

  const handleValueChange = (newValue: string) => {
    if (newValue === "all") {
      onValueChange(undefined);
    } else {
      onValueChange(parseInt(newValue));
    }
  };

  // Calculate the select value - use "all" only if showAllOption is true and value is undefined
  const selectValue = value ? value.toString() : showAllOption ? "all" : "";

  if (error) {
    return (
      <Select disabled>
        <SelectTrigger className={className}>
          <SelectValue placeholder="Error loading colleges" />
        </SelectTrigger>
      </Select>
    );
  }

  return (
    <Select
      value={selectValue}
      onValueChange={handleValueChange}
      disabled={loading}
    >
      <SelectTrigger className={className}>
        <SelectValue
          placeholder={loading ? "Loading colleges..." : placeholder}
        />
      </SelectTrigger>
      <SelectContent>
        {showAllOption && <SelectItem value="all">All Colleges</SelectItem>}
        {colleges.map((college) => (
          <SelectItem key={college.id} value={college.id.toString()}>
            <div className="flex items-center justify-between w-full">
              <span>{college.name}</span>
              {college.shortName && (
                <span className="text-muted-foreground text-xs ml-2">
                  {college.shortName}
                </span>
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
