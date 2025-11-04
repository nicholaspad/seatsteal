import { IonContent, IonPage } from "@ionic/react";
import { AdminLoginForm } from "@/components/auth/AdminLoginForm";

export default function LoginAdmin() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <AdminLoginForm />
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
