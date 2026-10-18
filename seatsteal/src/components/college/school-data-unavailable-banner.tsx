import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatRelativeTime } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { useSession } from "@/components/providers/SessionProvider";
import { logError } from "@/lib/logger";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface SchoolDataUnavailableBannerProps {
  collegeId: number;
  schoolName: string;
  lastUpdatedAt?: string | null;
  className?: string;
}

export function SchoolDataUnavailableBanner({
  collegeId,
  schoolName,
  lastUpdatedAt,
  className,
}: SchoolDataUnavailableBannerProps) {
  const { user } = useSession();
  const relativeTime = formatRelativeTime(lastUpdatedAt ?? null);
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [registered, setRegistered] = useState(false);

  const signedIn = Boolean(user);

  const handleNotify = async () => {
    setEmailError(null);

    if (!signedIn) {
      const trimmed = email.trim();
      if (!EMAIL_PATTERN.test(trimmed)) {
        setEmailError("Enter a valid email");
        return;
      }
    }

    setSubmitting(true);
    try {
      const response = await fetchWithToasts(
        `/api/colleges/${collegeId}/data-waitlist`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(signedIn ? {} : { email: email.trim() }),
        },
      );

      if (!response.ok) {
        if (response.status === 422) {
          setEmailError("Enter a valid email");
          return;
        }
        setEmailError("Could not save your request. Please try again.");
        return;
      }

      setRegistered(true);
    } catch (error) {
      if (!(error instanceof ServerErrorWithToast)) {
        logError("Failed to join data waitlist", error);
        setEmailError("Could not save your request. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Alert
      className={cn(
        "border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-50",
        className,
      )}
      data-testid="school-data-unavailable-banner"
    >
      <AlertTriangle className="text-amber-600 dark:text-amber-400" />
      <AlertTitle>Seat data temporarily unavailable</AlertTitle>
      <AlertDescription>
        <p>
          Seat data for {schoolName} is temporarily unavailable. We&apos;re
          working on it. Last updated {relativeTime}.
        </p>
        {registered ? (
          <p
            className="mt-2 font-medium text-amber-950 dark:text-amber-50"
            data-testid="data-waitlist-confirmation"
          >
            We&apos;ll let you know when it&apos;s back
          </p>
        ) : (
          <div className="mt-3 flex w-full flex-col gap-2 sm:flex-row sm:items-center">
            {!signedIn && (
              <Input
                type="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setEmailError(null);
                }}
                placeholder="Your email"
                aria-label="Email"
                className="bg-white sm:max-w-xs dark:bg-background"
                data-testid="data-waitlist-email"
              />
            )}
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={handleNotify}
              disabled={submitting}
              className="border-amber-400 bg-white text-amber-950 hover:bg-amber-100 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-50 dark:hover:bg-amber-900"
              data-testid="data-waitlist-notify"
            >
              {submitting ? "Saving..." : "Notify me when it's back"}
            </Button>
          </div>
        )}
        {emailError && (
          <p className="mt-1 text-sm text-red-700 dark:text-red-300">
            {emailError}
          </p>
        )}
      </AlertDescription>
    </Alert>
  );
}
