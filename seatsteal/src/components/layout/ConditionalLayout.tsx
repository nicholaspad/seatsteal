import { useLocation } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

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

  // Pages where we don't show any navigation
  const isFullscreenPage =
    location.pathname.startsWith("/select-college") ||
    location.pathname.startsWith("/verify-request") ||
    location.pathname.includes("/error");

  if (isFullscreenPage) {
    // For fullscreen auth pages, render children without any navigation
    return <main className="h-screen">{children}</main>;
  }

  if (isAuthPage) {
    // For auth pages (like login), render without header/footer
    return <main className="h-screen">{children}</main>;
  }

  // Standard layout with header and footer for both mobile and desktop
  return (
    <div className="min-h-screen flex flex-col">
      <Header className="flex-shrink-0 z-50" />
      <main className="flex-1 relative">
        {children}
      </main>
      <Footer className="flex-shrink-0" />
    </div>
  );
}
