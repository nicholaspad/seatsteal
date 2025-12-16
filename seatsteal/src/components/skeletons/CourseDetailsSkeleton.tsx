import { IonContent, IonPage } from "@ionic/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function CourseDetailsSkeleton() {
  return (
    <IonPage>
      <IonContent>
        <div className="container mx-auto px-4 py-8">
          <div className="space-y-6">
            {/* Breadcrumb skeleton */}
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-12" />
              <Skeleton className="h-4 w-1" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-1" />
              <Skeleton className="h-4 w-20" />
            </div>

            {/* Back button skeleton */}
            <Skeleton className="h-9 w-32" />

            {/* Main layout: 2 columns */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Left Sidebar - Course Info */}
              <div className="lg:col-span-1">
                <Card className="py-0">
                  <CardHeader className="space-y-4 p-6">
                    {/* Course title and code */}
                    <div className="space-y-2">
                      <Skeleton className="h-7 w-full" />
                      <Skeleton className="h-7 w-3/4" />
                      <Skeleton className="h-5 w-2/3" />
                    </div>

                    {/* Summary button */}
                    <Skeleton className="h-9 w-full" />

                    {/* Filter section */}
                    <div className="border-t pt-4 space-y-3">
                      <Skeleton className="h-4 w-20" />
                      <Skeleton className="h-10 w-full" />
                      <Skeleton className="h-4 w-32" />
                    </div>
                  </CardHeader>
                </Card>
              </div>

              {/* Main Content - Class List */}
              <div className="lg:col-span-3 space-y-6">
                {/* Class cards */}
                <div className="space-y-4">
                  {Array.from({ length: 5 }, (_, i) => (
                    <Card key={i}>
                      <CardContent className="pt-6">
                        <div className="space-y-4">
                          {/* Class header */}
                          <div className="flex items-start justify-between">
                            <div className="space-y-2 flex-1">
                              <Skeleton className="h-6 w-32" />
                              <Skeleton className="h-4 w-48" />
                            </div>
                            <Skeleton className="h-9 w-28" />
                          </div>

                          {/* Class details */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="space-y-1">
                              <Skeleton className="h-3 w-16" />
                              <Skeleton className="h-4 w-12" />
                            </div>
                            <div className="space-y-1">
                              <Skeleton className="h-3 w-20" />
                              <Skeleton className="h-4 w-16" />
                            </div>
                            <div className="space-y-1">
                              <Skeleton className="h-3 w-16" />
                              <Skeleton className="h-4 w-14" />
                            </div>
                            <div className="space-y-1">
                              <Skeleton className="h-3 w-20" />
                              <Skeleton className="h-4 w-20" />
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Footer card */}
                <Card className="py-0">
                  <CardContent className="p-4">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                      <Skeleton className="h-4 w-40" />
                      <Skeleton className="h-4 w-48" />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
