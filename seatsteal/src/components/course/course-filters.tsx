import { useState, useEffect } from "react";
import { useHistory } from "react-router-dom";
import { useSearchParams } from "@/hooks/use-search-params";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CourseSearch } from "@/components/course/course-search";
import type { College } from "@/types/api";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

interface CourseFiltersProps {
  initialValues: {
    q?: string;
    college?: string;
    sort?: string;
  };
}

export function CourseFilters({ initialValues }: CourseFiltersProps) {
  const history = useHistory();
  const searchParams = useSearchParams();
  const [colleges, setColleges] = useState<College[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch colleges for all users
  useEffect(() => {
    fetchColleges();
  }, []);

  const fetchColleges = async () => {
    try {
      setLoading(true);
      const response = await fetchWithToasts("/api/colleges");
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setColleges(data.data);
        }
      }
    } catch (error) {
      if (error instanceof ServerErrorWithToast) {
        return;
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    const current = new URLSearchParams(searchParams.toString());

    if (value) {
      current.set(key, value);
    } else {
      current.delete(key);
    }

    // Reset to page 1 when filters change
    current.delete("page");

    const search = current.toString();
    const query = search ? `?${search}` : "";
    history.push(`/courses${query}`);
  };

  return (
    <Card>
      <CardContent className="space-y-4">
        <div className="space-y-4">
          {/* Search */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Search Courses</label>
            <CourseSearch
              value={initialValues.q || ""}
              onValueChange={(value: string) => handleFilterChange("q", value)}
              placeholder="Search courses..."
            />
            <p className="text-sm text-muted-foreground">
              Courses with no sections are hidden
            </p>
          </div>

          {/* College Filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">College</label>
            <Select
              name="college"
              defaultValue={initialValues.college || "all"}
              onValueChange={(value: string) =>
                handleFilterChange("college", value)
              }
              disabled={loading}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Colleges" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Colleges</SelectItem>
                {colleges.map((college) => (
                  <SelectItem key={college.id} value={college.id.toString()}>
                    {college.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {/* Display term name for selected college */}
            {initialValues.college &&
              initialValues.college !== "all" &&
              (() => {
                const selectedCollege = colleges.find(
                  (college) => college.id.toString() === initialValues.college,
                );
                return (
                  selectedCollege?.termName && (
                    <p className="text-sm text-muted-foreground pl-3">
                      Term: {selectedCollege.termName}
                    </p>
                  )
                );
              })()}
          </div>

          {/* Sort Options */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Sort By</label>
            <Select
              name="sort"
              defaultValue={initialValues.sort || "relevance"}
              onValueChange={(value: string) =>
                handleFilterChange("sort", value)
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="relevance">Relevance</SelectItem>
                <SelectItem value="code">Course Code</SelectItem>
                <SelectItem value="title">Course Title</SelectItem>
                <SelectItem value="college">College</SelectItem>
                <SelectItem value="enrollment">Enrollment Status</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
