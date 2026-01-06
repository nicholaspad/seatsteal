import { useLocation } from "react-router-dom";
import { CoursesSkeleton } from "./CoursesSkeleton";
import { CourseDetailsSkeleton } from "./CourseDetailsSkeleton";
import { DashboardSkeleton } from "./DashboardSkeleton";
import { SettingsSkeleton } from "./SettingsSkeleton";
import { LoginSkeleton } from "./LoginSkeleton";
import { DefaultSkeleton } from "./DefaultSkeleton";

/**
 * Route-aware skeleton loader that displays page-specific skeletons
 * based on the current route path. This minimizes visual flicker by
 * showing a skeleton that matches the layout of the loading page.
 */
export function RouteAwareSkeleton() {
  const location = useLocation();
  const path = location.pathname;

  // Match routes to their specific skeletons
  if (path === "/login") {
    return <LoginSkeleton />;
  }

  if (path === "/courses") {
    return <CoursesSkeleton />;
  }

  if (path.startsWith("/courses/")) {
    return <CourseDetailsSkeleton />;
  }

  if (path === "/dashboard") {
    return <DashboardSkeleton />;
  }

  if (path === "/settings") {
    return <SettingsSkeleton />;
  }

  if (path === "/select-college") {
    return <SettingsSkeleton />;
  }

  // Admin routes - use default skeleton
  if (path.startsWith("/admin")) {
    return <DefaultSkeleton />;
  }

  // Default fallback for all other routes
  return <DefaultSkeleton />;
}
