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
 * Check if user has premium features access (Plus or Pro)
 */
export function hasPremiumAccess(tier: SubscriptionTier): boolean {
  return tier === "plus" || tier === "pro";
}

/**
 * Check if user has Pro-exclusive features access
 */
export function hasProAccess(tier: SubscriptionTier): boolean {
  return tier === "pro";
}

/**
 * Check if user is a Pro subscriber
 * Alias for hasProAccess, can be used with tier directly
 */
export function isProUser(tier: SubscriptionTier | null | undefined): boolean {
  return tier === "pro";
}
