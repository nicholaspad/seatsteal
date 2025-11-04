import { IonContent, IonPage } from "@ionic/react";
import { LoginForm } from "@/components/auth/LoginForm";

export default function Login() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <LoginForm />
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
