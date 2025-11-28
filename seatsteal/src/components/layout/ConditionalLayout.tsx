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

  // Hide navigation on admin pages (they have their own layout)
  const isAdminPage = location.pathname.startsWith("/admin");

  if (isAuthPage) {
    // For auth pages, render children without header/footer and use full height
    return <main className="h-screen">{children}</main>;
  }

  if (isAdminPage) {
    // Admin pages have their own layout
    return (
      <div className="min-h-screen flex flex-col">
        <Header className="flex-shrink-0 z-50" />
        <main className="flex-1 relative">{children}</main>
      </div>
    );
  }

  // For regular pages:
  // - Desktop: top header visible, no bottom navbar
  // - Mobile: bottom navbar visible, top header hidden
  return (
    <div className="min-h-screen flex flex-col">
      {/* Desktop header - hidden on mobile */}
      <Header className="flex-shrink-0 z-50 hidden md:block" />
      {/* Main content with bottom padding on mobile to account for bottom navbar */}
      <main className="flex-1 relative pb-20 md:pb-0">{children}</main>
      {/* Mobile bottom navbar - hidden on desktop */}
      <div className="md:hidden">
        <BottomNavbar />
      </div>
    </div>
  );
}
