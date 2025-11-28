import { useLocation } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { BottomNavbar } from "@/components/layout/BottomNavbar";
import { useEffect, useState } from "react";

interface ConditionalLayoutProps {
  children: React.ReactNode;
}

// Custom hook to detect mobile viewport
function useIsMobile(breakpoint: number = 768) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.innerWidth < breakpoint;
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

  // Hide header and footer on auth pages (but not login for bottom nav)
  const isAuthPage =
    location.pathname.startsWith("/login") ||
    location.pathname.startsWith("/select-college") ||
    location.pathname.startsWith("/verify-request") ||
    location.pathname.includes("/error");

  // Pages where we don't show any navigation
  const isFullscreenPage =
    location.pathname.startsWith("/select-college") ||
    location.pathname.startsWith("/verify-request") ||
    location.pathname.includes("/error");

  if (isFullscreenPage) {
    // For fullscreen auth pages, render children without any navigation
    return <main className="h-screen">{children}</main>;
  }

  // Mobile layout: bottom navbar, no top header
  if (isMobile) {
    return (
      <div className="min-h-screen flex flex-col">
        <main className="flex-1 relative">{children}</main>
        <BottomNavbar className="fixed bottom-0 left-0 right-0 z-50" />
      </div>
    );
  }

  // Desktop layout: top header, no bottom navbar
  if (isAuthPage) {
    // For auth pages on desktop, render without header
    return <main className="h-screen">{children}</main>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header className="flex-shrink-0 z-50" />
      <main className="flex-1 relative">{children}</main>
    </div>
  );
}
