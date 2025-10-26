import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// @ts-expect-error - Font package doesn't have types
import "@fontsource/inter";
import "./index.css";
import { IonApp, IonRouterOutlet, setupIonicReact } from "@ionic/react";
import { IonReactRouter } from "@ionic/react-router";
import { SpeedInsights } from "@vercel/speed-insights/vue";
import { Route, Redirect } from "react-router-dom";
import { Toaster } from "sonner";

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

/* Pages */
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import LoginAdmin from "@/pages/LoginAdmin";
import VerifyRequest from "@/pages/VerifyRequest";
import SelectCollege from "@/pages/SelectCollege";
import Error from "@/pages/Error";
import Courses from "@/pages/Courses";
import Dashboard from "@/pages/Dashboard";
import Settings from "@/pages/Settings";
import Offline from "@/pages/Offline";

/* Layout */
import { ConditionalLayout } from "@/components/layout/ConditionalLayout";

setupIonicReact();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="seatsteal-theme">
      <SessionProvider>
        <TooltipProvider>
          <IonApp>
            <IonReactRouter>
              <ConditionalLayout>
                <IonRouterOutlet>
                  {/* Public routes */}
                  <Route exact path="/" component={Home} />
                  <Route exact path="/courses" component={Courses} />
                  <Route exact path="/offline" component={Offline} />

                  {/* Auth routes */}
                  <Route exact path="/login" component={Login} />
                  <Route exact path="/login-admin" component={LoginAdmin} />
                  <Route
                    exact
                    path="/verify-request"
                    component={VerifyRequest}
                  />
                  <Route exact path="/error" component={Error} />

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

                  {/* Fallback redirect */}
                  <Route render={() => <Redirect to="/" />} />
                </IonRouterOutlet>
              </ConditionalLayout>
            </IonReactRouter>
            <Toaster position="top-center" />
          </IonApp>
        </TooltipProvider>
      </SessionProvider>
    </ThemeProvider>
    <SpeedInsights/>
  </StrictMode>,
);
