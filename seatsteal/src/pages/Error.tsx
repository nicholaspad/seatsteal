import { IonContent, IonPage } from "@ionic/react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { getErrorMessage } from "@/lib/security";

export default function Error() {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  // Use only predefined error codes to prevent XSS and information disclosure
  const errorCode = searchParams.get("code");
  const { title, message } = getErrorMessage(errorCode);

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6 text-center">
            <div className="flex justify-center">
              <div className="p-4 bg-red-100 dark:bg-red-900/30 rounded-full">
                <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400" />
              </div>
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-semibold">{title}</h2>
              <p className="text-sm text-muted-foreground">{message}</p>
            </div>

            <div className="pt-4 space-y-2">
              <Button asChild className="w-full">
                <Link to="/">Go Home</Link>
              </Button>
              <Button asChild variant="outline" className="w-full">
                <Link to="/login">Try Signing In Again</Link>
              </Button>
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
