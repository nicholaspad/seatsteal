import { createContext, useContext, useEffect, useState, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { fetchWithToasts } from "@/lib/api";
import type { User } from "@supabase/supabase-js";
import type { SubscriptionTier } from "@/lib/subscription-constants";
import type { SubscriptionStatus } from "@/types/api";

interface UserProfile {
  email: string;
  phone: string;
  role: string;
  collegeId: number;
  collegeName: string;
}

interface SessionContextType {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  profileLoading: boolean;
  subscriptionTier: SubscriptionTier;
  tierLoading: boolean;
  subscriptionStatus: SubscriptionStatus | null;
  subscriptionStatusLoading: boolean;
  refreshSubscriptionStatus: () => Promise<void>;
  refreshSubscriptionTier: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(true);
  const [subscriptionTier, setSubscriptionTier] =
    useState<SubscriptionTier>("free");
  const [tierLoading, setTierLoading] = useState(true);
  const [subscriptionStatus, setSubscriptionStatus] =
    useState<SubscriptionStatus | null>(null);
  const [subscriptionStatusLoading, setSubscriptionStatusLoading] =
    useState(true);

  // Prevent race conditions between initial auth and auth state changes
  const initializingRef = useRef(false);
  // Track if initial data load has completed (to avoid showing loading skeleton on background refreshes)
  const initialLoadCompleteRef = useRef(false);

  // Function to fetch user's profile from backend
  const fetchUserProfile = async () => {
    try {
      setProfileLoading(true);
      const response = await fetchWithToasts("/api/user/settings");

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setProfile(data.data);
        } else {
          throw new Error(data.error || "Failed to fetch profile");
        }
      } else {
        throw new Error("Failed to fetch user profile");
      }
    } catch {
      // Clear profile on error
      setProfile(null);
    } finally {
      setProfileLoading(false);
    }
  };

  // Function to fetch user's subscription tier
  const fetchSubscriptionTier = async (userId?: string) => {
    const effectiveUserId = userId || user?.id;
    if (!effectiveUserId) {
      setTierLoading(false);
      return;
    }

    try {
      setTierLoading(true);
      const response = await fetchWithToasts("/api/user/subscription-tier");

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setSubscriptionTier(data.data.tier);
        } else {
          throw new Error(data.error || "Failed to fetch tier");
        }
      } else {
        throw new Error("Failed to fetch subscription tier");
      }
    } catch {
      // Default to free on error
      setSubscriptionTier("free");
    } finally {
      setTierLoading(false);
    }
  };

  // Function to fetch user's subscription status (count, limit, tier)
  const fetchSubscriptionStatus = async () => {
    try {
      setSubscriptionStatusLoading(true);
      const response = await fetchWithToasts("/api/subscriptions/status");

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setSubscriptionStatus(data.data);
        } else {
          throw new Error(data.error || "Failed to fetch subscription status");
        }
      } else {
        throw new Error("Failed to fetch subscription status");
      }
    } catch {
      // Default to null on error
      setSubscriptionStatus(null);
    } finally {
      setSubscriptionStatusLoading(false);
    }
  };

  useEffect(() => {
    // Get initial user with secure validation
    const initializeAuth = async () => {
      // Prevent multiple simultaneous auth operations
      if (initializingRef.current) {
        return;
      }

      initializingRef.current = true;

      try {
        const {
          data: { user },
          error: userError,
        } = await supabase.auth.getUser();

        if (userError || !user) {
          setUser(null);
          setProfile(null);
          setLoading(false);
          setProfileLoading(false);
          setTierLoading(false);
          setSubscriptionStatusLoading(false);
          return;
        }

        setUser(user);
        setLoading(false);
        // Fetch profile, tier, and subscription status in parallel for better performance
        Promise.all([
          fetchUserProfile(),
          fetchSubscriptionTier(user.id),
          fetchSubscriptionStatus(),
        ]).then(() => {
          initialLoadCompleteRef.current = true;
        });
      } catch {
        setUser(null);
        setProfile(null);
        setLoading(false);
        setProfileLoading(false);
        setTierLoading(false);
        setSubscriptionStatusLoading(false);
      } finally {
        initializingRef.current = false;
      }
    };

    initializeAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "SIGNED_OUT" || !session?.user) {
        setUser(null);
        setProfile(null);
        setSubscriptionTier("free");
        setSubscriptionStatus(null);
        setProfileLoading(false);
        setTierLoading(false);
        setSubscriptionStatusLoading(false);
        setLoading(false);
        // Reset initial load flag so next sign-in shows proper loading state
        initialLoadCompleteRef.current = false;
        return;
      }

      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
        // Prevent race condition with initial auth
        if (initializingRef.current) {
          return;
        }

        // Skip refetching if initial load is complete - both TOKEN_REFRESHED and
        // SIGNED_IN can fire on tab visibility change, and we don't want to
        // flash loading skeletons or refetch data that's already loaded.
        const skipRefetch = initialLoadCompleteRef.current;

        // Use session data directly if available to avoid redundant getUser() call
        if (session?.user) {
          // Only update user state if it's a different user to avoid triggering
          // re-renders and effect dependencies (e.g., Courses.tsx refetch)
          setUser((prevUser) =>
            prevUser?.id === session.user.id ? prevUser : session.user,
          );
          setLoading(false);

          if (!skipRefetch) {
            // Fetch profile, tier, and subscription status in parallel for better performance
            Promise.all([
              fetchUserProfile(),
              fetchSubscriptionTier(session.user.id),
              fetchSubscriptionStatus(),
            ]);
          }
          return;
        }

        // Fallback to getUser() if no session data (shouldn't happen)
        try {
          const {
            data: { user },
            error: userError,
          } = await supabase.auth.getUser();

          if (userError) {
            setUser(null);
            setProfile(null);
            setSubscriptionTier("free");
            setSubscriptionStatus(null);
            setProfileLoading(false);
            setTierLoading(false);
            setSubscriptionStatusLoading(false);
          } else if (!user) {
            setUser(null);
            setProfile(null);
            setSubscriptionTier("free");
            setSubscriptionStatus(null);
            setProfileLoading(false);
            setTierLoading(false);
            setSubscriptionStatusLoading(false);
          } else {
            // Only update user state if it's a different user to avoid triggering
            // re-renders and effect dependencies
            setUser((prevUser) => (prevUser?.id === user.id ? prevUser : user));

            if (!skipRefetch) {
              // Fetch profile, tier, and subscription status in parallel for better performance
              Promise.all([
                fetchUserProfile(),
                fetchSubscriptionTier(user.id),
                fetchSubscriptionStatus(),
              ]);
            }
          }
          setLoading(false);
        } catch (error) {
          setUser(null);
          setProfile(null);
          setSubscriptionTier("free");
          setSubscriptionStatus(null);
          setProfileLoading(false);
          setTierLoading(false);
          setSubscriptionStatusLoading(false);
          setLoading(false);
        }
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  return (
    <SessionContext.Provider
      value={{
        user,
        profile,
        loading,
        profileLoading,
        subscriptionTier,
        tierLoading,
        subscriptionStatus,
        subscriptionStatusLoading,
        refreshSubscriptionStatus: fetchSubscriptionStatus,
        refreshSubscriptionTier: fetchSubscriptionTier,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};

// Custom hook for easy access to subscription tier data
export const useSubscriptionTier = () => {
  const { subscriptionTier, tierLoading } = useSession();
  return { subscriptionTier, tierLoading };
};

// Custom hook for subscription status (count, limit, can subscribe)
export const useSubscriptionStatus = () => {
  const {
    subscriptionStatus,
    subscriptionStatusLoading,
    refreshSubscriptionStatus,
  } = useSession();
  return {
    subscriptionStatus,
    subscriptionStatusLoading,
    refreshSubscriptionStatus,
  };
};
