import { IonContent, IonPage } from "@ionic/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function SettingsSkeleton() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="container mx-auto py-8">
          {/* Breadcrumb skeleton */}
          <div className="flex items-center gap-2 mb-6">
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-4 w-1" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-1" />
            <Skeleton className="h-4 w-16" />
          </div>

          <div className="max-w-2xl mx-auto">
            <Card>
              <CardHeader>
                <Skeleton className="h-7 w-48" />
              </CardHeader>

              <CardContent className="space-y-6 pt-2">
                {/* Alert */}
                <Skeleton className="h-32 w-full" />

                {/* Form fields */}
                {Array.from({ length: 3 }, (_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-4 w-48" />
                  </div>
                ))}

                {/* Button */}
                <Skeleton className="h-10 w-full" />
              </CardContent>
            </Card>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
