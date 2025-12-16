import { IonContent, IonPage } from "@ionic/react";
import { Skeleton } from "@/components/ui/skeleton";

export function DefaultSkeleton() {
  return (
    <IonPage>
      <IonContent>
        <div className="container mx-auto px-4 py-8">
          <div className="space-y-6">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/5" />
            <div className="pt-4">
              <Skeleton className="h-32 w-full" />
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
