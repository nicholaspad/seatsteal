import { useState, useEffect, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { ClassList } from "@/components/class/class-list";
import {
  ClassSectionsHeader,
  type FilterType,
} from "@/components/class/class-sections-header";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  BookOpen,
  Clock,
  ArrowLeft,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { CourseSummaryModal } from "@/components/course/course-summary-modal";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useSubscriptionTier } from "@/components/providers/SessionProvider";
import { formatLocalDateTimeWithAt } from "@/lib/date-utils";
import type { CourseWithClasses } from "@/types/api";

interface CourseDetailsProps {
  courseId: number;
  course?: CourseWithClasses;
  loading?: boolean;
  error?: string | null;
  subscriptions?: Set<number>;
  subscriptionsLoading?: boolean;
  onSubscriptionChange?: (
    classId: number,
    isSubscribed: boolean,
  ) => Promise<void> | void;
  onBack?: () => void;
  className?: string;
  collegeId?: number;
}

export function CourseDetails({
  courseId,
  course,
  loading = false,
  error = null,
  subscriptions = new Set(),
  subscriptionsLoading = false,
  onSubscriptionChange,
  onBack,
  className,
  collegeId,
}: CourseDetailsProps) {
  const [localCourse, setLocalCourse] = useState<CourseWithClasses | null>(
    course || null,
  );
  const [localLoading, setLocalLoading] = useState(loading);
  const [localError, setLocalError] = useState<string | null>(error);
  const [filter, setFilter] = useState<FilterType>("all");
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);

  const { subscriptionTier: userTier, tierLoading } = useSubscriptionTier();

  // Client-side utility to check premium access without database dependencies
  const hasPremiumAccess = (tier: string): boolean => {
    return tier === "plus" || tier === "pro";
  };

  const hasSummaryAccess = hasPremiumAccess(userTier);

  const fetchCourseData = useCallback(async () => {
    try {
      setLocalLoading(true);
      setLocalError(null);

      const response = await fetchWithToasts(`/api/courses/${courseId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to fetch course details");
      }

      setLocalCourse(data.data);
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      setLocalError(
        err instanceof Error ? err.message : "Failed to load course",
      );
    } finally {
      setLocalLoading(false);
    }
  }, [courseId]);

  // Fetch course data if not provided
  useEffect(() => {
    if (!course && courseId) {
      fetchCourseData();
    }
  }, [courseId, course, fetchCourseData]);

  // Filter classes
  const filteredClasses = useMemo(() => {
    if (!localCourse?.classes) return [];

    let filtered = [...localCourse.classes];

    // Apply filter
    if (filter !== "all") {
      filtered = filtered.filter((classItem) => {
        const status =
          classItem.currentEnrollment?.enrollmentStatus.toLowerCase();
        if (filter === "open") return status === "open";
        if (filter === "closed") return status === "closed";
        return true;
      });
    }

    // Sort by class number (default)
    filtered.sort((a, b) => a.classNumber.localeCompare(b.classNumber));

    return filtered;
  }, [localCourse?.classes, filter]);

  // Format the last scraper update time
  const lastScraperUpdate = localCourse?.lastScraperUpdate
    ? new Date(localCourse.lastScraperUpdate)
    : null;

  if (localLoading) {
    return (
      <div className={cn("space-y-6", className)}>
        <Card>
          <CardContent className="pt-6">
            <div className="animate-pulse space-y-4">
              <div className="h-8 bg-muted rounded w-1/3"></div>
              <div className="h-4 bg-muted rounded w-1/2"></div>
              <div className="space-y-2">
                <div className="h-3 bg-muted rounded"></div>
                <div className="h-3 bg-muted rounded w-2/3"></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (localError) {
    return (
      <Card className={cn("border-destructive", className)}>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <h3 className="font-medium text-destructive mb-1">
              Error Loading Course
            </h3>
            <p className="text-sm text-muted-foreground mb-4">{localError}</p>
            <div className="flex gap-2 justify-center">
              <Button variant="outline" size="sm" onClick={fetchCourseData}>
                Try Again
              </Button>
              {onBack && (
                <Button variant="ghost" size="sm" onClick={onBack}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Go Back
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!localCourse) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <h3 className="font-medium mb-1">Course Not Found</h3>
            <p className="text-sm text-muted-foreground">
              The requested course could not be found.
            </p>
            {onBack && (
              <Button
                variant="outline"
                size="sm"
                onClick={onBack}
                className="mt-4"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Go Back
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Breadcrumb Navigation */}
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/">Home</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to={collegeId ? `/courses?college=${collegeId}` : "/courses"}>
                Courses
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{localCourse.courseCode}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Back Button */}
      {onBack && (
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Courses
        </Button>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Course Info Sidebar */}
        <div className="lg:col-span-1">
          <div className="sticky top-8">
            <Card className="py-0">
              <CardHeader className="space-y-4 p-6">
                <div className="space-y-2">
                  <h1 className="text-2xl font-bold break-words leading-none pb-2">
                    {localCourse.title}
                  </h1>

                  <h2 className="text-base text-muted-foreground font-medium line-clamp-2 break-all leading-none mb-2">
                    {localCourse.courseCode}
                  </h2>
                </div>

                {/* Premium Summary Button Section */}
                <div className="flex items-center justify-center">
                  {/* Premium Summary Button with Gradient Border */}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="w-full">
                        <Button
                          variant="outline"
                          size="sm"
                          className={cn(
                            "justify-center w-full rounded-md",
                            hasSummaryAccess
                              ? "hover:bg-gray-50 dark:hover:bg-gray-800"
                              : "cursor-not-allowed opacity-60",
                          )}
                          onClick={() =>
                            hasSummaryAccess && setSummaryModalOpen(true)
                          }
                          disabled={!hasSummaryAccess || tierLoading}
                        >
                          <div
                            className={cn(
                              "flex items-center",
                              hasSummaryAccess
                                ? "gradient-premium-combo"
                                : "text-gray-500 dark:text-gray-400",
                            )}
                          >
                            <Sparkles className="mr-2 h-4 w-4" />
                            <span>Summary</span>
                          </div>
                        </Button>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-xs">
                      {hasSummaryAccess ? (
                        "View subscriptions and notifications summary"
                      ) : (
                        <div className="space-y-1 text-center">
                          <p className="font-medium">
                            Course Summary is a premium feature. Subscribe to
                            Plus/Pro to unlock!
                          </p>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-auto p-1 text-xs"
                            onClick={() => window.open("/#pricing", "_blank")}
                          >
                            View pricing{" "}
                            <ExternalLink className="ml-1 h-3 w-3" />
                          </Button>
                        </div>
                      )}
                    </TooltipContent>
                  </Tooltip>
                </div>

                {/* Class Sections Header */}
                {localCourse.classes && localCourse.classes.length > 0 && (
                  <div className="border-t pt-4">
                    <ClassSectionsHeader
                      classes={localCourse.classes}
                      filter={filter}
                      onFilterChange={setFilter}
                      filteredCount={filteredClasses.length}
                    />
                  </div>
                )}
              </CardHeader>
            </Card>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Class Sections */}
          <ClassList
            classes={filteredClasses}
            showSubscriptionButtons={true}
            subscriptions={subscriptions}
            subscriptionsLoading={subscriptionsLoading}
            onSubscriptionChange={onSubscriptionChange}
          />

          {/* Footer Info */}
          <Card className="py-0">
            <CardContent className="p-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-4">
                  <span>College: {localCourse.college.name}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>
                    {lastScraperUpdate ? (
                      <>
                        Last updated:{" "}
                        {formatLocalDateTimeWithAt(lastScraperUpdate)}
                      </>
                    ) : (
                      "Last update time unavailable"
                    )}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Course Summary Modal */}
      {hasSummaryAccess && (
        <CourseSummaryModal
          isOpen={summaryModalOpen}
          onClose={() => setSummaryModalOpen(false)}
          course={localCourse}
        />
      )}
    </div>
  );
}
