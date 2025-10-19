// Subscription tier constants that can be safely imported in client components
export type SubscriptionTier = "free" | "plus" | "pro";

export interface SubscriptionFeatures {
  analyticsAccess: boolean;
  checkFrequency: number; // minutes between checks
  maxSubscriptions: number;
  monthlyPrice: number; // price in dollars
}

/**
 * Get subscription features for a given tier (client-safe version)
 */
export function getSubscriptionFeatures(
  tier: SubscriptionTier,
): SubscriptionFeatures {
  switch (tier) {
    case "free":
      return {
        analyticsAccess: false,
        checkFrequency: 30, // 30 minutes
        maxSubscriptions: 1,
        monthlyPrice: 0,
      };
    case "plus":
      return {
        analyticsAccess: true,
        checkFrequency: 5, // 5 minutes
        maxSubscriptions: 5,
        monthlyPrice: 2,
      };
    case "pro":
      return {
        analyticsAccess: true,
        checkFrequency: 1, // 1 minute
        maxSubscriptions: 20,
        monthlyPrice: 5,
      };
    default:
      return getSubscriptionFeatures("free");
  }
}
