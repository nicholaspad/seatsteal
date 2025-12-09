import { useState, useEffect, useMemo, useCallback, memo } from "react";
import { useSession } from "@/components/providers/SessionProvider";
import { Link } from "react-router-dom";
import { Pagination } from "@/components/layout/Pagination";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BellOff,
  BookOpen,
  Users,
  Settings,
  Calendar,
  ExternalLink,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { CollegeBadge } from "@/components/college/CollegeBadge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { UnsubscribeConfirmationModal } from "@/components/ui/unsubscribe-confirmation-modal";
import { formatLocalDate } from "@/lib/date-utils";
import { isValidStripeUrl } from "@/lib/security";
import type {
  SubscriptionWithDetails,
  SubscriptionsApiResponse,
} from "@/types/api";

interface UserDashboardProps {
  className?: string;
  title?: string;
  showHeader?: boolean;
  itemsPerPage?: number;
  userTier?: "free" | "plus" | "pro";
}

type FilterType = "all" | "open" | "closed" | "recent";
type SortType = "date" | "course" | "status" | "notified";

// Helper function to format date labels for the trends graph
const formatTrendLabel = (dateString: string): string => {
  const [year, month, day] = dateString.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const dateOnly = new Date(date);
  dateOnly.setHours(0, 0, 0, 0);

  if (dateOnly.getTime() === today.getTime()) {
    return "Today";
  } else if (dateOnly.getTime() === yesterday.getTime()) {
    return "Yesterday";
  } else {
    // Format as MM/D
    return `${date.getMonth() + 1}/${date.getDate()}`;
  }
};

