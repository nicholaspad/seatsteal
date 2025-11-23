import { useState } from "react";
import { signInWithMagicLink } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mail } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { EduEmailSchema } from "@/lib/validation";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<React.ReactNode>("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [validationError, setValidationError] = useState("");

  const validateEmail = (email: string) => {
    try {
      EduEmailSchema.parse(email);
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
      // Check early access before sending magic link
      const earlyAccessResponse = await fetchWithToasts(
        "/api/auth/check-early-access",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        },
      );

      const earlyAccessData = await earlyAccessResponse.json();

      if (!earlyAccessResponse.ok) {
        setError(earlyAccessData.error || "Failed to verify email");
        setIsLoading(false);
        return;
      }

      if (!earlyAccessData.hasEarlyAccess) {
        setError(
          <>
            This email is not enrolled in early access.{" "}
            <a
              href="https://form.typeform.com/to/mi3IrgGR"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:no-underline"
            >
              Request early access
            </a>
          </>,
        );
        setIsLoading(false);
        return;
      }

      // Proceed with magic link if early access is granted
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
      <div className="space-y-2 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Welcome Back</h1>
        <p className="text-muted-foreground">
          Sign in to your SeatSteal account
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {validationError && (
          <Alert variant="destructive">
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">
            Email Address
          </label>
          <div className="relative">
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
              placeholder="john@university.edu"
              className="pl-10"
              required
              disabled={isLoading}
            />
          </div>
        </div>

        <Button type="submit" className="w-full" disabled={isLoading || !email}>
          {isLoading ? (
            <>
              <Spinner className="size-4 mr-2" />
              Sending Magic Link...
            </>
          ) : (
            "Send Magic Link"
          )}
        </Button>

        <div className="text-center text-xs text-muted-foreground">
          We&apos;ll send you a secure link to sign in instantly. No password
          required. Must use a valid .edu email address.
        </div>
      </form>
    </>
  );
}
