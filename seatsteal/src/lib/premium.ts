// Premium subscription utilities
// TODO: Integrate with actual payment/subscription system

import {
  getSubscriptionFeatures,
  type SubscriptionTier,
  type SubscriptionFeatures,
} from "./subscription-constants";

export type { SubscriptionTier };

export interface UserSubscription {
  tier: SubscriptionTier;
  expiresAt?: Date;
  features: SubscriptionFeatures;
}

/**
 * Get subscription features for a given tier
 */
export { getSubscriptionFeatures };

/**
 * Check if user has premium features access
 */
export function hasPremiumAccess(tier: SubscriptionTier): boolean {
  return tier === "plus" || tier === "pro";
}
