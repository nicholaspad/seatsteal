import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { UserDashboard } from "@/components/class/user-dashboard";
import { Footer } from "@/components/layout/Footer";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { signOut } from "@/lib/supabase";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Dashboard() {
  const { subscriptionTier, tierLoading } = useSession();
  const isMobile = useIsMobile();

  const handleLogout = async () => {
    await signOut();
  };

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
          {isMobile && (
            <div className="mt-8 flex justify-center">
              <Button
                variant="ghost"
                onClick={handleLogout}
                className="text-muted-foreground hover:text-foreground"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Log out
              </Button>
            </div>
          )}
        </div>

        {/* Footer */}
        <Footer className="mt-auto" />
      </IonContent>
    </IonPage>
  );
}
