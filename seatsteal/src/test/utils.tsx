import React from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
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

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  user?: User | null;
  profile?: UserProfile | null;
  loading?: boolean;
  profileLoading?: boolean;
  subscriptionTier?: SubscriptionTier;
  tierLoading?: boolean;
  subscriptionStatus?: SubscriptionStatus | null;
  subscriptionStatusLoading?: boolean;
  initialRoute?: string;
  routerEntries?: string[];
}

export function customRender(
  ui: React.ReactElement,
  options: CustomRenderOptions = {},
) {
  const {
    user = null,
    profile = null,
    loading = false,
    profileLoading = false,
    subscriptionTier = "free",
    tierLoading = false,
    subscriptionStatus = null,
    subscriptionStatusLoading = false,
    routerEntries = [options.initialRoute || "/"],
    ...renderOptions
  } = options;

  // Configure the global mock session state directly
  globalThis.__mockSessionState = {
    user,
    profile,
    loading,
    profileLoading,
    subscriptionTier,
    tierLoading,
    subscriptionStatus,
    subscriptionStatusLoading,
  };

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={routerEntries}>
        <TooltipProvider>{children}</TooltipProvider>
      </MemoryRouter>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

export function renderAuthenticated(
  ui: React.ReactElement,
  options: Omit<CustomRenderOptions, "user" | "profile"> = {},
) {
  return customRender(ui, {
    user: mockUser,
    profile: mockProfile,
    ...options,
  });
}

export function renderAnonymous(
  ui: React.ReactElement,
  options: CustomRenderOptions = {},
) {
  return customRender(ui, {
    user: null,
    profile: null,
    ...options,
  });
}

export * from "@testing-library/react";
export { customRender as render };
