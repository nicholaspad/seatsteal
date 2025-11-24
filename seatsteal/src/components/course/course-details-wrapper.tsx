import { useState, useEffect } from "react";
import { useHistory } from "react-router-dom";
import { useSubscriptionTier, useSession } from "@/components/providers/SessionProvider";
import { CourseDetails } from "@/components/course/course-details";
import { Button } from "@/components/ui/button";
import { UnsubscribeConfirmationModal } from "@/components/ui/unsubscribe-confirmation-modal";
import { ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import type {
  CourseWithClasses,
  SubscriptionsApiResponse,
  SubscriptionWithDetails,
} from "@/types/api";

interface CourseDetailsWrapperProps {
  course: CourseWithClasses;
}

export function CourseDetailsWrapper({ course }: CourseDetailsWrapperProps) {
  const history = useHistory();
  const [mounted, setMounted] = useState(false);
  const { subscriptionTier: userTier } = useSubscriptionTier();
  const { profile } = useSession();
  const [subscriptionsData, setSubscriptionsData] = useState<
    SubscriptionWithDetails[]
  >([]);
  const [subscriptionsLoading, setSubscriptionsLoading] = useState(false);
  const [confirmUnsubscribe, setConfirmUnsubscribe] = useState<{
    classId: number;
    subscription: SubscriptionWithDetails;
  } | null>(null);
  const [unsubscribing, setUnsubscribing] = useState(false);

  // Handle client-side mounting
  useEffect(() => {
    setMounted(true);
  }, []);

  // Convert subscriptions array to Set for easy lookup
  const subscriptions = new Set(subscriptionsData.map((sub) => sub.classId));

  // Fetch user subscriptions - user is guaranteed to exist since route is protected
  useEffect(() => {
    if (!mounted) return;

    const fetchSubscriptions = async () => {
      try {
        setSubscriptionsLoading(true);
        const response = await fetchWithToasts("/api/subscriptions");

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: SubscriptionsApiResponse = await response.json();
        if (data.success) {
          setSubscriptionsData(data.data || []);
        }
      } catch (err) {
        if (err instanceof ServerErrorWithToast) {
          return;
        }
      } finally {
        setSubscriptionsLoading(false);
      }
    };

    fetchSubscriptions();
  }, [mounted]);

  const handleConfirmedUnsubscribe = async (confirmData: {
    classId: number;
    subscription: SubscriptionWithDetails;
  }) => {
    try {
      setUnsubscribing(true);
      const response = await fetchWithToasts(
        `/api/subscriptions/${confirmData.subscription.id}`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error("Failed to unsubscribe");
      }

      setSubscriptionsData((prev) =>
        prev.filter((sub) => sub.classId !== confirmData.classId),
      );

      // Close confirmation modal and show success toast
      setConfirmUnsubscribe(null);
      toast.success("Unsubscribed successfully!");
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      toast.error("Failed to unsubscribe. Please try again.");
    } finally {
      setUnsubscribing(false);
    }
  };

  const handleSubscriptionChange = async (
    classId: number,
    isSubscribed: boolean,
  ) => {
    try {
      if (isSubscribed) {
        // Subscribe
        const response = await fetchWithToasts("/api/subscriptions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ classId, collegeId: course.college.id }),
        });

        if (!response.ok) {
          // Check if this is a subscription limit error
          if (response.status === 400) {
            const errorData = await response.json();
            const errorMessage =
              errorData.error || errorData.message || "Failed to subscribe";

            // Check if the error message contains subscription limit information
            if (errorMessage.includes("subscription limit")) {
              // Customize message based on user's current tier
              let upgradeMessage = "";
              let showUpgradeButton = true;

              if (userTier === "free") {
                upgradeMessage = "Upgrade to Plus/Pro for more!";
              } else if (userTier === "plus") {
                upgradeMessage = "Upgrade to Pro for more!";
              } else if (userTier === "pro") {
                upgradeMessage = "";
                showUpgradeButton = false;
              }

              // Show custom toast with tier-specific upgrade message
              toast.error(
                <div className="space-y-2">
                  <p className="font-medium text-sm">
                    You've reached your subscription limit. {upgradeMessage}
                  </p>
                  {showUpgradeButton && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-1 text-xs"
                      onClick={() => window.open("/#pricing", "_blank")}
                    >
                      View pricing <ExternalLink className="ml-1 h-3 w-3" />
                    </Button>
                  )}
                </div>,
                {
                  duration: 5000,
                },
              );
              return;
            }
          }
          throw new Error("Failed to subscribe");
        }

        const data = await response.json();
        if (data.success) {
          setSubscriptionsData((prev) => [...prev, data.data]);
          toast.success("You'll be notified when seats become available!");
        }
      } else {
        // Find subscription to delete and show confirmation modal
        const subscription = subscriptionsData.find(
          (sub) => sub.classId === classId,
        );
        if (subscription) {
          setConfirmUnsubscribe({
            classId,
            subscription,
          });
        }
      }
    } catch (error) {
      if (error instanceof ServerErrorWithToast) {
        return;
      }
      toast.error("Failed to update subscription. Please try again.");
    }
  };

  const handleBack = () => {
    // Navigate back to courses with college ID if available
    const coursesPath = profile?.collegeId
      ? `/courses?college=${profile.collegeId}`
      : "/courses";
    history.push(coursesPath);
  };

  // Show loading state during SSR/hydration
  if (!mounted) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-muted rounded w-1/3"></div>
            <div className="h-4 bg-muted rounded w-1/2"></div>
            <div className="space-y-2">
              <div className="h-3 bg-muted rounded"></div>
              <div className="h-3 bg-muted rounded w-2/3"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Confirmation Modal */}
      {confirmUnsubscribe && (
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={() => setConfirmUnsubscribe(null)}
          onConfirm={() => handleConfirmedUnsubscribe(confirmUnsubscribe)}
          isLoading={unsubscribing}
        />
      )}

      <div className="container mx-auto px-4 py-8">
        <CourseDetails
          courseId={course.id}
          course={course}
          error={null}
          subscriptions={subscriptions}
          subscriptionsLoading={subscriptionsLoading}
          onSubscriptionChange={handleSubscriptionChange}
          onBack={handleBack}
          collegeId={profile?.collegeId}
        />
      </div>
    </>
  );
}
