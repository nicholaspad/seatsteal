import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mail } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { EmailSchema } from "@/lib/validation";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

export function AdminLoginForm() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [validationError, setValidationError] = useState("");

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
      const response = await fetchWithToasts("/api/auth/admin-signin", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMsg = data.detail || data.error || "";
        // Parse error message for rate limiting
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
          setError(errorMsg || "Failed to send admin magic link");
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
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Login link sent to <strong>{email}</strong>.
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
            placeholder=""
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
            Logging in...
          </>
        ) : (
          <>Login</>
        )}
      </Button>
    </form>
  );
}
