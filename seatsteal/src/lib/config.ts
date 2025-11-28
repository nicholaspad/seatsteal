/**
 * Get the API base URL, automatically detecting Vercel preview deployments.
 * In preview environments, constructs the corresponding backend preview URL.
 */
const getApiBaseUrl = (): string => {
  const vercelEnv = import.meta.env.VERCEL_ENV;
  const branch = import.meta.env.VERCEL_GIT_COMMIT_REF;

  if (vercelEnv === "preview" && branch) {
    // Sanitize branch name to match Vercel's URL format
    const sanitizedBranch = branch.toLowerCase().replace(/[^a-z0-9-]/g, "-");
    return `https://seatsteal-backend-git-${sanitizedBranch}-seatsteal.vercel.app`;
  }

  return import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";
};

export const config = {
  supabase: {
    url: import.meta.env.VITE_SUPABASE_URL || "",
    anonKey: import.meta.env.VITE_SUPABASE_ANON_KEY || "",
  },
  api: {
    baseUrl: getApiBaseUrl(),
  },
} as const;
