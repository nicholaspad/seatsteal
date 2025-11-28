import { createContext, useContext, useEffect, useState, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { fetchWithToasts } from "@/lib/api";
import { PushNotificationService } from "@/lib/push-notifications";
import type { User } from "@supabase/supabase-js";
import type { SubscriptionTier } from "@/lib/subscription-constants";

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

  // Prevent race conditions between initial auth and auth state changes
  const initializingRef = useRef(false);

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
  const fetchSubscriptionTier = async (userId: string) => {
    if (!userId) {
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
          return;
        }

        setUser(user);
        setLoading(false);
        fetchUserProfile();
        fetchSubscriptionTier(user.id);

        // Initialize push notifications for authenticated user
        PushNotificationService.initialize().catch((error) => {
          console.error("Failed to initialize push notifications:", error);
        });
      } catch {
        setUser(null);
        setProfile(null);
        setLoading(false);
        setProfileLoading(false);
        setTierLoading(false);
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
        setProfileLoading(false);
        setTierLoading(false);
        setLoading(false);

        // Cleanup push notifications on sign out
        PushNotificationService.cleanup().catch((error) => {
          console.error("Failed to cleanup push notifications:", error);
        });
        return;
      }

      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
        // Prevent race condition with initial auth
        if (initializingRef.current) {
          return;
        }

        // Use session data directly if available to avoid redundant getUser() call
        if (session?.user) {
          setUser(session.user);
          setLoading(false);
          fetchUserProfile();
          fetchSubscriptionTier(session.user.id);

          // Initialize push notifications for authenticated user
          PushNotificationService.initialize().catch((error) => {
            console.error("Failed to initialize push notifications:", error);
          });
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
            setProfileLoading(false);
            setTierLoading(false);
          } else if (!user) {
            setUser(null);
            setProfile(null);
            setSubscriptionTier("free");
            setProfileLoading(false);
            setTierLoading(false);
          } else {
            setUser(user);
            fetchUserProfile();
            fetchSubscriptionTier(user.id);

            // Initialize push notifications for authenticated user
            PushNotificationService.initialize().catch((error) => {
              console.error("Failed to initialize push notifications:", error);
            });
          }
          setLoading(false);
        } catch (error) {
          setUser(null);
          setProfile(null);
          setSubscriptionTier("free");
          setProfileLoading(false);
          setTierLoading(false);
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
