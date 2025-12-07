import React, { createContext, useContext } from "react";
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

export const mockProfile: UserProfile = {
  email: "test@university.edu",
  phone: "1234567890",
  role: "user",
  collegeId: 1,
  collegeName: "Test University",
};

export const mockUser: User = {
  id: "test-user-id",
  email: "test@university.edu",
  app_metadata: {},
  user_metadata: {},
  aud: "authenticated",
  created_at: "2024-01-01T00:00:00Z",
} as User;

const MockSessionContext = createContext<SessionContextType | null>(null);

interface MockSessionProviderProps {
  children: React.ReactNode;
  user?: User | null;
  profile?: UserProfile | null;
  loading?: boolean;
  profileLoading?: boolean;
  subscriptionTier?: SubscriptionTier;
  tierLoading?: boolean;
}

export function MockSessionProvider({
  children,
  user = null,
  profile = null,
  loading = false,
  profileLoading = false,
  subscriptionTier = "free",
  tierLoading = false,
}: MockSessionProviderProps) {
  return (
    <MockSessionContext.Provider
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
    </MockSessionContext.Provider>
  );
}

export const useSession = () => {
  const context = useContext(MockSessionContext);
  if (context === null) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};

export const useSubscriptionTier = () => {
  const { subscriptionTier, tierLoading } = useSession();
  return { subscriptionTier, tierLoading };
};
