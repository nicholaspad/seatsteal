import { Link, useLocation } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { Home, BookOpen, LayoutDashboard, LogIn } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItemProps {
  href: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  onClick?: (e: React.MouseEvent<HTMLAnchorElement>) => void;
}

function NavItem({ href, icon, label, isActive, onClick }: NavItemProps) {
  return (
    <Link
      to={href}
      onClick={onClick}
      className={cn(
        "flex flex-col items-center justify-center gap-1 py-2 px-3 min-w-[64px] transition-colors",
        isActive
          ? "text-foreground"
          : "text-muted-foreground hover:text-foreground/80",
      )}
    >
      <div className={cn("transition-transform", isActive && "scale-110")}>
        {icon}
      </div>
      <span className="text-xs font-medium">{label}</span>
    </Link>
  );
}

export function BottomNavbar() {
  const location = useLocation();
  const { user, profile, loading, profileLoading } = useSession();

  const isLoading = loading || (user && profileLoading);

  const handleHomeClick = async (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (location.pathname === "/") {
      e.preventDefault();
      const ionContent = document.querySelector("ion-content");
      if (ionContent) {
        await ionContent.scrollToTop(300);
      }
    }
  };

  const coursesHref = profile?.collegeId
    ? `/courses?college=${profile.collegeId}`
    : "/courses";

  // Check if path starts with the given base (for active state)
  const isPathActive = (basePath: string) => {
    if (basePath === "/") {
      return location.pathname === "/";
    }
    return location.pathname.startsWith(basePath);
  };

  if (isLoading) {
    return (
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
        style={{
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
        }}
      >
        <div className="flex items-center justify-around h-16">
          {/* Skeleton loading state */}
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex flex-col items-center gap-1 py-2 px-3">
              <div className="w-6 h-6 bg-muted rounded animate-pulse" />
              <div className="w-10 h-3 bg-muted rounded animate-pulse" />
            </div>
          ))}
        </div>
      </nav>
    );
  }

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
      style={{
        paddingBottom: "env(safe-area-inset-bottom, 0px)",
      }}
    >
      <div className="flex items-center justify-around h-16">
        <NavItem
          href="/"
          icon={<Home className="h-6 w-6" />}
          label="Home"
          isActive={isPathActive("/")}
          onClick={handleHomeClick}
        />
        <NavItem
          href={coursesHref}
          icon={<BookOpen className="h-6 w-6" />}
          label="Courses"
          isActive={isPathActive("/courses")}
        />
        {user ? (
          <NavItem
            href="/dashboard"
            icon={<LayoutDashboard className="h-6 w-6" />}
            label="Dashboard"
            isActive={isPathActive("/dashboard")}
          />
        ) : (
          <NavItem
            href="/login"
            icon={<LogIn className="h-6 w-6" />}
            label="Login"
            isActive={isPathActive("/login")}
          />
        )}
      </div>
    </nav>
  );
}
