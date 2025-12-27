import { useState } from "react";
import { useHistory } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PlusBadgeSvg, ProBadgeSvg } from "@/components/ui/svg-badges";
import { CheckCircle, ArrowRight } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import {
  getSubscriptionFeatures,
  type BillingInterval,
} from "@/lib/subscription-constants";
import { supabase } from "@/lib/supabase";
import { fetchWithToasts } from "@/lib/api";
import { toast } from "sonner";
import { isValidStripeUrl } from "@/lib/security";

export function PricingTiers() {
  const history = useHistory();
  const [loading, setLoading] = useState<string | null>(null);
  const [billingInterval, setBillingInterval] =
    useState<BillingInterval>("monthly");

  const freeFeatures = getSubscriptionFeatures("free");
  const plusFeatures = getSubscriptionFeatures("plus");
  const proFeatures = getSubscriptionFeatures("pro");

  const isAnnual = billingInterval === "annual";

  const tiers = [
    {
      id: "free",
      name: "Free",
      price: `$${freeFeatures.monthlyPrice}`,
      period: "/month",
      features: [
        `Monitor ${freeFeatures.maxSubscriptions} section`,
        "Email notifications",
        `Checks every ${freeFeatures.checkFrequency} minutes`,
      ],
      cta: "Get Started",
      popular: false,
    },
    {
      id: "plus",
      name: "Plus",
      price: isAnnual
        ? `$${plusFeatures.annualPrice}`
        : `$${plusFeatures.monthlyPrice}`,
      period: isAnnual ? "/year" : "/month",
      savings: isAnnual ? "Save $3" : null,
      features: [
        `Monitor ${plusFeatures.maxSubscriptions} sections`,
        `Checks every ${plusFeatures.checkFrequency} minutes`,
        "Email + SMS notifications",
      ],
      cta: "Subscribe",
      popular: true,
    },
    {
      id: "pro",
      name: "Pro",
      price: isAnnual
        ? `$${proFeatures.annualPrice}`
        : `$${proFeatures.monthlyPrice}`,
      period: isAnnual ? "/year" : "/month",
      savings: isAnnual ? "Save $12" : null,
      features: [
        `Monitor ${proFeatures.maxSubscriptions} sections`,
        `Checks every minute`,
        "Priority email + SMS notifications (30 seconds before non-Pro users)",
        "Subscription and notification analytics",
      ],
      cta: "Subscribe",
      popular: false,
    },
  ];

  const handleSubscribe = async (tierId: string) => {
    if (tierId === "free") {
      // Redirect to login for free tier
      history.push("/login");
      return;
    }

    setLoading(tierId);

    try {
      // Check if user is authenticated first
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        // Redirect to login if not authenticated
        history.push("/login");
        return;
      }

      // Create checkout session
      const response = await fetchWithToasts(
        "/api/stripe/create-checkout-session",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ tier: tierId, interval: billingInterval }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to create checkout session");
      }

      // Validate Stripe URL before redirecting to prevent phishing
      const sessionUrl = data.data.sessionUrl;
      if (!isValidStripeUrl(sessionUrl)) {
        throw new Error("Invalid checkout session URL");
      }

      // Redirect to Stripe checkout
      window.location.href = sessionUrl;
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to start subscription process",
      );
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Billing Toggle */}
      <div className="flex flex-col items-center gap-2 mb-4">
        <div className="flex items-center gap-3">
          <span
            className={`text-sm ${billingInterval === "monthly" ? "font-medium" : "text-muted-foreground"}`}
          >
            Monthly
          </span>
          <button
            onClick={() => setBillingInterval(isAnnual ? "monthly" : "annual")}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              isAnnual ? "bg-primary" : "bg-muted"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                isAnnual ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <span
            className={`text-sm ${billingInterval === "annual" ? "font-medium" : "text-muted-foreground"}`}
          >
            Annual
          </span>
        </div>
        <span className="text-sm text-green-600 font-medium">
          Save 25% with an annual plan!
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tiers.map((tier) => (
          <Card
            key={tier.name}
            className={`relative flex flex-col h-full ${tier.popular ? "ring-2 ring-primary" : ""}`}
          >
            {tier.popular && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </span>
              </div>
            )}
            <CardHeader className="text-center">
              <CardTitle className="flex items-center justify-center gap-2">
                {tier.id === "plus" ? (
                  <PlusBadgeSvg />
                ) : tier.id === "pro" ? (
                  <ProBadgeSvg />
                ) : (
                  tier.name
                )}
              </CardTitle>
              <div className="flex items-center justify-center gap-2">
                <div className="text-3xl font-bold">
                  {tier.price}
                  <span className="text-lg font-normal text-muted-foreground">
                    {tier.period}
                  </span>
                </div>
                {tier.savings && (
                  <span className="flex items-center bg-green-600 text-white px-2 py-1 rounded-full text-xs font-medium">
                    {tier.savings}
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
              <ul className="space-y-2 flex-1">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 shrink-0 text-green-600 mt-0.5" />
                    <span className="text-sm">{feature}</span>
                  </li>
                ))}
              </ul>
              <Button
                className="w-full mt-4"
                variant={tier.popular ? "default" : "outline"}
                onClick={() => handleSubscribe(tier.id)}
                disabled={loading === tier.id}
              >
                {loading === tier.id ? (
                  <>
                    <Spinner className="size-4 mr-2" />
                    Loading...
                  </>
                ) : (
                  <>
                    {tier.cta}
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
