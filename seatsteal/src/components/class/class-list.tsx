import { ClassCard } from "./class-card";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ClassWithEnrollment } from "@/types/api";

interface ClassListProps {
  classes: ClassWithEnrollment[];
  loading?: boolean;
  error?: string | null;
  showSubscriptionButtons?: boolean;
  subscriptions?: Set<number>; // Set of subscribed class IDs
  subscriptionsLoading?: boolean;
  onSubscriptionChange?: (
    classId: number,
    isSubscribed: boolean,
  ) => Promise<void> | void;
  className?: string;
  // Pro-exclusive: watcher counts per class (how many users are watching each section)
  watcherCounts?: Record<number, number>;
}

export function ClassList({
  classes,
  loading = false,
  error = null,
  showSubscriptionButtons = false,
  subscriptions = new Set(),
  subscriptionsLoading = false,
  onSubscriptionChange,
  className,
  watcherCounts = {},
}: ClassListProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="animate-pulse space-y-2">
                <div className="h-4 bg-muted rounded w-24 mx-auto"></div>
                <div className="h-3 bg-muted rounded w-32 mx-auto"></div>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Loading classes...
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={cn("border-destructive", className)}>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <h3 className="font-medium text-destructive mb-1">
              Error Loading Classes
            </h3>
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Class List */}
      {classes.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
              <h3 className="font-medium mb-1">No Classes Available</h3>
              <p className="text-sm text-muted-foreground">
                This course has no class sections at the moment.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {classes.map((classItem) => (
            <ClassCard
              key={classItem.classId}
              class={classItem}
              showSubscriptionButton={showSubscriptionButtons}
              isSubscribed={subscriptions.has(classItem.classId)}
              subscriptionsLoading={subscriptionsLoading}
              onSubscriptionChange={onSubscriptionChange}
              watcherCount={watcherCounts[classItem.classId]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
