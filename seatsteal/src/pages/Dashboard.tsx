import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { UserDashboard } from "@/components/class/user-dashboard";
import { RouteAwareSkeleton } from "@/components/skeletons/RouteAwareSkeleton";

export default function Dashboard() {
  const { subscriptionTier, tierLoading } = useSession();

  if (tierLoading) {
    return <RouteAwareSkeleton />;
  }

  return (
    <IonPage>
      <IonContent>
        <div className="container mx-auto px-4 py-8">
          <UserDashboard
            title="My Subscriptions"
            showHeader={true}
            itemsPerPage={10}
            userTier={subscriptionTier}
          />
        </div>
      </IonContent>
    </IonPage>
  );
}
