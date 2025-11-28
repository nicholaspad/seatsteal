/**
 * Check if we're in a Vercel preview environment.
 */
const isVercelPreview = (): boolean => {
  return import.meta.env.VERCEL_ENV === "preview";
};

/**
 * Get the API base URL, automatically detecting Vercel preview deployments.
 * In preview environments, constructs the corresponding backend preview URL.
 */
const getApiBaseUrl = (): string => {
  const branch = import.meta.env.VERCEL_GIT_COMMIT_REF;

  if (isVercelPreview() && branch) {
    // Sanitize branch name to match Vercel's URL format
    const sanitizedBranch = branch.toLowerCase().replace(/[^a-z0-9-]/g, "-");
    return `https://seatsteal-backend-git-${sanitizedBranch}-seatsteal.vercel.app`;
  }

  return import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";
};

/**
 * Get the Vercel protection bypass secret for preview deployments.
 * Returns undefined if not in preview or secret not configured.
 */
const getVercelBypassSecret = (): string | undefined => {
  if (isVercelPreview()) {
    return import.meta.env.VERCEL_AUTOMATION_BYPASS_SECRET || undefined;
  }
  return undefined;
};

export const config = {
  supabase: {
    url: import.meta.env.VITE_SUPABASE_URL || "",
    anonKey: import.meta.env.VITE_SUPABASE_ANON_KEY || "",
  },
  api: {
    baseUrl: getApiBaseUrl(),
    /** Bypass secret for Vercel-protected preview deployments */
    vercelBypassSecret: getVercelBypassSecret(),
  },
} as const;
