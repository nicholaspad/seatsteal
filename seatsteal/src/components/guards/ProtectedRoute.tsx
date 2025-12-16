import { type ReactNode } from "react";
import { Redirect } from "react-router-dom";
import { useSession } from "@/components/providers/SessionProvider";
import { RouteAwareSkeleton } from "@/components/skeletons";

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading } = useSession();

  if (loading) {
    return <RouteAwareSkeleton />;
  }

  if (!user) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
