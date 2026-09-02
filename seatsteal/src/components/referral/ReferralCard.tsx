import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Gift, Copy, Check, Share2 } from "lucide-react";
import { toast } from "sonner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

interface ReferralData {
  referral_code: string;
  referral_url: string;
  total_referrals: number;
  successful_referrals: number;
}

export function ReferralCard() {
  const [referralData, setReferralData] = useState<ReferralData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchReferralData();
  }, []);

  const fetchReferralData = async () => {
    try {
      const response = await fetchWithToasts("/api/referrals/my-referral");
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setReferralData(data.data);
        }
      }
    } catch (err) {
      if (!(err instanceof ServerErrorWithToast)) {
        console.error("Failed to fetch referral data:", err);
      }
    } finally {
      setLoading(false);
    }
  };

  const getReferralMessage = () => {
    if (!referralData) return "";
    return `I use SeatSteal to get notifications for course seat openings. Sign up with my referral code and we both get a free week of Pro! ${referralData.referral_url}`;
  };

  const handleShare = async () => {
    if (!referralData) return;

    const message = getReferralMessage();

    if (navigator.share) {
      try {
        await navigator.share({
          title: "Join SeatSteal",
          text: message,
        });
        toast.success("Shared successfully!");
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          toast.error("Failed to share");
        }
      }
    } else {
      copyToClipboard();
    }
  };

  const copyToClipboard = async () => {
    if (!referralData) return;

    const message = getReferralMessage();

    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
      toast.success("Message copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Failed to copy message");
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-4">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-muted rounded w-3/4" />
            <div className="h-8 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!referralData) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Gift className="h-4 w-4" />
          Refer Friends
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Textarea
            value={getReferralMessage()}
            readOnly
            className="!text-[11px] resize-none text-white"
            rows={3}
          />
          <div className="flex flex-col gap-2">
            {"share" in navigator && (
              <Button
                variant="default"
                size="sm"
                onClick={handleShare}
                className="px-2"
              >
                <Share2 className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={copyToClipboard}
              className="px-2"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        <p className="text-xs text-muted-foreground">
          You'll both get a free week of Pro! If a subscription is already
          active, 7 free days will be added.{" "}
          {referralData.successful_referrals === 0
            ? "No successful referrals yet."
            : `You have ${referralData.successful_referrals} successful referral${referralData.successful_referrals !== 1 ? "s" : ""}!`}
        </p>

        <p className="text-xs text-muted-foreground">
          Misuse of referrals will result in deletion of all applicable
          accounts.
        </p>
      </CardContent>
    </Card>
  );
}
