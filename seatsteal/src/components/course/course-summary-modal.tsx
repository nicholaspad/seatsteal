import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Loader2,
  Users,
  Bell,
  BookOpen,
  TrendingUp,
} from "lucide-react";
import { fetchWithToasts } from "@/lib/api";
import type { CourseWithCollege } from "@/types/api";

interface CourseSummaryData {
  courseId: number;
  totalSubscriptions: number;
  classesWithSubscriptions: number;
  uniqueSubscribedUsers: number;
  totalNotificationsSent: number;
  totalClasses: number;
  generatedAt: string;
}

interface CourseSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  course: CourseWithCollege;
}

export function CourseSummaryModal({
  isOpen,
  onClose,
  course,
}: CourseSummaryModalProps) {
  const [summaryData, setSummaryData] = useState<CourseSummaryData | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummaryData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithToasts(
        `/api/courses/${course.id}/summary`,
      );

      if (!response.ok) {
        throw new Error("Failed to fetch course summary data");
      }

      const apiResponse = await response.json();
      const data = apiResponse.data || apiResponse;
      setSummaryData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [course.id]);

  useEffect(() => {
    if (isOpen && course.id) {
      fetchSummaryData();
    }
  }, [isOpen, course.id, fetchSummaryData]);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Course Summary - {course.courseCode}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-2">Loading summary...</span>
            </div>
          )}

          {error && (
            <div className="text-center py-8 text-red-600">
              <p>Error: {error}</p>
              <Button onClick={fetchSummaryData} className="mt-2">
                Retry
              </Button>
            </div>
          )}

          {summaryData ? (
            <>
              {/* Course Overview */}
              <Card>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">
                        Course Title:
                      </span>
                      <p className="font-medium">{course.title}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">College:</span>
                      <p className="font-medium">{course.college.name}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Statistics Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Total Subscriptions */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">
                        {summaryData.totalSubscriptions}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Bell className="h-3 w-3" />
                        Total subscriptions
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Classes with Subscriptions */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {summaryData.classesWithSubscriptions}
                        <span className="text-sm text-muted-foreground">
                          /{summaryData.totalClasses}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <BookOpen className="h-3 w-3" />
                        Classes with subscriptions
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Unique Subscribed Users */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">
                        {summaryData.uniqueSubscribedUsers}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Users className="h-3 w-3" />
                        Subscribed users
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Total Notifications */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">
                        {summaryData.totalNotificationsSent}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <TrendingUp className="h-3 w-3" />
                        Notifications sent
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : (
            !loading &&
            !error && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
                  <Sparkles className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  No Summary Available
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Summary will become available as subscription data is
                  collected over time.
                </p>
              </div>
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
