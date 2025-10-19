import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";

export default function Settings() {
  const { user } = useSession();

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="container mx-auto py-8">
          <h1 className="text-3xl font-bold mb-6">Settings</h1>
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold mb-2">Account</h3>
              <p className="text-sm text-muted-foreground">
                Email: {user?.email}
              </p>
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
