import { useLocation } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { BottomNavbar } from "@/components/layout/BottomNavbar";
import { useIsMobile } from "@/hooks/use-is-mobile";

interface ConditionalLayoutProps {
  children: React.ReactNode;
}

export function ConditionalLayout({ children }: ConditionalLayoutProps) {
  const location = useLocation();
  const isMobile = useIsMobile();

  // Hide header and footer on auth pages
  const isAuthPage =
    location.pathname.startsWith("/login") ||
    location.pathname.startsWith("/select-college") ||
    location.pathname.startsWith("/verify-request") ||
    location.pathname.includes("/error");

  // Also hide on admin pages for cleaner admin experience
  const isAdminPage = location.pathname.startsWith("/admin");

  if (isAuthPage) {
    // For auth pages, render children without header/footer and use full height
    return <main className="h-screen">{children}</main>;
  }

  // For mobile: show bottom navbar, hide top header
  if (isMobile && !isAdminPage) {
    return (
      <div className="min-h-screen flex flex-col">
        <main className="flex-1 relative pb-16">{children}</main>
        <BottomNavbar />
      </div>
    );
  }

  // For desktop (or admin pages): use flex layout with header
  // This ensures header stays at top, content fills the rest
  return (
    <div className="min-h-screen flex flex-col">
      <Header className="flex-shrink-0 z-50" />
      <main className="flex-1 relative">{children}</main>
    </div>
  );
}
