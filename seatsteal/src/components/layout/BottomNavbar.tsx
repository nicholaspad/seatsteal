import { Link, useLocation } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { Home, BookOpen, LayoutDashboard, LogIn } from "lucide-react";
import { cn } from "@/lib/utils";
import { Capacitor } from "@capacitor/core";
import { Haptics, ImpactStyle } from "@capacitor/haptics";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

export function BottomNavbar() {
  const location = useLocation();
  const { user, profile, loading, profileLoading } = useSession();

  const isLoading = loading || (user && profileLoading);

  const navigation: NavItem[] = [
    { name: "Home", href: "/", icon: Home },
    {
      name: "Courses",
      href: profile?.collegeId
        ? `/courses?college=${profile.collegeId}`
        : "/courses",
      icon: BookOpen,
    },
    user
      ? { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard }
      : { name: "Login", href: "/login", icon: LogIn },
  ];

  const handleNavClick = async (
    e: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => {
    // Trigger haptic feedback on native platforms
    if (Capacitor.isNativePlatform()) {
      try {
        await Haptics.impact({ style: ImpactStyle.Light });
      } catch {
        // Ignore haptic errors silently
      }
    }

    // Handle Home link - scroll to top if already on homepage
    if (href === "/" && location.pathname === "/") {
      e.preventDefault();
      const ionContent = document.querySelector("ion-content");
      if (ionContent) {
        await ionContent.scrollToTop(300);
      }
    }
  };

  const isActive = (href: string) => {
    if (href === "/") {
      return location.pathname === "/";
    }
    return location.pathname.startsWith(href.split("?")[0]);
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-border/40 bg-background/95 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80"
      style={{
        paddingBottom: "env(safe-area-inset-bottom, 0px)",
      }}
    >
      <div className="flex items-center justify-around h-16 max-w-md mx-auto px-2">
        {isLoading ? (
          // Loading skeleton
          <>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="flex flex-col items-center justify-center gap-1 py-2 px-4"
              >
                <div className="h-6 w-6 rounded-lg bg-muted animate-pulse" />
                <div className="h-3 w-10 rounded bg-muted animate-pulse" />
              </div>
            ))}
          </>
        ) : (
          navigation.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);

            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={(e) => handleNavClick(e, item.href)}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 py-2 px-4 rounded-xl transition-all duration-200 min-w-[72px]",
                  "active:scale-95 active:opacity-80",
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground/80",
                )}
              >
                {/* Active indicator pill */}
                {active && (
                  <span
                    className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-8 h-1 rounded-full bg-foreground"
                    style={{
                      animation: "fadeIn 0.2s ease-out",
                    }}
                  />
                )}
                <Icon
                  className={cn(
                    "h-6 w-6 transition-transform duration-200",
                    active && "scale-110",
                  )}
                />
                <span
                  className={cn(
                    "text-xs font-medium transition-opacity duration-200",
                    active ? "opacity-100" : "opacity-70",
                  )}
                >
                  {item.name}
                </span>
              </Link>
            );
          })
        )}
      </div>
    </nav>
  );
}
