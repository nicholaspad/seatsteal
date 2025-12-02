import { useEffect } from "react";

const BASE_TITLE = "SeatSteal";

interface DocumentMetaOptions {
  title: string;
  description?: string;
  suffix?: boolean;
}

/**
 * Updates the document title and meta description for SEO.
 * Note: For SPAs, search engines primarily use the initial HTML meta tags.
 * This hook improves user experience by updating the browser tab title
 * and can help with social sharing if users share from specific pages.
 *
 * @param options - Title and optional description
 */
export function useDocumentTitle({
  title,
  description,
  suffix = true,
}: DocumentMetaOptions) {
  useEffect(() => {
    // Update title
    const fullTitle = suffix ? `${title} | ${BASE_TITLE}` : title;
    document.title = fullTitle;

    // Update meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription && description) {
      metaDescription.setAttribute("content", description);
    }

    // Update OG title
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) {
      ogTitle.setAttribute("content", fullTitle);
    }

    // Update OG description
    const ogDescription = document.querySelector(
      'meta[property="og:description"]',
    );
    if (ogDescription && description) {
      ogDescription.setAttribute("content", description);
    }

    // Update Twitter title
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');
    if (twitterTitle) {
      twitterTitle.setAttribute("content", fullTitle);
    }

    // Update Twitter description
    const twitterDescription = document.querySelector(
      'meta[name="twitter:description"]',
    );
    if (twitterDescription && description) {
      twitterDescription.setAttribute("content", description);
    }

    // No cleanup needed - let each page set its own title
    // The initial HTML already has good defaults for crawlers
  }, [title, description, suffix]);
}

/**
 * Pre-defined SEO configurations for common pages
 */
export const SEO_CONFIGS = {
  home: {
    title:
      "SeatSteal - Course Enrollment Notifications | Get Notified When Seats Open",
    description:
      "Never miss a spot in your dream class. SeatSteal monitors college course availability and sends instant notifications when seats open. Support for 8+ universities. Free tier available.",
    suffix: false,
  },
  courses: {
    title: "Browse Courses",
    description:
      "Search and browse available courses at your university. Monitor class availability and get notified when seats open. Find courses at Brown, Cornell, Penn, USC, and more.",
  },
  login: {
    title: "Sign In",
    description:
      "Sign in to SeatSteal to start monitoring course availability and receive notifications when seats open in your classes.",
  },
  dashboard: {
    title: "Dashboard",
    description:
      "View and manage your course subscriptions. Track enrollment status and notification history.",
  },
  settings: {
    title: "Settings",
    description:
      "Manage your SeatSteal account settings, notification preferences, and subscription.",
  },
  privacy: {
    title: "Privacy Policy",
    description:
      "Learn how SeatSteal collects, uses, and protects your personal information.",
  },
  terms: {
    title: "Terms of Service",
    description:
      "Read the terms and conditions for using SeatSteal course notification service.",
  },
};
