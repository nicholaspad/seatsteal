import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { UserDashboard } from "@/components/class/user-dashboard";
import { useDocumentTitle, SEO_CONFIGS } from "@/hooks/use-document-title";

export default function Dashboard() {
  const { subscriptionTier, tierLoading } = useSession();

  // SEO: Set document title and meta description
  useDocumentTitle(SEO_CONFIGS.dashboard);

  return (
    <IonPage>
      <IonContent>
        <div className="container mx-auto px-4 py-8">
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
