import { useLocation, useHistory } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { IonTabBar, IonTabButton, IonLabel } from "@ionic/react";
import { Home, BookOpen, LayoutDashboard } from "lucide-react";
import { Capacitor } from "@capacitor/core";
import { Haptics, ImpactStyle } from "@capacitor/haptics";
import { cn } from "@/lib/utils";

interface BottomNavbarProps {
  className?: string;
}

export function BottomNavbar({ className }: BottomNavbarProps) {
  const location = useLocation();
  const history = useHistory();
  const { user, profile, loading, profileLoading } = useSession();

  const isLoading = loading || (user && profileLoading);

  // Trigger haptic feedback on native platforms
  const triggerHaptic = async () => {
    if (Capacitor.isNativePlatform()) {
      try {
        await Haptics.impact({ style: ImpactStyle.Light });
      } catch {
        // Haptics not available on this device
      }
    }
  };

  const handleNavigation = async (path: string) => {
    await triggerHaptic();

    // Handle Home link - scroll to top if already on homepage
    if (path === "/" && location.pathname === "/") {
      const ionContent = document.querySelector("ion-content");
      if (ionContent) {
        await ionContent.scrollToTop(300);
      }
      return;
    }
    history.push(path);
  };

  const getCoursesPath = () => {
    return profile?.collegeId
      ? `/courses?college=${profile.collegeId}`
      : "/courses";
  };

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <IonTabBar
      slot="bottom"
      className={cn(
        "bottom-navbar border-t border-border/40 bg-background/95 backdrop-blur-xl",
        className,
      )}
      style={{
        paddingBottom: "env(safe-area-inset-bottom, 8px)",
      }}
    >
      {/* Home Tab */}
      <IonTabButton
        tab="home"
        onClick={() => handleNavigation("/")}
        className={cn(
          "bottom-nav-tab",
          isActive("/") &&
            !isActive("/courses") &&
            !isActive("/dashboard") &&
            !isActive("/login")
            ? "tab-active"
            : "tab-inactive",
        )}
      >
        <Home className="h-6 w-6" />
        <IonLabel>Home</IonLabel>
      </IonTabButton>

      {/* Courses Tab */}
      <IonTabButton
        tab="courses"
        onClick={() => handleNavigation(getCoursesPath())}
        className={cn(
          "bottom-nav-tab",
          isActive("/courses") ? "tab-active" : "tab-inactive",
        )}
      >
        <BookOpen className="h-6 w-6" />
        <IonLabel>Courses</IonLabel>
      </IonTabButton>

      {/* Dashboard Tab */}
      {isLoading ? (
        <IonTabButton tab="account" className="bottom-nav-tab tab-inactive">
          <div className="w-6 h-6 rounded-full bg-muted animate-pulse" />
          <IonLabel>
            <div className="w-12 h-3 rounded bg-muted animate-pulse mt-1" />
          </IonLabel>
        </IonTabButton>
      ) : (
        <IonTabButton
          tab="dashboard"
          onClick={() => handleNavigation("/dashboard")}
          className={cn(
            "bottom-nav-tab",
            isActive("/dashboard") ? "tab-active" : "tab-inactive",
          )}
        >
          <LayoutDashboard className="h-6 w-6" />
          <IonLabel>Dashboard</IonLabel>
        </IonTabButton>
      )}
    </IonTabBar>
  );
}
