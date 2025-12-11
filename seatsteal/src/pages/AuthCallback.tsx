import { useEffect, useState } from "react";
import { useHistory } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { fetchWithToasts } from "@/lib/api";
import { AlertCircle } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { logError } from "@/lib/logger";

export default function AuthCallback() {
  const history = useHistory();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Get the session from the URL hash
        const {
          data: { session },
          error: sessionError,
        } = await supabase.auth.getSession();

        if (sessionError) {
          logError("Auth callback error", sessionError);
          setError(
            sessionError.message ||
              "Failed to complete authentication. Please try again.",
          );
          setIsProcessing(false);
          return;
        }

        if (!session) {
          setError(
            "No authentication session found. The link may have expired or already been used.",
          );
          setIsProcessing(false);
          return;
        }

        // Get user data to check role
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (!user) {
          setError(
            "Failed to get user information. Please try logging in again.",
          );
          setIsProcessing(false);
          return;
        }

        // Check if URL contains admin redirect hint
        const urlParams = new URLSearchParams(window.location.search);
        const isAdminRedirect = urlParams.get("admin") === "true";

        // Redirect based on user type or admin flag
        if (isAdminRedirect) {
          history.replace("/admin");
        } else {
          // Check if user has a college selected
          try {
            const response = await fetchWithToasts("/api/user/settings");
            if (response.ok) {
              const data = await response.json();
              if (data.success && data.data.collegeId > 0) {
                history.replace("/dashboard");
              } else {
                history.replace("/select-college");
              }
            } else {
              // API error - default to dashboard
              history.replace("/dashboard");
            }
          } catch {
            // Network error - default to dashboard
            history.replace("/dashboard");
          }
        }
      } catch (err) {
        logError("Unexpected error during auth callback", err);
        setError("An unexpected error occurred. Please try logging in again.");
        setIsProcessing(false);
      }
    };

    handleAuthCallback();
  }, [history]);

  if (isProcessing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4">
        <div className="text-center space-y-4">
          <Spinner className="size-12 mx-auto" />
          <h2 className="text-xl font-semibold">Signing you in...</h2>
          <p className="text-muted-foreground">
            Please wait while we complete your authentication.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4">
        <div className="max-w-md w-full space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <div className="flex gap-2">
            <Button
              onClick={() => history.push("/login")}
              className="flex-1"
              variant="outline"
            >
              Back to Login
            </Button>
            <Button onClick={() => window.location.reload()} className="flex-1">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
