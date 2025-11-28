import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { UserDashboard } from "@/components/class/user-dashboard";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { signOut } from "@/lib/supabase";
import { useHistory } from "react-router-dom";

export default function Dashboard() {
  const { subscriptionTier, tierLoading } = useSession();
  const history = useHistory();

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

          {/* Mobile-only logout button */}
          <div className="md:hidden mt-8 pb-8">
            <Button
              variant="outline"
              className="w-full"
              onClick={async () => {
                await signOut();
                history.push("/");
              }}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
