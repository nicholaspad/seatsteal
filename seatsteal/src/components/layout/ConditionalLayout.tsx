import { useLocation } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { BottomNavbar } from "@/components/layout/BottomNavbar";

interface ConditionalLayoutProps {
  children: React.ReactNode;
}

export function ConditionalLayout({ children }: ConditionalLayoutProps) {
  const location = useLocation();

  // Hide header and footer on auth pages
  const isAuthPage =
    location.pathname.startsWith("/login") ||
    location.pathname.startsWith("/select-college") ||
    location.pathname.startsWith("/verify-request") ||
    location.pathname.includes("/error");

  // Admin pages should not show bottom navbar
  const isAdminPage = location.pathname.startsWith("/admin");

  if (isAuthPage) {
    // For auth pages, render children without header/footer and use full height
    return <main className="h-screen">{children}</main>;
  }

  // For regular pages, use flex layout with header on desktop
  // and bottom navbar on mobile
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header: hidden on mobile, shown on desktop */}
      <Header className="flex-shrink-0 z-50 hidden md:block" />
      {/* Main content with bottom padding on mobile for bottom navbar */}
      <main className="flex-1 relative pb-20 md:pb-0">{children}</main>
      {/* Bottom navbar: shown on mobile, hidden on desktop and admin pages */}
      {!isAdminPage && (
        <div className="md:hidden">
          <BottomNavbar />
        </div>
      )}
    </div>
  );
}
