import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Gift, Copy, Check } from "lucide-react";
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

  const copyToClipboard = async () => {
    if (!referralData) return;

    const message = `I use SeatSteal to get notifications for course seat openings. Sign up with my referral code and we both get a free week of Pro! ${referralData.referral_url}`;

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
        <p className="text-xs text-muted-foreground">
          You'll both get one free week of Pro! Your friend must sign up for an
          account.
        </p>

        <div className="flex gap-2">
          <Textarea
            value={`I use SeatSteal to get notifications for course seat openings. Sign up with my referral code and we both get a free week of Pro! ${referralData.referral_url}`}
            readOnly
            className="text-xs resize-none text-white"
            rows={3}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={copyToClipboard}
            className="px-2 self-start"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">
          Misuse of referrals will result in deletion of all applicable
          accounts.
        </p>

        <p className="text-xs text-muted-foreground">
          {referralData.successful_referrals === 0
            ? "No successful referrals yet."
            : `${referralData.successful_referrals} successful referral${referralData.successful_referrals !== 1 ? "s" : ""}!`}
        </p>
      </CardContent>
    </Card>
  );
}
