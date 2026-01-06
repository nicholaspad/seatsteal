import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
// @ts-expect-error - Font package doesn't have types
import "@fontsource/geist-sans";
import "./index.css";
import { IonApp, IonRouterOutlet, setupIonicReact } from "@ionic/react";
import { IonReactRouter } from "@ionic/react-router";
import { Route, Redirect } from "react-router-dom";
import { Toaster } from "sonner";
import { SpeedInsights } from "@vercel/speed-insights/react";
import { Analytics } from "@vercel/analytics/react";

/* Core Ionic framework styles */
import "@ionic/react/css/core.css";

/* Basic CSS for apps built with Ionic */
import "@ionic/react/css/normalize.css";
import "@ionic/react/css/structure.css";
import "@ionic/react/css/typography.css";

/* Optional CSS utils that can be commented out */
import "@ionic/react/css/padding.css";
import "@ionic/react/css/float-elements.css";
import "@ionic/react/css/text-alignment.css";
import "@ionic/react/css/text-transformation.css";
import "@ionic/react/css/flex-utils.css";
import "@ionic/react/css/display.css";

/* Ionic Theme variables */
import "./variables.css";

/* Providers */
import { SessionProvider } from "@/components/providers/SessionProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { TooltipProvider } from "@/components/ui/tooltip";

/* Guards */
import ProtectedRoute from "@/components/guards/ProtectedRoute";
import AdminRoute from "@/components/guards/AdminRoute";

/* Layout */
import { ConditionalLayout } from "@/components/layout/ConditionalLayout";

/*
 * Eagerly loaded pages - critical for first paint / common entry points
 * These are loaded in the main bundle for instant navigation
 */
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import Courses from "@/pages/Courses";
import AuthCallback from "@/pages/AuthCallback";
import Error from "@/pages/Error";

/*
 * Lazily loaded pages - loaded on-demand when navigating
 * This reduces initial bundle size and improves first paint time
 */
const CourseDetails = lazy(() => import("@/pages/CourseDetails"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Settings = lazy(() => import("@/pages/Settings"));
const SelectCollege = lazy(() => import("@/pages/SelectCollege"));
const VerifyRequest = lazy(() => import("@/pages/VerifyRequest"));
const Offline = lazy(() => import("@/pages/Offline"));
const PrivacyPolicy = lazy(() => import("@/pages/PrivacyPolicy"));
const TermsOfService = lazy(() => import("@/pages/TermsOfService"));

/* Admin Pages - lazy loaded since only accessed by admins */
const Admin = lazy(() => import("@/pages/admin/Admin"));
const AdminColleges = lazy(() => import("@/pages/admin/AdminColleges"));
const AdminPerformance = lazy(() => import("@/pages/admin/AdminPerformance"));
const AdminScrapers = lazy(() => import("@/pages/admin/AdminScrapers"));
const AdminUsers = lazy(() => import("@/pages/admin/AdminUsers"));
const AdminNotifications = lazy(
  () => import("@/pages/admin/AdminNotifications"),
);
const AdminTerminal = lazy(() => import("@/pages/admin/AdminTerminal"));

/* Route-aware skeleton loader for lazy-loaded routes */
import { RouteAwareSkeleton } from "@/components/skeletons";

setupIonicReact();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="seatsteal-theme">
      <SessionProvider>
        <TooltipProvider>
          <IonApp>
            <IonReactRouter>
              <ConditionalLayout>
                <Suspense fallback={<RouteAwareSkeleton />}>
                  <IonRouterOutlet animated={false}>
                    {/* Public routes - eagerly loaded */}
                    <Route exact path="/" component={Home} />
                    <Route exact path="/courses" component={Courses} />
                    <Route exact path="/login" component={Login} />
                    <Route
                      exact
                      path="/auth/callback"
                      component={AuthCallback}
                    />
                    <Route exact path="/error" component={Error} />

                    {/* Public routes - lazily loaded */}
                    <Route exact path="/offline" component={Offline} />
                    <Route exact path="/privacy" component={PrivacyPolicy} />
                    <Route exact path="/terms" component={TermsOfService} />
                    <Route
                      exact
                      path="/verify-request"
                      component={VerifyRequest}
                    />

                    {/* Protected course detail route */}
                    <Route
                      exact
                      path="/courses/:id"
                      render={() => (
                        <ProtectedRoute>
                          <CourseDetails />
                        </ProtectedRoute>
                      )}
                    />

                    {/* Protected routes */}
                    <Route
                      exact
                      path="/select-college"
                      render={() => (
                        <ProtectedRoute>
                          <SelectCollege />
                        </ProtectedRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/dashboard"
                      render={() => (
                        <ProtectedRoute>
                          <Dashboard />
                        </ProtectedRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/settings"
                      render={() => (
                        <ProtectedRoute>
                          <Settings />
                        </ProtectedRoute>
                      )}
                    />

                    {/* Admin routes */}
                    <Route
                      exact
                      path="/admin"
                      render={() => (
                        <AdminRoute>
                          <Admin />
                        </AdminRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/admin/colleges"
                      render={() => (
                        <AdminRoute>
                          <AdminColleges />
                        </AdminRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/admin/performance"
                      render={() => (
                        <AdminRoute>
                          <AdminPerformance />
                        </AdminRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/admin/scrapers"
                      render={() => (
                        <AdminRoute>
                          <AdminScrapers />
                        </AdminRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/admin/users"
                      render={() => (
                        <AdminRoute>
                          <AdminUsers />
                        </AdminRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/admin/notifications"
                      render={() => (
                        <AdminRoute>
                          <AdminNotifications />
                        </AdminRoute>
                      )}
                    />
                    <Route
                      exact
                      path="/admin/terminal"
                      render={() => (
                        <AdminRoute>
                          <AdminTerminal />
                        </AdminRoute>
                      )}
                    />

                    {/* Fallback redirect */}
                    <Route render={() => <Redirect to="/" />} />
                  </IonRouterOutlet>
                </Suspense>
              </ConditionalLayout>
            </IonReactRouter>
            <Toaster position="top-center" />
          </IonApp>
        </TooltipProvider>
      </SessionProvider>
      <SpeedInsights />
      <Analytics />
    </ThemeProvider>
  </StrictMode>,
);
