import { useState } from "react";
import { useHistory } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, ArrowRight, Loader2 } from "lucide-react";
import { getSubscriptionFeatures } from "@/lib/subscription-constants";
import { supabase } from "@/lib/supabase";
import { fetchWithToasts } from "@/lib/api";
import { toast } from "sonner";
import { isValidStripeUrl } from "@/lib/security";

export function PricingTiers() {
  const history = useHistory();
  const [loading, setLoading] = useState<string | null>(null);

  const freeFeatures = getSubscriptionFeatures("free");
  const plusFeatures = getSubscriptionFeatures("plus");
  const proFeatures = getSubscriptionFeatures("pro");

  const tiers = [
    {
      id: "free",
      name: "Free",
      price: `$${freeFeatures.monthlyPrice}`,
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
      price: `$${plusFeatures.monthlyPrice}`,
      features: [
        `Monitor ${plusFeatures.maxSubscriptions} sections`,
        `Checks every ${plusFeatures.checkFrequency} minutes`,
        "Email + SMS notifications",
        "Section enrollment analytics",
      ],
      cta: "Subscribe",
      popular: true,
    },
    {
      id: "pro",
      name: "Pro",
      price: `$${proFeatures.monthlyPrice}`,
      features: [
        `Monitor ${proFeatures.maxSubscriptions} sections`,
        `Checks every ${proFeatures.checkFrequency} minute`,
        "Email + SMS notifications",
        "Section enrollment analytics",
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
          body: JSON.stringify({ tier: tierId }),
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
            <CardTitle>{tier.name}</CardTitle>
            <div className="text-3xl font-bold">
              {tier.price}
              <span className="text-lg font-normal text-muted-foreground">
                /month
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            <ul className="space-y-2 flex-1">
              {tier.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
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
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
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
  );
}
