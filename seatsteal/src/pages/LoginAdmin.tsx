import { IonContent, IonPage } from "@ionic/react";
import { AdminLoginForm } from "@/components/auth/AdminLoginForm";
import { Shield } from "lucide-react";

export default function LoginAdmin() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <div className="space-y-2 text-center">
              <div className="flex justify-center mb-4">
                <Shield className="w-12 h-12 text-blue-600" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">
                Admin Portal
              </h1>
              <p className="text-muted-foreground">Administrator access only</p>
            </div>
            <AdminLoginForm />
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
