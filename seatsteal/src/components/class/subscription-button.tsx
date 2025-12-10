import { useState } from "react";
import {
  useSession,
  useSubscriptionTier,
  useSubscriptionStatus,
} from "@/components/providers/SessionProvider";
import { useHistory } from "react-router-dom";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Bell, BellOff, AlertCircle, LogIn, ExternalLink } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { SubscribeConfirmationModal } from "@/components/ui/subscribe-confirmation-modal";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { ClassWithEnrollment, SubscriptionRequest } from "@/types/api";
import { getSubscriptionFeatures } from "@/lib/subscription-constants";

interface SubscriptionButtonProps {
  class: ClassWithEnrollment;
  collegeId: number;
  isSubscribed?: boolean;
  onSubscriptionChange?: (classId: number, isSubscribed: boolean) => void;
  size?: "sm" | "default" | "lg";
  variant?: "default" | "outline" | "ghost";
  className?: string;
  showIcon?: boolean;
}

export function SubscriptionButton({
  class: classData,
  collegeId,
  isSubscribed = false,
  onSubscriptionChange,
  size = "default",
  variant = "default",
  className,
  showIcon = true,
}: SubscriptionButtonProps) {
  const { user, loading: sessionLoading } = useSession();
  const { subscriptionTier: userTier } = useSubscriptionTier();
  const { subscriptionStatus, refreshSubscriptionStatus } =
    useSubscriptionStatus();
  const history = useHistory();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [optimisticState, setOptimisticState] = useState(isSubscribed);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const enrollment = classData.currentEnrollment;
  const isOpen = enrollment?.enrollmentStatus.toLowerCase() === "open";
  const isClosed = enrollment?.enrollmentStatus.toLowerCase() === "closed";

  // Check if user has reached subscription limit
  const isAtLimit =
    subscriptionStatus !== null && !subscriptionStatus.canSubscribe;
  const tierFeatures = getSubscriptionFeatures(userTier);

  // Can only subscribe to closed classes, must be authenticated, and not at limit
  const canSubscribe = isClosed && !isOpen && !!user && !isAtLimit;

  const handleSubscriptionToggle = async () => {
    if (loading || sessionLoading) return;

    // If not authenticated and class is closed, redirect to login
    if (!user && isClosed) {
      history.push("/login");
      return;
    }

    if (!canSubscribe) return;

    // If subscribing, show confirmation modal first
    if (!optimisticState) {
      setShowConfirmModal(true);
      return;
    }

    // If unsubscribing, proceed directly
    await performUnsubscribe();
  };

  const performSubscribe = async () => {
    setLoading(true);
    setError(null);
    setShowConfirmModal(false);

    // Optimistic update
    setOptimisticState(true);

    try {
      const request: SubscriptionRequest = {
        classId: classData.classId,
        collegeId,
      };

      const response = await fetchWithToasts("/api/subscriptions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
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

            // Revert optimistic update
            setOptimisticState(isSubscribed);
            return;
          }
        }
        throw new Error("Failed to subscribe");
      }

      // Notify parent component of successful change
      onSubscriptionChange?.(classData.classId, true);

      // Refresh subscription status to update count
      refreshSubscriptionStatus();
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        // Revert optimistic update on error
        setOptimisticState(isSubscribed);
        return; // Toast already shown
      }
      setError(err instanceof Error ? err.message : "An error occurred");

      // Revert optimistic update on error
      setOptimisticState(isSubscribed);
    } finally {
      setLoading(false);
    }
  };

  const performUnsubscribe = async () => {
    setLoading(true);
    setError(null);

    // Optimistic update
    setOptimisticState(false);

    try {
      const response = await fetchWithToasts(
        `/api/subscriptions/${classData.classId}`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error("Failed to unsubscribe");
      }

      // Notify parent component of successful change
      onSubscriptionChange?.(classData.classId, false);

      // Refresh subscription status to update count
      refreshSubscriptionStatus();
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        // Revert optimistic update on error
        setOptimisticState(isSubscribed);
        return; // Toast already shown
      }
      setError(err instanceof Error ? err.message : "An error occurred");

      // Revert optimistic update on error
      setOptimisticState(isSubscribed);
    } finally {
      setLoading(false);
    }
  };

  // Determine button state and styling
  const getButtonContent = () => {
    if (loading || sessionLoading) {
      return (
        <>
          <Spinner
            className={cn(
              showIcon && "mr-2",
              size === "sm" ? "size-3" : "size-4",
            )}
          />
          {loading ? "Processing..." : "Loading..."}
        </>
      );
    }

    if (!user && isClosed) {
      return (
        <>
          {showIcon && (
            <LogIn
              className={cn("mr-2", size === "sm" ? "h-3 w-3" : "h-4 w-4")}
            />
          )}
          Login to Subscribe
        </>
      );
    }

    if (!canSubscribe) {
      return (
        <>
          {showIcon && (
            <Bell
              className={cn("mr-2", size === "sm" ? "h-3 w-3" : "h-4 w-4")}
            />
          )}
          Subscribe
        </>
      );
    }

    if (optimisticState) {
      return (
        <>
          {showIcon && (
            <BellOff
              className={cn("mr-2", size === "sm" ? "h-3 w-3" : "h-4 w-4")}
            />
          )}
          Unsubscribe
        </>
      );
    }

    return (
      <>
        {showIcon && (
          <Bell className={cn("mr-2", size === "sm" ? "h-3 w-3" : "h-4 w-4")} />
        )}
        Subscribe
      </>
    );
  };

  const getButtonVariant = () => {
    if (!user && isClosed) return "default";
    if (!canSubscribe) return "outline";
    if (optimisticState) return "outline"; // Changed from 'destructive' to 'outline'
    return variant;
  };

  // Generate tooltip message for subscription limit
  const getTooltipMessage = () => {
    if (userTier === "pro") {
      return `You've reached your limit of ${tierFeatures.maxSubscriptions} subscriptions`;
    }
    const nextTier = userTier === "free" ? "Plus" : "Pro";
    return `You've reached your limit of ${tierFeatures.maxSubscriptions} subscription${tierFeatures.maxSubscriptions === 1 ? "" : "s"}. Upgrade to ${nextTier} for more!`;
  };

  // Determine if we should show tooltip (at limit, not already subscribed, and user is logged in)
  const showLimitTooltip = isAtLimit && !optimisticState && !!user && isClosed;

  const buttonElement = (
    <Button
      onClick={handleSubscriptionToggle}
      disabled={
        (!canSubscribe && !!user && !optimisticState) ||
        loading ||
        sessionLoading
      }
      size={size}
      variant={getButtonVariant()}
      className={cn(
        "transition-all duration-200",
        !canSubscribe &&
          !!user &&
          !optimisticState &&
          "opacity-60 cursor-not-allowed",
        optimisticState &&
          !loading &&
          "text-destructive hover:text-destructive hover:bg-destructive/10",
        className,
      )}
      aria-label={
        !user && isClosed
          ? "Login required to subscribe"
          : isAtLimit && !optimisticState
            ? getTooltipMessage()
            : !canSubscribe
              ? "Class is open, notifications not available"
              : optimisticState
                ? "Unsubscribe from notifications"
                : "Subscribe to get notified when seats become available"
      }
    >
      {getButtonContent()}
    </Button>
  );

  return (
    <div className="space-y-1">
      {showLimitTooltip ? (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span tabIndex={0}>{buttonElement}</span>
            </TooltipTrigger>
            <TooltipContent>
              <p>{getTooltipMessage()}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        buttonElement
      )}

      {error && (
        <div className="flex items-center gap-1 text-xs text-destructive">
          <AlertCircle className="h-3 w-3" />
          <span>{error}</span>
        </div>
      )}

      {(!canSubscribe || (!user && isClosed)) && !optimisticState && (
        <p className="text-xs text-muted-foreground">
          {!user && isClosed
            ? "Login required to subscribe"
            : isAtLimit
              ? `Limit reached (${subscriptionStatus?.currentCount}/${subscriptionStatus?.maxSubscriptions})`
              : isOpen
                ? "Class is currently open for enrollment"
                : "Notifications not available for this class"}
        </p>
      )}

      <SubscribeConfirmationModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={performSubscribe}
        isLoading={loading}
      />
    </div>
  );
}
