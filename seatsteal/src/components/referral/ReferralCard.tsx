import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Gift, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

interface ReferralData {
  referralCode: string;
  referralUrl: string;
  totalReferrals: number;
  successfulReferrals: number;
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

    try {
      await navigator.clipboard.writeText(referralData.referralCode);
      setCopied(true);
      toast.success("Code copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Failed to copy code");
    }
  };

  const copyMessage = async () => {
    if (!referralData) return;

    const message = `I use SeatSteal to get notifications for course seat openings. Sign up with my referral code and we both get a free week of Pro! ${referralData.referralUrl}`;

    try {
      await navigator.clipboard.writeText(message);
      toast.success("Message copied!");
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
        <div>
          <p className="text-xs text-muted-foreground">
            You'll both get one free week of Pro! Your friend must sign up for
            an account. Misuse of referrals will result in deletion of all
            applicable accounts.
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            {referralData.successfulReferrals === 0
              ? "No successful referrals yet."
              : `${referralData.successfulReferrals} successful referral${referralData.successfulReferrals !== 1 ? "s" : ""}!`}
          </p>
        </div>

        <div className="flex gap-2">
          <Input
            value={referralData.referralCode}
            readOnly
            className="text-sm font-mono h-8"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={copyToClipboard}
            className="h-8 px-2"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={copyMessage}
          className="w-full h-8"
        >
          <Copy className="h-4 w-4 mr-2" />
          Copy message
        </Button>
      </CardContent>
    </Card>
  );
}
