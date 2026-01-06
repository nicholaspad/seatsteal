import { createClient } from "@supabase/supabase-js";
import { config } from "./config";

if (!config.supabase.url) {
  throw new Error("VITE_SUPABASE_URL environment variable is required");
}

if (!config.supabase.anonKey) {
  throw new Error("VITE_SUPABASE_ANON_KEY environment variable is required");
}

export const supabase = createClient(
  config.supabase.url,
  config.supabase.anonKey,
);

// Helper function to sign in with magic link
export const signInWithMagicLink = async (email: string) => {
  return await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
    },
  });
};

// Helper function to sign in with admin magic link
export const signInWithAdminMagicLink = async (email: string) => {
  return await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback?admin=true`,
    },
  });
};

// Helper function to sign in with Google
export const signInWithGoogle = async () => {
  return await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
      scopes: "openid email",
    },
  });
};

// Helper function to sign out
export const signOut = async () => {
  return await supabase.auth.signOut();
};

// Helper function to get current user
export const getCurrentUser = async () => {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
};

// Helper function to get current user with secure validation
export const getCurrentSession = async () => {
  // Validate user securely - no getSession() calls
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  // Return only validated user data, no session metadata
  return userError || !user ? null : user;
};
