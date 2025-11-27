import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { BottomNav } from "@/components/layout/BottomNav";

interface ConditionalLayoutProps {
  children: React.ReactNode;
}

// Custom hook to detect mobile screen size
function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth < breakpoint;
    }
    return false;
  });

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < breakpoint);
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [breakpoint]);

  return isMobile;
}

export function ConditionalLayout({ children }: ConditionalLayoutProps) {
  const location = useLocation();
  const isMobile = useIsMobile();

  // Hide header and footer on auth pages and admin pages
  const isAuthPage =
    location.pathname.startsWith("/login") ||
    location.pathname.startsWith("/select-college") ||
    location.pathname.startsWith("/verify-request") ||
    location.pathname.includes("/error");

  const isAdminPage = location.pathname.startsWith("/admin");

  // Don't show bottom nav on auth pages or admin pages
  const showBottomNav = isMobile && !isAuthPage && !isAdminPage;
  // Show top header on desktop, or on admin pages regardless of screen size
  const showTopHeader = (!isMobile || isAdminPage) && !isAuthPage;

  if (isAuthPage) {
    // For auth pages, render children without header/footer and use full height
    return <main className="h-screen">{children}</main>;
  }

  // For regular pages, use flex layout with conditional header/bottom nav
  return (
    <div className="min-h-screen flex flex-col">
      {showTopHeader && <Header className="flex-shrink-0 z-50" />}
      <main className={`flex-1 relative ${showBottomNav ? "pb-[60px]" : ""}`}>
        {children}
      </main>
      {showBottomNav && <BottomNav />}
    </div>
  );
}
