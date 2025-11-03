import { useState, lazy, Suspense } from "react";
import { Link, useLocation, useHistory } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { signOut } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Home,
  BookOpen,
  LayoutDashboard,
  Menu,
  X,
  User,
  LogOut,
  LogIn,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Lazy load ThemeToggle for better performance
const ThemeToggle = lazy(() =>
  import("@/components/theme/ThemeToggle").then((mod) => ({
    default: mod.ThemeToggle,
  })),
);

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const history = useHistory();
  const { user, loading } = useSession();

  const navigation = [
    { name: "Home", href: "/", icon: Home },
    { name: "Courses", href: "/courses", icon: BookOpen },
    ...(user
      ? [{ name: "Dashboard", href: "/dashboard", icon: LayoutDashboard }]
      : []),
  ];

  const handleNavClick = async (
    e: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => {
    // Handle Home link - scroll to top if already on homepage
    if (href === "/" && location.pathname === "/") {
      e.preventDefault();
      const ionContent = document.querySelector("ion-content");
      if (ionContent) {
        await ionContent.scrollToTop(300);
      }
    }
  };

  return (
    <header
      className={cn(
        "border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        className,
      )}
    >
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link
            to="/"
            onClick={(e) => handleNavClick(e, "/")}
            className="flex items-center space-x-2"
          >
            <span className="font-bold text-lg">seatsteal</span>
            <Badge variant="secondary" className="text-xs">
              BETA
            </Badge>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;

              return (
                <Link
                  key={item.href}
                  to={item.href}
                  onClick={(e) => handleNavClick(e, item.href)}
                  className={cn(
                    "flex items-center space-x-2 transition-colors hover:text-foreground/80",
                    isActive ? "text-foreground" : "text-foreground/60",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Theme Toggle & User Menu & Mobile Menu Button */}
          <div className="flex items-center space-x-2">
            {/* Theme Toggle */}
            <Suspense
              fallback={
                <div className="w-9 h-9 rounded-md border border-input bg-background animate-pulse" />
              }
            >
              <ThemeToggle />
            </Suspense>

            {/* Authentication Menu */}
            {loading ? (
              <Button variant="ghost" size="sm" disabled>
                <User className="h-4 w-4" />
                <span className="hidden sm:ml-2 sm:inline">Loading...</span>
              </Button>
            ) : user ? (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={async () => {
                    await signOut();
                    history.push("/");
                  }}
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:ml-2 sm:inline">Logout</span>
                </Button>
              </>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => history.push("/login")}
              >
                <LogIn className="h-4 w-4" />
                <span className="hidden sm:ml-2 sm:inline">Login</span>
              </Button>
            )}

            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t">
            <nav className="flex flex-col space-y-1 py-4">
              {navigation.map((item) => {
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className="flex items-center space-x-3 rounded-md px-3 py-2 text-sm font-medium transition-colors bg-white text-black hover:bg-white/90"
                    onClick={(e) => {
                      handleNavClick(e, item.href);
                      setMobileMenuOpen(false);
                    }}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}

              {/* Mobile Authentication Options */}
              <div className="border-t pt-4 mt-4">
                {user ? (
                  <button
                    onClick={async () => {
                      setMobileMenuOpen(false);
                      await signOut();
                      history.push("/");
                    }}
                    className="flex w-full items-center space-x-3 rounded-md px-3 py-2 text-sm font-medium transition-colors bg-white text-black hover:bg-white/90"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Logout</span>
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      history.push("/login");
                    }}
                    className="flex w-full items-center space-x-3 rounded-md px-3 py-2 text-sm font-medium transition-colors bg-white text-black hover:bg-white/90"
                  >
                    <LogIn className="h-4 w-4" />
                    <span>Login</span>
                  </button>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
