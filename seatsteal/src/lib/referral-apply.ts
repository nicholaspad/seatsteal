import { toast } from "sonner";
import { fetchWithToasts } from "@/lib/api";
import { logError } from "@/lib/logger";
import { openStripeBillingPortal } from "@/lib/stripe-portal";

export const REFERRAL_CODE_STORAGE_KEY = "referral_code";
export const REFERRAL_PAST_DUE_TOAST_SESSION_KEY =
  "referral_past_due_toast_shown";

async function readErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
  } catch {
    // Keep the fallback if the body isn't JSON.
  }
  return fallback;
}

function showPastDueToastOnce(detail: string): void {
  if (sessionStorage.getItem(REFERRAL_PAST_DUE_TOAST_SESSION_KEY)) {
    return;
  }
  sessionStorage.setItem(REFERRAL_PAST_DUE_TOAST_SESSION_KEY, "1");
  toast.error(detail, {
    duration: 12000,
    action: {
      label: "Update card",
      onClick: () => {
        void openStripeBillingPortal();
      },
    },
  });
}

/**
 * Apply a referral code stored in localStorage.
 * Keeps the code on 409 (past_due) and transient errors so we can retry
 * after the user updates their card. Clears it on success or terminal 400s.
 * The past_due toast is shown at most once per browser session.
 */
export async function applyStoredReferralCode(options?: {
  refreshSubscriptionTier?: () => Promise<void>;
}): Promise<void> {
  const storedReferralCode = localStorage.getItem(REFERRAL_CODE_STORAGE_KEY);
  if (!storedReferralCode) {
    return;
  }

  try {
    const response = await fetchWithToasts("/api/referrals/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ referral_code: storedReferralCode }),
    });

    if (response.ok) {
      toast.success("🎉 Your referral has been applied!");
      localStorage.removeItem(REFERRAL_CODE_STORAGE_KEY);
      sessionStorage.removeItem(REFERRAL_PAST_DUE_TOAST_SESSION_KEY);
      await options?.refreshSubscriptionTier?.();
      return;
    }

    const detail = await readErrorDetail(
      response,
      "Failed to apply referral code",
    );

    if (response.status === 409) {
      showPastDueToastOnce(detail);
      return;
    }

    toast.error(detail);
    if (response.status === 400) {
      localStorage.removeItem(REFERRAL_CODE_STORAGE_KEY);
    }
  } catch (err) {
    logError("Failed to apply referral code", err);
  }
}
