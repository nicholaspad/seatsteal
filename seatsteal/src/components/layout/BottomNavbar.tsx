import { useLocation, useHistory } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { IonTabBar, IonTabButton, IonIcon, IonLabel } from "@ionic/react";
import { home, bookOutline, logIn, grid } from "ionicons/icons";
import { cn } from "@/lib/utils";

export function BottomNavbar() {
  const location = useLocation();
  const history = useHistory();
  const { user, profile, loading, profileLoading } = useSession();

  const isLoading = loading || (user && profileLoading);

  const handleNavClick = async (href: string) => {
    // Handle Home link - scroll to top if already on homepage
    if (href === "/" && location.pathname === "/") {
      const ionContent = document.querySelector("ion-content");
      if (ionContent) {
        await ionContent.scrollToTop(300);
      }
      return;
    }

    history.push(href);
  };

  const getCoursesHref = () => {
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
      className="bottom-navbar"
      style={{
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ["--background" as any]: "rgba(0, 0, 0, 0.95)",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ["--border" as any]: "1px solid rgba(255, 255, 255, 0.1)",
        height: "auto",
        paddingBottom: "env(safe-area-inset-bottom, 8px)",
      }}
    >
      {/* Home */}
      <IonTabButton
        tab="home"
        onClick={() => handleNavClick("/")}
        className={cn("bottom-nav-button", isActive("/") && "tab-selected")}
      >
        <IonIcon
          icon={home}
          className={cn(
            "text-xl transition-all duration-200",
            isActive("/") ? "scale-110" : "opacity-60",
          )}
        />
        <IonLabel
          className={cn(
            "text-xs font-medium transition-opacity duration-200",
            isActive("/") ? "opacity-100" : "opacity-60",
          )}
        >
          Home
        </IonLabel>
      </IonTabButton>

      {/* Courses */}
      <IonTabButton
        tab="courses"
        onClick={() => handleNavClick(getCoursesHref())}
        className={cn(
          "bottom-nav-button",
          isActive("/courses") && "tab-selected",
        )}
      >
        <IonIcon
          icon={bookOutline}
          className={cn(
            "text-xl transition-all duration-200",
            isActive("/courses") ? "scale-110" : "opacity-60",
          )}
        />
        <IonLabel
          className={cn(
            "text-xs font-medium transition-opacity duration-200",
            isActive("/courses") ? "opacity-100" : "opacity-60",
          )}
        >
          Courses
        </IonLabel>
      </IonTabButton>

      {/* Login/Dashboard */}
      {isLoading ? (
        <IonTabButton tab="account" disabled className="bottom-nav-button">
          <div className="w-6 h-6 rounded-full bg-white/10 animate-pulse" />
          <IonLabel className="text-xs font-medium opacity-60">...</IonLabel>
        </IonTabButton>
      ) : user ? (
        <IonTabButton
          tab="dashboard"
          onClick={() => handleNavClick("/dashboard")}
          className={cn(
            "bottom-nav-button",
            isActive("/dashboard") && "tab-selected",
          )}
        >
          <IonIcon
            icon={grid}
            className={cn(
              "text-xl transition-all duration-200",
              isActive("/dashboard") ? "scale-110" : "opacity-60",
            )}
          />
          <IonLabel
            className={cn(
              "text-xs font-medium transition-opacity duration-200",
              isActive("/dashboard") ? "opacity-100" : "opacity-60",
            )}
          >
            Dashboard
          </IonLabel>
        </IonTabButton>
      ) : (
        <IonTabButton
          tab="login"
          onClick={() => handleNavClick("/login")}
          className={cn(
            "bottom-nav-button",
            isActive("/login") && "tab-selected",
          )}
        >
          <IonIcon
            icon={logIn}
            className={cn(
              "text-xl transition-all duration-200",
              isActive("/login") ? "scale-110" : "opacity-60",
            )}
          />
          <IonLabel
            className={cn(
              "text-xs font-medium transition-opacity duration-200",
              isActive("/login") ? "opacity-100" : "opacity-60",
            )}
          >
            Login
          </IonLabel>
        </IonTabButton>
      )}
    </IonTabBar>
  );
}
