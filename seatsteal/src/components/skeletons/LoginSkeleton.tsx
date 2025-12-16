import { IonContent, IonPage } from "@ionic/react";
import { Skeleton } from "@/components/ui/skeleton";

export function LoginSkeleton() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <div className="space-y-4">
              {/* Label */}
              <div className="space-y-2">
                <Skeleton className="h-4 w-12" />
                {/* Input field */}
                <Skeleton className="h-10 w-full" />
              </div>

              {/* Submit button */}
              <Skeleton className="h-10 w-full" />

              {/* Help text */}
              <div className="flex justify-center">
                <Skeleton className="h-3 w-64" />
              </div>
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
