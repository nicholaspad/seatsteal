import { memo, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EnrollmentBadge } from "@/components/class/enrollment-badge";
import { CollegeBadge } from "@/components/college/CollegeBadge";
import { CourseSummaryModal } from "@/components/course/course-summary-modal";
import { Users, ArrowRight, Sparkles, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSubscriptionTier } from "@/components/providers/SessionProvider";
import type { CourseWithCollege, ClassWithEnrollment } from "@/types/api";

type SubscriptionTier = "free" | "plus" | "pro";

// Client-side utility to check premium access without database dependencies
const hasPremiumAccess = (tier: SubscriptionTier): boolean => {
  return tier === "plus" || tier === "pro";
};

interface CourseCardProps {
  course: CourseWithCollege;
  classes?: ClassWithEnrollment[];
  className?: string;
  showClassDetails?: boolean;
  showPremiumFeatures?: boolean;
}

const CourseCard = memo(function CourseCard({
  course,
  classes = [],
  className,
  showClassDetails = true,
  showPremiumFeatures = true,
}: CourseCardProps) {
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);

  const { subscriptionTier: userTier, tierLoading } = useSubscriptionTier();
  const hasSummaryAccess = hasPremiumAccess(userTier);
  // Memoized enrollment status calculations
  const { openClasses, closedClasses, totalClasses } = useMemo(() => {
    const open = classes.filter(
      (c) => c.currentEnrollment?.enrollmentStatus.toLowerCase() === "open",
    ).length;
    const closed = classes.filter(
      (c) => c.currentEnrollment?.enrollmentStatus.toLowerCase() === "closed",
    ).length;
    return {
      openClasses: open,
      closedClasses: closed,
      totalClasses: classes.length,
    };
  }, [classes]);

  return (
    <Card
      className={cn(
        "hover:shadow-md transition-shadow duration-200 flex flex-col",
        className,
      )}
    >
      <CardHeader className="pb-3">
        <div className="space-y-1 overflow-hidden">
          <div className="flex items-center gap-2">
            <CollegeBadge college={course.college} />
            <h3 className="font-semibold text-lg leading-none tracking-tight">
              {course.title}
            </h3>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">
            {course.courseCode}
          </p>
        </div>
      </CardHeader>

      {showClassDetails && totalClasses > 0 && (
        <CardContent className="pt-0 pb-3 flex-1">
          <div className="space-y-3">
            {/* Enrollment summary */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">
                  {totalClasses} section{totalClasses !== 1 ? "s" : ""}
                </span>
              </div>

              {openClasses > 0 && (
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span className="text-green-700">{openClasses} open</span>
                </div>
              )}

              {closedClasses > 0 && (
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                  <span className="text-red-700">{closedClasses} closed</span>
                </div>
              )}
            </div>

            {/* Class sections preview (first 2) */}
            <div className="space-y-2 min-h-[6rem]">
              {classes.slice(0, 2).map((classItem) => (
                <div
                  key={classItem.classId}
                  className="flex items-center justify-between p-2 rounded-md bg-muted/50"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {classItem.sectionCode}
                    </span>
                    {classItem.classNumber && (
                      <span className="text-xs text-muted-foreground">
                        • {classItem.classNumber}
                      </span>
                    )}
                  </div>

                  <EnrollmentBadge class={classItem} />
                </div>
              ))}

              {classes.length > 2 && (
                <div className="text-center">
                  <span className="text-xs text-muted-foreground">
                    +{classes.length - 2} more section
                    {classes.length - 2 !== 1 ? "s" : ""}
                  </span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      )}

      {/* Class sections summary */}
      {showClassDetails && totalClasses === 0 && (
        <CardContent className="pt-0 pb-3 flex-1">
          <div className="text-center py-4 text-muted-foreground">
            <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">
              {openClasses} Open, {closedClasses} Closed
            </p>
          </div>
        </CardContent>
      )}

      {/* Spacer when no class details are shown */}
      {!showClassDetails && <div className="flex-1" />}

      <CardFooter className="pt-3">
        <div className="flex gap-2 w-full">
          {/* Premium Summary button - Icon only, first position */}
          {showPremiumFeatures && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Button
                    variant="outline"
                    size="sm"
                    className={cn(
                      "rounded-md",
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
                        hasSummaryAccess
                          ? "gradient-premium-combo"
                          : "text-gray-500 dark:text-gray-400",
                      )}
                    >
                      <Sparkles className="h-4 w-4" />
                    </div>
                  </Button>
                </div>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                {hasSummaryAccess ? (
                  "View subscriptions and notifications summary"
                ) : (
                  <div className="space-y-1 text-center">
                    <p className="font-medium">
                      Course Summary is a premium feature. Subscribe to Plus/Pro
                      to unlock!
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-1 text-xs"
                      onClick={() => window.open("/#pricing", "_blank")}
                    >
                      View pricing <ExternalLink className="ml-1 h-3 w-3" />
                    </Button>
                  </div>
                )}
              </TooltipContent>
            </Tooltip>
          )}

          {/* Classes Button */}
          <Button asChild variant="outline" size="sm" className="flex-1">
            <Link to={`/courses/${course.id}`}>
              Classes
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </CardFooter>

      {/* Premium Course Summary Modal */}
      {showPremiumFeatures && hasSummaryAccess && (
        <CourseSummaryModal
          isOpen={summaryModalOpen}
          onClose={() => setSummaryModalOpen(false)}
          course={course}
        />
      )}
    </Card>
  );
});

export { CourseCard };
