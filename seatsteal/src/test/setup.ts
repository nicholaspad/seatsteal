import "@testing-library/jest-dom";
import { vi } from "vitest";
import React from "react";
import type { User } from "@supabase/supabase-js";
import type { SubscriptionTier } from "@/lib/subscription-constants";

// Define types for global mock state
interface MockSessionState {
  user: User | null;
  profile: {
    email: string;
    phone: string;
    role: string;
    collegeId: number;
    collegeName: string;
  } | null;
  loading: boolean;
  profileLoading: boolean;
  subscriptionTier: SubscriptionTier;
  tierLoading: boolean;
}

// Attach mock state to globalThis so it can be accessed from vi.mock factories
declare global {
  // eslint-disable-next-line no-var
  var __mockSessionState: MockSessionState;
}

globalThis.__mockSessionState = {
  user: null,
  profile: null,
  loading: false,
  profileLoading: false,
  subscriptionTier: "free",
  tierLoading: false,
};

// Export for use in test utils
export const mockSessionState = globalThis.__mockSessionState;

// Reset function for beforeEach
export const resetMockSessionState = () => {
  globalThis.__mockSessionState.user = null;
  globalThis.__mockSessionState.profile = null;
  globalThis.__mockSessionState.loading = false;
  globalThis.__mockSessionState.profileLoading = false;
  globalThis.__mockSessionState.subscriptionTier = "free";
  globalThis.__mockSessionState.tierLoading = false;
};

// Mock window.matchMedia (needed for Ionic/theme detection)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock window.scrollTo
window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;

// Mock ResizeObserver (needed for many UI components)
globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock IntersectionObserver (needed for lazy loading)
globalThis.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
  root: null,
  rootMargin: "",
  thresholds: [],
  takeRecords: vi.fn(),
}));

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

// Mock Ionic React components globally
vi.mock("@ionic/react", () => ({
  IonPage: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "ion-page" }, children),
  IonContent: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
  }) =>
    React.createElement(
      "div",
      { "data-testid": "ion-content", className },
      children,
    ),
  IonApp: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "ion-app" }, children),
  IonRouterOutlet: ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      "div",
      { "data-testid": "ion-router-outlet" },
      children,
    ),
  setupIonicReact: vi.fn(),
}));

vi.mock("@ionic/react-router", () => ({
  IonReactRouter: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "ion-react-router" }, children),
}));

// Mock Supabase
vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: null },
        error: null,
      }),
      getSession: vi.fn().mockResolvedValue({
        data: { session: null },
        error: null,
      }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signInWithOtp: vi.fn().mockResolvedValue({ data: {}, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    },
  },
  signInWithMagicLink: vi.fn(),
  signInWithAdminMagicLink: vi.fn(),
  signOut: vi.fn(),
  getCurrentUser: vi.fn(),
  getCurrentSession: vi.fn(),
}));

// Mock SessionProvider - uses globalThis.__mockSessionState
vi.mock("@/components/providers/SessionProvider", () => ({
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
  useSession: () => globalThis.__mockSessionState,
  useSubscriptionTier: () => ({
    subscriptionTier: globalThis.__mockSessionState.subscriptionTier,
    tierLoading: globalThis.__mockSessionState.tierLoading,
  }),
}));

// Suppress console warnings in tests
vi.spyOn(console, "warn").mockImplementation(() => {});
