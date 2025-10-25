import { IonContent, IonPage } from "@ionic/react";
import { Button } from "@/components/ui/button";
import { Mail, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export default function VerifyRequest() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6 text-center">
            <div className="flex justify-center">
              <div className="p-4 bg-green-100 dark:bg-green-900/30 rounded-full">
                <Mail className="w-12 h-12 text-green-600 dark:text-green-400" />
              </div>
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Check Your Email</h2>
              <p className="text-sm text-muted-foreground">
                We've sent you a magic link to sign in to your account.
              </p>
            </div>

            <div className="border border-border p-4 rounded-lg">
              <p className="text-xs text-muted-foreground">
                Click the link in your email to complete the sign-in process.
                The link will expire in 24 hours.
              </p>
            </div>

            <div className="pt-4">
              <Button asChild variant="outline" className="w-full">
                <Link to="/login">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Sign In
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
