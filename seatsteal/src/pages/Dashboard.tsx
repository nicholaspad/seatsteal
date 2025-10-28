import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { UserDashboard } from "@/components/class/user-dashboard";

export default function Dashboard() {
  const { subscriptionTier, tierLoading } = useSession();

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="container mx-auto py-8">
          {tierLoading ? (
            <div className="text-center py-12">
              <div className="animate-pulse space-y-4">
                <div className="h-8 bg-muted rounded w-64 mx-auto"></div>
                <div className="h-4 bg-muted rounded w-96 mx-auto"></div>
              </div>
            </div>
          ) : (
            <UserDashboard
              title="My Subscriptions"
              showHeader={true}
              itemsPerPage={10}
              userTier={subscriptionTier}
            />
          )}
        </div>
      </IonContent>
    </IonPage>
  );
}
