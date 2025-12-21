import { useEffect, useState } from "react";
import { useHistory } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { AlertCircle } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { logError } from "@/lib/logger";
import { fetchWithToasts } from "@/lib/api";
import { toast } from "sonner";

export default function AuthCallback() {
  const history = useHistory();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  console.log("AuthCallback");

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

        // Apply referral code if one was stored
        const storedReferralCode = localStorage.getItem("referral_code");
        if (storedReferralCode) {
          try {
            const response = await fetchWithToasts("/api/referrals/apply", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ referral_code: storedReferralCode }),
            });

            if (response.ok) {
              toast.success("🎉 Your referral has been applied!");
            }

            localStorage.removeItem("referral_code");
          } catch (err) {
            // Don't block auth on referral error, just log it
            logError("Failed to apply referral code", err);
            localStorage.removeItem("referral_code");
          }
        }

        // Redirect based on user type or admin flag
        if (isAdminRedirect) {
          history.replace("/admin");
        } else {
          // Check if user needs to select a college first
          // We'll redirect to dashboard, and the app will handle college selection if needed
          history.replace("/dashboard");
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
          <h2 className="text-xl font-semibold mt-1">Signing you in...</h2>
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
