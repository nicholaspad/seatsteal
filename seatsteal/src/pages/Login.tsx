import { IonContent, IonPage } from "@ionic/react";
import { LoginForm } from "@/components/auth/LoginForm";

export default function Login() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <div className="space-y-2 text-center">
              <h1 className="text-3xl font-bold tracking-tight">
                Welcome Back
              </h1>
              <p className="text-muted-foreground">
                Sign in to your SeatSteal account
              </p>
            </div>
            <LoginForm />
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
