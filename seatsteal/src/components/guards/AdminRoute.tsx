import { type ReactNode } from "react";
import { Redirect } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { RouteAwareSkeleton } from "@/components/skeletons";

interface AdminRouteProps {
  children: ReactNode;
}

export default function AdminRoute({ children }: AdminRouteProps) {
  const { user, profile, loading, profileLoading } = useSession();

  // Wait for both user and profile to load
  if (loading || profileLoading) {
    return <RouteAwareSkeleton />;
  }

  // Redirect to login if no user
  if (!user) {
    return <Redirect to="/login" />;
  }

  // Redirect to home if not admin (UX only, backend enforces real authorization)
  if (!profile || profile.role !== "admin") {
    return <Redirect to="/" />;
  }

  return <>{children}</>;
}
