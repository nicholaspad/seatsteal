import { vi } from "vitest";

export const mockSupabaseUser = {
  id: "test-user-id",
  email: "test@university.edu",
  app_metadata: {},
  user_metadata: {},
  aud: "authenticated",
  created_at: "2024-01-01T00:00:00Z",
};

export const mockSupabaseSession = {
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  expires_in: 3600,
  token_type: "bearer",
  user: mockSupabaseUser,
};

export const createMockSupabase = (
  options: { authenticated?: boolean } = {},
) => ({
  auth: {
    getUser: vi.fn().mockResolvedValue({
      data: { user: options.authenticated ? mockSupabaseUser : null },
      error: options.authenticated ? null : { message: "Not authenticated" },
    }),
    getSession: vi.fn().mockResolvedValue({
      data: { session: options.authenticated ? mockSupabaseSession : null },
      error: null,
    }),
    onAuthStateChange: vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    }),
    signInWithOtp: vi.fn().mockResolvedValue({ data: {}, error: null }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
  },
});

export const supabase = createMockSupabase({ authenticated: false });
