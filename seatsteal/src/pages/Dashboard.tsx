import { useEffect, useRef } from "react";
import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { UserDashboard } from "@/components/class/user-dashboard";
import { RouteAwareSkeleton } from "@/components/skeletons/RouteAwareSkeleton";
import { applyStoredReferralCode } from "@/lib/referral-apply";

export default function Dashboard() {
  const { subscriptionTier, tierLoading, refreshSubscriptionTier } =
    useSession();
  const referralRetryRef = useRef(false);

  useEffect(() => {
    if (referralRetryRef.current) {
      return;
    }
    referralRetryRef.current = true;
    void applyStoredReferralCode({ refreshSubscriptionTier });
  }, [refreshSubscriptionTier]);

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
