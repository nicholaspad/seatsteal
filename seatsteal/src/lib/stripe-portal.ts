import { toast } from "sonner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { isValidStripeUrl } from "@/lib/security";

/**
 * Open the existing Stripe billing portal (same endpoint as
 * dashboard Manage subscription). return_url is /dashboard on the backend.
 */
export async function openStripeBillingPortal(): Promise<void> {
  try {
    const response = await fetchWithToasts(
      "/api/stripe/create-portal-session",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    if (!response.ok) {
      throw new Error("Failed to create portal session");
    }

    const data = (await response.json()) as {
      success?: boolean;
      error?: string;
      data?: { sessionUrl?: string };
    };

    if (!data.success) {
      throw new Error(data.error || "Failed to create portal session");
    }

    const sessionUrl = data.data?.sessionUrl;
    if (!sessionUrl || !isValidStripeUrl(sessionUrl)) {
      throw new Error("Invalid portal session URL");
    }

    window.location.href = sessionUrl;
  } catch (err) {
    if (err instanceof ServerErrorWithToast) {
      return;
    }
    toast.error(
      err instanceof Error
        ? err.message
        : "Failed to open billing portal. Please try again.",
    );
  }
}
