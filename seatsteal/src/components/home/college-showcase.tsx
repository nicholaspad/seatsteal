import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Users } from "lucide-react";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

interface College {
  id: number;
  name: string;
  shortName: string;
  domain: string | null;
  isActive: boolean;
}

export function CollegeShowcase() {
  const [colleges, setColleges] = useState<College[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchColleges = async () => {
      try {
        const response = await fetchWithToasts("/api/colleges");
        if (!response.ok) {
          throw new Error("Failed to fetch colleges");
        }
        const data = await response.json();
        if (data.success) {
          // Show first 6 active colleges
          setColleges((data.data || []).slice(0, 6));
        } else {
          throw new Error(data.error || "Failed to load colleges");
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
    };

    fetchColleges();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Supported Colleges
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Track courses across these universities
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Supported Colleges
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-sm">Unable to load colleges</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          Supported Colleges
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Track courses across these universities
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {colleges.map((college) => (
            <div
              key={college.id}
              className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                  <Building2 className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-sm">{college.shortName}</p>
                  <p className="text-xs text-muted-foreground">
                    {college.name}
                  </p>
                </div>
              </div>
              <Badge variant="secondary" className="text-xs">
                Active
              </Badge>
            </div>
          ))}
        </div>

        <div className="pt-2 space-y-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Users className="h-4 w-4" />
            <span>Join thousands of students tracking courses</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
