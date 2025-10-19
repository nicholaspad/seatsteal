import { CollegeFilter } from "@/components/course/college-filter";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useHistory } from "react-router-dom";
import { useState } from "react";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

export function CollegeSelectionForm() {
  const [selectedCollegeId, setSelectedCollegeId] = useState<
    number | undefined
  >(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const history = useHistory();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!selectedCollegeId) {
      setError("Please select a college");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await fetchWithToasts("/api/auth/update-college", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ collegeId: selectedCollegeId }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        history.push("/dashboard");
        window.location.reload(); // Refresh to update session
      } else {
        setError(data.error || "Failed to update college");
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

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-2 flex flex-col items-center">
        <label className="text-sm font-medium">Select Your College</label>
        <CollegeFilter
          value={selectedCollegeId}
          onValueChange={setSelectedCollegeId}
          placeholder="Choose your college..."
          showAllOption={false}
        />
      </div>

      <div className="space-y-3">
        <Button
          type="submit"
          className="w-full"
          disabled={isLoading || !selectedCollegeId}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Setting Up Account...
            </>
          ) : (
            "Continue to Dashboard"
          )}
        </Button>

        <p className="text-xs text-muted-foreground text-center">
          You can change your college selection later in your profile settings.
        </p>
      </div>
    </form>
  );
}