const UserDashboard = memo(function UserDashboard({
  className,
  title = "My Subscriptions",
  showHeader = true,
  itemsPerPage = 10,
  userTier = "free",
}: UserDashboardProps) {
  const { user, profile } = useSession();
  const [subscriptions, setSubscriptions] = useState<SubscriptionWithDetails[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [sort, setSort] = useState<SortType>("date");
  const [currentPage, setCurrentPage] = useState(1);
  const [hoveredTrendDay, setHoveredTrendDay] = useState<string | null>(null);
  const [weeklyTrend, setWeeklyTrend] = useState<
    Array<{
      date: string;
      notifications: number;
      courses: string[];
    }>
  >([]);
  const [confirmUnsubscribe, setConfirmUnsubscribe] =
    useState<SubscriptionWithDetails | null>(null);
  const [unsubscribing, setUnsubscribing] = useState(false);
  const [managingSubscription, setManagingSubscription] = useState(false);

  const fetchSubscriptions = useCallback(async () => {
    if (!user) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithToasts("/api/subscriptions");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: SubscriptionsApiResponse = await response.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to fetch subscriptions");
      }

      setSubscriptions(data.data || []);
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError(
        err instanceof Error ? err.message : "Failed to load subscriptions",
      );
    } finally {
      setLoading(false);
    }
  }, [user]);

  const fetchWeeklyTrends = useCallback(async () => {
    if (!user) return;

    try {
      const response = await fetchWithToasts("/api/notifications/trends");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setWeeklyTrend(data.data || []);
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      // Set empty array on error - backend always returns 7 days of data
      setWeeklyTrend([]);
    }
  }, [user]);

  // Fetch user subscriptions and trends
  useEffect(() => {
    fetchSubscriptions();
    fetchWeeklyTrends();
  }, [fetchSubscriptions, fetchWeeklyTrends]);

  // Handle manage subscription
  const handleManageSubscription = async () => {
    try {
      setManagingSubscription(true);
      const response = await fetchWithToasts(
        "/api/stripe/create-portal-session",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

      if (!response.ok) {
        // Check for no Stripe customer error (404)
        if (response.status === 404) {
          try {
            const errorData = await response.json();
            // Check if this is the specific "no customer" error
            if (errorData.detail?.code === "NO_STRIPE_CUSTOMER") {
              // Show custom toast with pricing link
              toast.error(
                <div className="space-y-2">
                  <p className="font-medium text-sm">
                    Customer not found. Subscribe to get started!
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-1 text-xs"
                    onClick={() => window.open("/#pricing", "_blank")}
                  >
                    View plans <ExternalLink className="ml-1 h-3 w-3" />
                  </Button>
                </div>,
                {
                  duration: 5000,
                },
              );
              return;
            }
          } catch (parseError) {
            // If JSON parsing fails, fall through to generic error
          }
        }
        throw new Error("Failed to create portal session");
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to create portal session");
      }

      // Validate Stripe URL before redirecting to prevent phishing
      const sessionUrl = data.data.sessionUrl;
      if (!isValidStripeUrl(sessionUrl)) {
        throw new Error("Invalid portal session URL");
      }

      // Redirect to Stripe customer portal
      window.location.href = sessionUrl;
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      toast.error(
        err instanceof Error
          ? err.message
          : "Failed to open billing portal. Please try again.",
      );
    } finally {
      setManagingSubscription(false);
    }
  };

  // Handle unsubscribe
  const handleUnsubscribe = async (subscription: SubscriptionWithDetails) => {
    try {
      setUnsubscribing(true);
      const response = await fetchWithToasts(
        `/api/subscriptions/${subscription.id}`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error("Failed to unsubscribe");
      }

      // Remove from local state
      setSubscriptions((prev) =>
        prev.filter((sub) => sub.id !== subscription.id),
      );

      // Close confirmation modal and show success toast
      setConfirmUnsubscribe(null);
      toast.success("Unsubscribed successfully!");
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      toast.error("Failed to unsubscribe. Please try again.");
    } finally {
      setUnsubscribing(false);
    }
  };

  // Filter and sort subscriptions
  const filteredAndSortedSubscriptions = useMemo(() => {
    let filtered = [...subscriptions];

    // Apply filter
    if (filter !== "all") {
      filtered = filtered.filter((sub) => {
        const status =
          sub.class.currentEnrollment?.enrollmentStatus.toLowerCase();
        if (filter === "open") return status === "open";
        if (filter === "closed") return status === "closed";
        if (filter === "recent")
          return (
            sub.lastNotified &&
            new Date(sub.lastNotified).getTime() >
              Date.now() - 7 * 24 * 60 * 60 * 1000
          );
        return true;
      });
    }

    // Apply sort
    filtered.sort((a, b) => {
      if (sort === "date") {
        return (
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
      }
      if (sort === "course") {
        return a.class.course.courseCode.localeCompare(
          b.class.course.courseCode,
        );
      }
      if (sort === "status") {
        const statusA = a.class.currentEnrollment?.enrollmentStatus || "";
        const statusB = b.class.currentEnrollment?.enrollmentStatus || "";
        return statusA.localeCompare(statusB);
      }
      if (sort === "notified") {
        const dateA = a.lastNotified ? new Date(a.lastNotified).getTime() : 0;
        const dateB = b.lastNotified ? new Date(b.lastNotified).getTime() : 0;
        return dateB - dateA;
      }
      return 0;
    });

    return filtered;
  }, [subscriptions, filter, sort]);

  // Memoized pagination calculations
  const { totalPages, paginatedSubscriptions } = useMemo(() => {
    const pages = Math.ceil(
      filteredAndSortedSubscriptions.length / itemsPerPage,
    );
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;

    return {
      totalPages: pages,
      paginatedSubscriptions: filteredAndSortedSubscriptions.slice(
        startIndex,
        endIndex,
      ),
    };
  }, [filteredAndSortedSubscriptions, currentPage, itemsPerPage]);

  if (loading) {
    return (
      <div className={cn("space-y-6", className)}>
        <Card>
          <CardContent className="pt-6">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-muted rounded w-1/4"></div>
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-20 bg-muted rounded"></div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <Card className={cn("border-destructive", className)}>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <h3 className="font-medium text-destructive mb-1">
              Error Loading Dashboard
            </h3>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchSubscriptions}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      {/* Confirmation Modal */}
      {confirmUnsubscribe && (
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={() => setConfirmUnsubscribe(null)}
          onConfirm={() => handleUnsubscribe(confirmUnsubscribe)}
          isLoading={unsubscribing}
        />
      )}

      <div className={cn("grid grid-cols-1 lg:grid-cols-4 gap-6", className)}>
        {/* Left Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* User Summary */}
          <Card>
            <CardContent className="pt-0 space-y-4">
              {/* Tier Badge with Manage Link */}
              <div className="flex items-center justify-between">
                <Badge
                  variant={userTier as "free" | "plus" | "pro"}
                  className="capitalize"
                >
                  {userTier}
                </Badge>
                {
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleManageSubscription}
                    disabled={managingSubscription}
                    className="h-auto py-1 px-2 text-xs text-muted-foreground hover:text-foreground"
                  >
                    {managingSubscription ? (
                      <>
                        <Spinner className="size-3 mr-1" />
                        Loading...
                      </>
                    ) : (
                      <>
                        Manage
                        <ExternalLink className="h-3 w-3 ml-1" />
                      </>
                    )}
                  </Button>
                }
              </div>

              <Button variant="outline" className="w-full" asChild>
                <Link to="/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  Account
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Filters */}
          <Card>
            <CardContent className="pt-0 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Show</label>
                <Select
                  value={filter}
                  onValueChange={(value: string) =>
                    setFilter(value as FilterType)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Subscriptions</SelectItem>
                    <SelectItem value="open">Now Open</SelectItem>
                    <SelectItem value="closed">Still Closed</SelectItem>
                    <SelectItem value="recent">Recently Notified</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Sort by</label>
                <Select
                  value={sort}
                  onValueChange={(value: string) => setSort(value as SortType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="date">Date Added</SelectItem>
                    <SelectItem value="course">Course Code</SelectItem>
                    <SelectItem value="status">Status</SelectItem>
                    <SelectItem value="notified">Last Notified</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Header */}
          {showHeader && (
            // <div className="flex items-center justify-between">
            //   <div className="text-center space-y-2">
            //     <h1 className="text-2xl font-bold">{title}</h1>
            //     <p className="text-muted-foreground">
            //       Showing {paginatedSubscriptions.length} of{" "}
            //       {filteredAndSortedSubscriptions.length} subscriptions
            //     </p>
            //   </div>
            // </div>

            <div className="text-center space-y-2">
              <h1 className="text-2xl font-bold">{title}</h1>
              <p className="text-muted-foreground">
                Showing {paginatedSubscriptions.length} of{" "}
                {filteredAndSortedSubscriptions.length} subscriptions
              </p>
            </div>
          )}

          {/* Weekly Notifications Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Past 7 Days Notifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end justify-between h-32 gap-2 relative">
                {weeklyTrend.map((day) => {
                  const label = formatTrendLabel(day.date);
                  return (
                    <div
                      key={day.date}
                      className="flex flex-col items-center flex-1 relative"
                    >
                      <div
                        className="flex flex-col items-center justify-end h-24 w-full cursor-pointer"
                        onMouseEnter={() => setHoveredTrendDay(day.date)}
                        onMouseLeave={() => setHoveredTrendDay(null)}
                      >
                        <div
                          className="bg-primary/80 rounded-t w-full transition-all hover:bg-primary"
                          style={{
                            height: `${day.notifications > 0 ? Math.max((day.notifications / 4) * 100, 10) : 0}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground mt-2">
                        {label}
                      </span>
                      <span className="text-xs font-medium">
                        {day.notifications}
                      </span>

                      {/* Tooltip */}
                      {hoveredTrendDay === day.date &&
                        day.notifications > 0 && (
                          <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-popover text-popover-foreground p-2 rounded-md shadow-lg border z-10 min-w-max">
                            <div className="text-xs font-medium mb-1">
                              {day.notifications} notification
                              {day.notifications !== 1 ? "s" : ""}
                            </div>
                            <div className="text-xs text-muted-foreground space-y-1">
                              {day.courses.map((course, index) => (
                                <div key={index}>{course}</div>
                              ))}
                            </div>
                          </div>
                        )}
                    </div>
                  );
                })}
              </div>
              <div className="text-center mt-4">
                {weeklyTrend.reduce((sum, day) => sum + day.notifications, 0) >
                0 ? (
                  <p className="text-sm text-muted-foreground">
                    Total notifications in the past 7 days:{" "}
                    {weeklyTrend.reduce(
                      (sum, day) => sum + day.notifications,
                      0,
                    )}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No notifications in the past 7 days.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Subscriptions List */}
          {paginatedSubscriptions.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-12">
                  {subscriptions.length === 0 ? (
                    <>
                      <BellOff className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                      <h3 className="text-lg font-medium pb-2">
                        No Subscriptions Yet
                      </h3>
                      <Button
                        className="bg-white text-black hover:bg-white/90 px-6"
                        asChild
                      >
                        <Link
                          to={
                            profile?.collegeId
                              ? `/courses?college=${profile.collegeId}`
                              : "/courses"
                          }
                        >
                          <BookOpen className="mr-2 h-4 w-4" />
                          Browse Courses
                        </Link>
                      </Button>
                    </>
                  ) : (
                    <>
                      <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                      <h3 className="font-medium mb-1">
                        No Subscriptions Match Filter
                      </h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        Try adjusting your filter to see more subscriptions.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setFilter("all")}
                      >
                        Show All Subscriptions
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {paginatedSubscriptions.map((subscription) => (
                <Card key={subscription.id}>
                  <CardContent>
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-3">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-lg">
                            {subscription.class.course.courseCode}
                          </h3>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 px-1 text-xs text-muted-foreground hover:text-foreground"
                            asChild
                          >
                            <Link
                              to={`/courses/${subscription.class.course.id}`}
                            >
                              <ExternalLink className="h-3 w-3" />
                            </Link>
                          </Button>
                          {subscription.class.sectionCode && (
                            <Badge variant="outline" className="text-xs">
                              {subscription.class.sectionCode}
                            </Badge>
                          )}
                          <CollegeBadge
                            college={subscription.class.course.college}
                            className="text-xs"
                          />
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">
                          {subscription.class.course.title}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span>
                            Subscribed:{" "}
                            {formatLocalDate(subscription.createdAt)}
                          </span>
                          {subscription.lastNotified && (
                            <>
                              <span>•</span>
                              <span>
                                Last notified:{" "}
                                {formatLocalDate(subscription.lastNotified)}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setConfirmUnsubscribe(subscription)}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        Unsubscribe
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                showFirstLast={true}
              />
            </div>
          )}
        </div>
      </div>
    </>
  );
});

export { UserDashboard };
