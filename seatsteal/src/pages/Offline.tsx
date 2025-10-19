import { IonContent, IonPage } from "@ionic/react";
import { Button } from "@/components/ui/button";
import { WifiOff } from "lucide-react";

export default function Offline() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6 text-center">
            <div className="flex justify-center">
              <div className="p-4 bg-orange-100 dark:bg-orange-900/30 rounded-full">
                <WifiOff className="w-12 h-12 text-orange-600 dark:text-orange-400" />
              </div>
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-semibold">No Internet Connection</h2>
              <p className="text-sm text-muted-foreground">
                Please check your connection and try again
              </p>
            </div>

            <Button onClick={() => window.location.reload()} className="w-full">
              Try Again
            </Button>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
