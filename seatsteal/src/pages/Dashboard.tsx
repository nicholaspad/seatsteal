import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";

export default function Dashboard() {
  const { user } = useSession();

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="container mx-auto py-8">
          <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
          <div className="space-y-4">
            <p>Welcome back, {user?.email}!</p>
            <p className="text-muted-foreground">
              Your subscriptions and notifications will appear here.
            </p>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
