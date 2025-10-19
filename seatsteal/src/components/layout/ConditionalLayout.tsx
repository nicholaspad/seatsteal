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

  if (isAuthPage) {
    // For auth pages, render children without header/footer
    return <>{children}</>;
  }

  // For regular pages, render Header and Footer alongside children
  // Header will be fixed at top, pages handle their own scrolling
  return (
    <>
      <Header />
      {children}
      <Footer />
    </>
  );
}
