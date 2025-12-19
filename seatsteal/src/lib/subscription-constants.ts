// Subscription tier constants that can be safely imported in client components
export type SubscriptionTier = "free" | "plus" | "pro";
export type BillingInterval = "monthly" | "annual";

export interface SubscriptionFeatures {
  analyticsAccess: boolean;
  checkFrequency: number; // minutes between checks
  maxSubscriptions: number;
  monthlyPrice: number; // price in dollars
  annualPrice: number; // annual price in dollars (with discount)
  // Pro-exclusive features
  watcherCountAccess: boolean; // Can see how many users are watching each section
  priorityNotifications: boolean; // Gets notified before Plus users
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
        annualPrice: 0,
        watcherCountAccess: false,
        priorityNotifications: false,
      };
    case "plus":
      return {
        analyticsAccess: false,
        checkFrequency: 5, // 5 minutes
        maxSubscriptions: 5,
        monthlyPrice: 1,
        annualPrice: 10, // ~17% savings vs $12/year
        watcherCountAccess: false,
        priorityNotifications: false,
      };
    case "pro":
      return {
        analyticsAccess: true,
        checkFrequency: 1, // 1 minute
        maxSubscriptions: 20,
        monthlyPrice: 4,
        annualPrice: 40, // ~17% savings vs $48/year
        watcherCountAccess: true,
        priorityNotifications: true,
      };
    default:
      return getSubscriptionFeatures("free");
  }
}
