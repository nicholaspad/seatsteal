import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CourseSearch } from "@/components/course/course-search";
import { Search } from "lucide-react";
import { Link } from "react-router-dom";

export function QuickSearch() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Quick Search
        </CardTitle>
        <p className="text-sm text-muted-foreground">Find courses by name</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Search Courses</label>
          <CourseSearch
            placeholder="Search for courses..."
            onValueChange={(query) => {
              if (query.trim()) {
                window.location.href = `/courses?q=${encodeURIComponent(query)}`;
              }
            }}
          />
        </div>

        <div className="pt-2">
          <Button asChild variant="outline" size="sm" className="w-full">
            <Link to="/courses">Get Started</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
