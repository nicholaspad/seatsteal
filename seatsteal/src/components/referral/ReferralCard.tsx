import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Gift, Copy, Check, Users } from "lucide-react";
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
      await navigator.clipboard.writeText(referralData.referralUrl);
      setCopied(true);
      toast.success("Link copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Failed to copy link");
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
          Refer a Friend
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          You both get 100% off your first month (monthly plans only)
        </p>

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

        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Users className="h-3 w-3" />
          <span>{referralData.successfulReferrals}/5 successful referrals</span>
        </div>

        <p className="text-xs text-muted-foreground italic border-t pt-2">
          Max 5 referrals per user. Misuse may result in closure of all
          applicable accounts.
        </p>
      </CardContent>
    </Card>
  );
}
