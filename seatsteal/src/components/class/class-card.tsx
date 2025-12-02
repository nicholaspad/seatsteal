import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EnrollmentBadge } from "./enrollment-badge";
import { EnrollmentAnalysisModal } from "./enrollment-analysis-modal";
import { SubscribeConfirmationModal } from "@/components/ui/subscribe-confirmation-modal";
import { Bell, Sparkles, ExternalLink } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { useSubscriptionTier } from "@/components/providers/SessionProvider";

type SubscriptionTier = "free" | "plus" | "pro";

// Client-side utility to check premium access without database dependencies
const hasPremiumAccess = (tier: SubscriptionTier): boolean => {
  return tier === "plus" || tier === "pro";
};
import type { ClassWithEnrollment } from "@/types/api";

interface ClassCardProps {
  class: ClassWithEnrollment;
  showSubscriptionButton?: boolean;
  onSubscriptionChange?: (
    classId: number,
    isSubscribed: boolean,
  ) => Promise<void> | void;
  isSubscribed?: boolean;
  subscriptionsLoading?: boolean;
  className?: string;
  showPremiumFeatures?: boolean;
}

export function ClassCard({
  class: classData,
  showSubscriptionButton = false,
  onSubscriptionChange,
  isSubscribed = false,
  subscriptionsLoading = false,
  className,
  showPremiumFeatures = true, // TODO: Set based on user subscription tier
}: ClassCardProps) {
  const [buttonLoading, setButtonLoading] = useState(false);
  const [analysisModalOpen, setAnalysisModalOpen] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const { subscriptionTier: userTier, tierLoading } = useSubscriptionTier();
  const enrollment = classData.currentEnrollment;
  const isOpen = enrollment?.enrollmentStatus.toLowerCase() === "open";
  const isClosed = enrollment?.enrollmentStatus.toLowerCase() === "closed";
  const hasAnalyticsAccess = hasPremiumAccess(userTier);

  const handleSubscriptionClick = async () => {
    if (onSubscriptionChange && !buttonLoading) {
      // Show confirmation modal when subscribing (not unsubscribing)
      if (!isSubscribed) {
        setShowConfirmModal(true);
        return;
      }
      // Proceed directly for unsubscribe
      setButtonLoading(true);
      try {
        await onSubscriptionChange(classData.classId, false);
      } finally {
        setButtonLoading(false);
      }
    }
  };

  const handleConfirmSubscribe = async () => {
    if (onSubscriptionChange && !buttonLoading) {
      setButtonLoading(true);
      setShowConfirmModal(false);
      try {
        await onSubscriptionChange(classData.classId, true);
      } finally {
        setButtonLoading(false);
      }
    }
  };

  return (
    <Card className={cn("transition-shadow duration-200 py-0", className)}>
      <CardHeader
        className={cn("p-6", showSubscriptionButton && isClosed && "pb-0")}
      >
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <div className="flex items-center gap-2 justify-self-start">
            <h3 className="font-semibold text-lg leading-none">
              {classData.sectionCode}
            </h3>
            {classData.classNumber && (
              <Badge variant="outline" className="text-xs flex items-center">
                ID: {classData.classNumber}
              </Badge>
            )}
          </div>

          {/* Premium Enrollment Analysis Button - Always centered */}
          {showPremiumFeatures && (
            <div className="flex items-center justify-self-center">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <Button
                      variant="outline"
                      size="xs"
                      className={cn(
                        "rounded-md",
                        hasAnalyticsAccess
                          ? "hover:bg-gray-50 dark:hover:bg-gray-800"
                          : "cursor-not-allowed opacity-60",
                      )}
                      onClick={() =>
                        hasAnalyticsAccess && setAnalysisModalOpen(true)
                      }
                      disabled={!hasAnalyticsAccess || tierLoading}
                    >
                      <div
                        className={cn(
                          hasAnalyticsAccess
                            ? "gradient-premium-combo"
                            : "text-gray-500 dark:text-gray-400",
                        )}
                      >
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <span className="sr-only">Enrollment analysis</span>
                    </Button>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  {hasAnalyticsAccess ? (
                    "View enrollment analysis"
                  ) : (
                    <div className="space-y-1 text-center">
                      <p className="font-medium">
                        Enrollment Analysis is a premium feature. Subscribe to
                        Plus/Pro to unlock!
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
            </div>
          )}

          <div className="flex justify-self-end">
            <EnrollmentBadge class={classData} />
          </div>
        </div>
      </CardHeader>

      {showSubscriptionButton && isClosed && (
        <CardContent className="pt-0 pb-4 px-4">
          {subscriptionsLoading ? (
            // Single loading skeleton line for entire subscription card
            <div className="h-16 w-full bg-muted rounded-lg animate-pulse" />
          ) : (
            <div className="flex items-center justify-between p-3 rounded-lg border-2 border-primary/20 bg-primary/5">
              <div className="flex items-center gap-3">
                <Bell className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-semibold text-sm">
                    {isSubscribed
                      ? "You're subscribed!"
                      : "Get notified when seats open"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {isClosed
                      ? "We'll alert you when this class becomes available"
                      : "This class is currently open for enrollment"}
                  </p>
                </div>
              </div>

              <button
                onClick={handleSubscriptionClick}
                disabled={isOpen || buttonLoading} // Can't subscribe to open classes or when loading
                className={cn(
                  "px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-200 shadow-sm flex items-center gap-2",
                  isSubscribed
                    ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    : "bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-md",
                  (isOpen || buttonLoading) &&
                    "opacity-60 cursor-not-allowed bg-muted text-muted-foreground",
                )}
                aria-label={
                  buttonLoading
                    ? "Processing subscription request"
                    : isOpen
                      ? "Class is open - notifications not available"
                      : isSubscribed
                        ? "Unsubscribe from notifications"
                        : "Subscribe for notifications"
                }
              >
                {buttonLoading ? (
                  <Spinner className="size-4" />
                ) : (
                  <Bell className="h-4 w-4" />
                )}
                {buttonLoading
                  ? "Processing..."
                  : isOpen
                    ? "Subscribe"
                    : isSubscribed
                      ? "Unsubscribe"
                      : "Subscribe"}
              </button>
            </div>
          )}
        </CardContent>
      )}

      {/* Premium Enrollment Analysis Modal */}
      {showPremiumFeatures && hasAnalyticsAccess && (
        <EnrollmentAnalysisModal
          isOpen={analysisModalOpen}
          onClose={() => setAnalysisModalOpen(false)}
          classData={classData}
        />
      )}

      {/* Subscribe Confirmation Modal */}
      <SubscribeConfirmationModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleConfirmSubscribe}
        isLoading={buttonLoading}
      />
    </Card>
  );
}
