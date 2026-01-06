import { useState } from "react";
import { signInWithMagicLink, signInWithGoogle } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mail, ArrowRight } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { EmailSchema } from "@/lib/validation";
import { ServerErrorWithToast } from "@/lib/api";

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [error, setError] = useState<React.ReactNode>("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [validationError, setValidationError] = useState("");

  async function handleGoogleSignIn() {
    setIsGoogleLoading(true);
    setError("");
    try {
      const { error } = await signInWithGoogle();
      if (error) {
        setError("Failed to sign in with Google. Please try again.");
      }
      // On success, Supabase redirects the user, so no need to handle here
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("An error occurred. Please try again.");
    } finally {
      setIsGoogleLoading(false);
    }
  }

  const validateEmail = (email: string) => {
    try {
      EmailSchema.parse(email);
      setValidationError("");
      return true;
    } catch (error) {
      const zodError = error as { issues?: { message: string }[] };
      setValidationError(
        zodError.issues?.[0]?.message || "Invalid email format",
      );
      return false;
    }
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setValidationError("");

    if (!validateEmail(email)) {
      setIsLoading(false);
      return;
    }

    try {
      const { error } = await signInWithMagicLink(email);

      if (error) {
        // Parse Supabase error message for rate limiting
        const errorMsg = error.message || "";
        if (
          errorMsg.toLowerCase().includes("security purposes") ||
          errorMsg.toLowerCase().includes("rate limit")
        ) {
          // Extract retry time if present (e.g., "59 seconds")
          const timeMatch = errorMsg.match(/(\d+)\s+(second|minute)/i);
          if (timeMatch) {
            const time = timeMatch[1];
            const unit = timeMatch[2];
            setError(
              `Too many login attempts. Please try again in ${time} ${unit}${parseInt(time) > 1 ? "s" : ""}.`,
            );
          } else {
            setError(
              "Too many login attempts. Please wait a few minutes and try again.",
            );
          }
        } else {
          setError("Failed to send magic link. Please try again.");
        }
      } else {
        setIsSubmitted(true);
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  if (isSubmitted) {
    return (
      <div className="space-y-4 text-center">
        <div className="flex justify-center">
          <div className="mt-2 p-4 bg-green-100 dark:bg-green-900/30 rounded-full">
            <Mail className="w-8 h-8 text-green-600 dark:text-green-400" />
          </div>
        </div>
        <div className="space-y-2">
          <h3 className="font-medium">Check Your Email</h3>
          <p className="text-sm text-muted-foreground">
            We&apos;ve sent a magic link to <strong>{email}</strong>.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            setIsSubmitted(false);
            setEmail("");
          }}
          className="w-full"
        >
          Try Different Email
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={handleGoogleSignIn}
          disabled={isGoogleLoading || isLoading}
        >
          {isGoogleLoading ? (
            <>
              <Spinner className="size-4 mr-2" />
              Signing in...
            </>
          ) : (
            <>
              <GoogleIcon className="size-4 mr-2" />
              Continue with Google
            </>
          )}
        </Button>

        <div className="flex items-center gap-3">
          <div className="flex-1 border-t" />
          <span className="text-xs uppercase text-muted-foreground">
            Or continue with email
          </span>
          <div className="flex-1 border-t" />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 mt-4">
        {validationError && (
          <Alert variant="destructive">
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        )}

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (validationError) {
                  setValidationError("");
                }
              }}
              onBlur={() => {
                if (email) {
                  validateEmail(email);
                }
              }}
              placeholder="john@example.com"
              className="pl-10"
              required
              disabled={isLoading}
            />
          </div>
          <Button
            type="submit"
            className="h-10 w-10 p-0"
            disabled={isLoading || !email}
            aria-label="Login"
          >
            {isLoading ? (
              <Spinner className="size-4" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
          </Button>
        </div>
      </form>
    </>
  );
}
