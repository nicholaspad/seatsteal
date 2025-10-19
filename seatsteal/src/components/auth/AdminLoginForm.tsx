import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mail, Loader2, Shield } from "lucide-react";
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
        setError(data.error || "Failed to send admin magic link");
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
          <div className="mt-2 p-4 bg-blue-100 dark:bg-blue-900/30 rounded-full">
            <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
        <div className="space-y-2">
          <h3 className="font-medium">Check Your Email</h3>
          <p className="text-sm text-muted-foreground">
            We&apos;ve sent an admin magic link to <strong>{email}</strong>.
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
        <label htmlFor="email" className="text-sm font-medium">
          Administrator Email
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
            placeholder="admin@example.com"
            className="pl-10"
            required
            disabled={isLoading}
          />
        </div>
      </div>

      <Button type="submit" className="w-full" disabled={isLoading || !email}>
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Sending Admin Link...
          </>
        ) : (
          <>
            <Shield className="w-4 h-4 mr-2" />
            Send Admin Magic Link
          </>
        )}
      </Button>

      <div className="text-center text-xs text-muted-foreground">
        Admin access only. Your email must be registered as an administrator.
      </div>
    </form>
  );
}
