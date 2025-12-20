import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Sparkles, X } from "lucide-react";

const DISMISSAL_KEY = "referral-alert-dismissed";

export function ReferralAlert() {
  const [visible, setVisible] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const refCode = params.get("ref");
    const dismissed = localStorage.getItem(DISMISSAL_KEY);

    if (refCode && !dismissed) {
      setVisible(true);
    }
  }, [location.search]);

  const handleDismiss = () => {
    localStorage.setItem(DISMISSAL_KEY, "true");
    setVisible(false);
  };

  if (!visible) {
    return null;
  }

  return (
    <div className="fixed top-16 left-0 right-0 z-40 px-4 py-2">
      <Alert className="bg-gradient-to-r from-purple-900/90 to-blue-900/90 border-purple-500/50 backdrop-blur-sm">
        <Sparkles className="text-yellow-400" />
        <AlertDescription className="flex items-center justify-between gap-2">
          <span className="text-white">
            You've been referred! Sign up to get 7 free days of Pro for you and
            your referrer.
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
            className="h-6 w-6 p-0 hover:bg-white/10"
          >
            <X className="h-4 w-4 text-white" />
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  );
}
