import { IonContent, IonPage } from "@ionic/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DashboardSkeleton() {
  return (
    <IonPage>
      <IonContent>
        <div className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Left Sidebar Skeleton */}
            <div className="lg:col-span-1 space-y-6">
              {/* User Summary Card */}
              <Card>
                <CardContent className="pt-0 space-y-4">
                  <div className="flex items-center justify-between">
                    <Skeleton className="h-6 w-16" />
                    <Skeleton className="h-8 w-20" />
                  </div>
                  <Skeleton className="h-10 w-full" />
                </CardContent>
              </Card>

              {/* Filters Card */}
              <Card>
                <CardContent className="pt-0 space-y-4">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Main Content Skeleton */}
            <div className="lg:col-span-3 space-y-6">
              {/* Header */}
              <div className="text-center space-y-2">
                <Skeleton className="h-8 w-48 mx-auto" />
                <Skeleton className="h-5 w-64 mx-auto" />
              </div>

              {/* Weekly Trends Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Skeleton className="h-5 w-5" />
                    <Skeleton className="h-6 w-48" />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {/* Bar chart skeleton */}
                  <div className="flex items-end justify-between h-32 gap-2">
                    {Array.from({ length: 7 }, (_, i) => (
                      <div
                        key={i}
                        className="flex flex-col items-center flex-1"
                      >
                        <Skeleton
                          className="w-full rounded-t"
                          style={{ height: `${Math.random() * 60 + 20}%` }}
                        />
                        <Skeleton className="h-3 w-12 mt-2" />
                        <Skeleton className="h-3 w-4 mt-1" />
                      </div>
                    ))}
                  </div>
                  <Skeleton className="h-4 w-48 mx-auto mt-4" />
                </CardContent>
              </Card>

              {/* Subscriptions List */}
              <div className="space-y-4">
                {Array.from({ length: 3 }, (_, i) => (
                  <Card key={i}>
                    <CardContent>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-2">
                            <Skeleton className="h-6 w-24" />
                            <Skeleton className="h-5 w-16" />
                            <Skeleton className="h-5 w-20" />
                          </div>
                          <Skeleton className="h-4 w-3/4" />
                          <div className="flex items-center gap-4">
                            <Skeleton className="h-3 w-32" />
                            <Skeleton className="h-3 w-32" />
                          </div>
                        </div>
                        <Skeleton className="h-9 w-24" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
