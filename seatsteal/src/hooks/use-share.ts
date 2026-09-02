import { useState, useEffect } from "react";
import { toast } from "sonner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

export function useShare() {
  const [referralUrl, setReferralUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchReferralUrl();
  }, []);

  const fetchReferralUrl = async () => {
    try {
      const response = await fetchWithToasts("/api/referrals/my-referral");
      if (response.ok) {
        const data: {
          success: boolean;
          data?: { referral_url: string };
        } = await response.json();
        if (data.success && data.data) {
          setReferralUrl(data.data.referral_url);
        }
      }
    } catch (err) {
      if (!(err instanceof ServerErrorWithToast)) {
        console.error("Failed to fetch referral data:", err);
      }
    }
  };

  const shareCourse = async (
    courseCode: string,
    courseTitle: string,
    courseUrl: string,
  ) => {
    setLoading(true);
    try {
      const message = referralUrl
        ? `Check out ${courseCode} - ${courseTitle} on SeatSteal! Get instant notifications when seats open. Sign up with my link for a free week of Pro: ${referralUrl}`
        : `Check out ${courseCode} - ${courseTitle} on SeatSteal! Get instant notifications when seats open. ${window.location.origin}${courseUrl}`;

      if (navigator.share) {
        await navigator.share({
          title: `${courseCode} - ${courseTitle}`,
          text: message,
        });
        toast.success("Shared successfully!");
      } else {
        await navigator.clipboard.writeText(message);
        toast.success("Link copied to clipboard!");
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        toast.error("Failed to share");
      }
    } finally {
      setLoading(false);
    }
  };

  return { shareCourse, loading, hasReferralUrl: !!referralUrl };
}
