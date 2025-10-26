import { createContext, useContext, useEffect, useState, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { fetchWithToasts } from "@/lib/api";
import type { User } from "@supabase/supabase-js";
import type { SubscriptionTier } from "@/lib/subscription-constants";

interface SessionContextType {
  user: User | null;
  loading: boolean;
  subscriptionTier: SubscriptionTier;
  tierLoading: boolean;
}

const SessionContext = createContext<SessionContextType | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [subscriptionTier, setSubscriptionTier] =
    useState<SubscriptionTier>("free");
  const [tierLoading, setTierLoading] = useState(true);

  // Prevent race conditions between initial auth and auth state changes
  const initializingRef = useRef(false);

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
          setLoading(false);
          setTierLoading(false);
          return;
        }

        setUser(user);
        setLoading(false);
        fetchSubscriptionTier(user.id);
      } catch {
        setUser(null);
        setLoading(false);
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
        setSubscriptionTier("free");
        setTierLoading(false);
        setLoading(false);
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
          fetchSubscriptionTier(session.user.id);
          return;
        }

        // Fallback to getUser() if no session data (shouldn't happen)
        try {
          const {
            data: { user },
            error: userError,
          } = await supabase.auth.getUser();

          if (userError || !user) {
            setUser(null);
            setSubscriptionTier("free");
            setTierLoading(false);
          } else {
            setUser(user);
            fetchSubscriptionTier(user.id);
          }
          setLoading(false);
        } catch {
          setUser(null);
          setSubscriptionTier("free");
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
      value={{ user, loading, subscriptionTier, tierLoading }}
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
