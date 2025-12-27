import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PricingTiers } from "../pricing-tiers";
import { supabase } from "@/lib/supabase";

// Mock dependencies
vi.mock("@/lib/api");
vi.mock("sonner");

const mockPush = vi.fn();
vi.mock("react-router-dom", () => ({
  useHistory: () => ({ push: mockPush }),
}));

describe("PricingTiers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
    delete (window as any).location;
    (window as any).location = { href: "" };
  });

  describe("Rendering", () => {
    it("renders all three pricing tiers", () => {
      render(<PricingTiers />);

      expect(screen.getByText("Free")).toBeInTheDocument();
      expect(screen.getByText("PLUS")).toBeInTheDocument();
      expect(screen.getByText("PRO")).toBeInTheDocument();
    });

    it("displays monthly prices by default", () => {
      render(<PricingTiers />);

      expect(screen.getByText("$0")).toBeInTheDocument();
      expect(screen.getAllByText(/\/month/)).toHaveLength(3);
    });

    it("marks Plus tier as most popular", () => {
      render(<PricingTiers />);

      expect(screen.getByText("Most Popular")).toBeInTheDocument();
    });

    it("displays correct features for Free tier", () => {
      render(<PricingTiers />);

      expect(screen.getByText(/Monitor 1 section/)).toBeInTheDocument();
      expect(screen.getByText(/Email notifications/)).toBeInTheDocument();
    });

    it("displays correct features for Plus tier", () => {
      render(<PricingTiers />);

      expect(screen.getByText(/Monitor 5 sections/)).toBeInTheDocument();
      expect(
        screen.getByText(/Email \+ SMS notifications/),
      ).toBeInTheDocument();
    });

    it("displays Get Started button for Free tier", () => {
      render(<PricingTiers />);

      expect(
        screen.getByRole("button", { name: /get started/i }),
      ).toBeInTheDocument();
    });

    it("displays Subscribe buttons for paid tiers", () => {
      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      expect(subscribeButtons).toHaveLength(2); // Plus and Pro
    });
  });

  describe("Billing Toggle", () => {
    it("shows annual savings message", () => {
      render(<PricingTiers />);

      expect(
        screen.getByText("Save 25% with an annual plan!"),
      ).toBeInTheDocument();
    });

    it("highlights monthly label when monthly is selected", () => {
      render(<PricingTiers />);

      const monthlyLabel = screen.getByText("Monthly");
      expect(monthlyLabel).toHaveClass("font-medium");
    });
  });

  describe("Free Tier", () => {
    it("redirects to login when Get Started clicked", async () => {
      const user = userEvent.setup();

      render(<PricingTiers />);

      const getStartedButton = screen.getByRole("button", {
        name: /get started/i,
      });
      await user.click(getStartedButton);

      expect(mockPush).toHaveBeenCalledWith("/login");
    });

    it("does not show loading state for free tier", async () => {
      const user = userEvent.setup();

      render(<PricingTiers />);

      const getStartedButton = screen.getByRole("button", {
        name: /get started/i,
      });
      await user.click(getStartedButton);

      expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
    });
  });

  describe("Paid Tiers - Unauthenticated User", () => {
    it("redirects to login for unauthenticated user", async () => {
      const user = userEvent.setup();

      vi.mocked(supabase.auth.getUser).mockResolvedValue({
        data: { user: null },
        error: null,
      });

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]); // Click Plus

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/login");
      });
    });

    it("does not call API for unauthenticated user", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(supabase.auth.getUser).mockResolvedValue({
        data: { user: null },
        error: null,
      });

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/login");
      });

      expect(fetchWithToasts).not.toHaveBeenCalled();
    });
  });

  describe("Paid Tiers - Authenticated User", () => {
    beforeEach(() => {
      vi.mocked(supabase.auth.getUser).mockResolvedValue({
        data: {
          user: {
            id: "user123",
            email: "test@example.com",
            aud: "authenticated",
            created_at: "",
          },
        },
        error: null,
      });
    });

    it("creates checkout session for Plus tier with monthly billing", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: { sessionUrl: "https://checkout.stripe.com/test" },
        }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]); // Plus

      await waitFor(() => {
        expect(fetchWithToasts).toHaveBeenCalledWith(
          "/api/stripe/create-checkout-session",
          expect.objectContaining({
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tier: "plus", interval: "monthly" }),
          }),
        );
      });
    });

    it("creates checkout session for Pro tier with monthly billing", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: { sessionUrl: "https://checkout.stripe.com/test" },
        }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[1]); // Pro

      await waitFor(() => {
        expect(fetchWithToasts).toHaveBeenCalledWith(
          "/api/stripe/create-checkout-session",
          expect.objectContaining({
            body: JSON.stringify({ tier: "pro", interval: "monthly" }),
          }),
        );
      });
    });

    it("redirects to Stripe checkout on success", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      const stripeUrl = "https://checkout.stripe.com/test-session";
      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: { sessionUrl: stripeUrl },
        }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(window.location.href).toBe(stripeUrl);
      });
    });

    it("validates Stripe URL before redirecting", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");
      const { toast } = await import("sonner");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: { sessionUrl: "https://evil.com/phishing" },
        }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          "Invalid checkout session URL",
        );
      });

      expect(window.location.href).not.toBe("https://evil.com/phishing");
    });

    it("shows loading state while creating checkout session", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({
                    success: true,
                    data: { sessionUrl: "https://checkout.stripe.com/test" },
                  }),
                } as Response),
              100,
            );
          }),
      );

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      expect(screen.getByText("Loading...")).toBeInTheDocument();
    });

    it("disables button during loading", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({
                    success: true,
                    data: { sessionUrl: "https://checkout.stripe.com/test" },
                  }),
                } as Response),
              100,
            );
          }),
      );

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      const loadingButton = screen.getByText("Loading...").closest("button");
      expect(loadingButton).toBeDisabled();
    });
  });

  describe("Error Handling", () => {
    beforeEach(() => {
      vi.mocked(supabase.auth.getUser).mockResolvedValue({
        data: {
          user: {
            id: "user123",
            email: "test@example.com",
            aud: "authenticated",
            created_at: "",
          },
        },
        error: null,
      });
    });

    it("shows error toast when checkout session creation fails", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");
      const { toast } = await import("sonner");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: false,
        json: async () => ({ error: "Payment system unavailable" }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Payment system unavailable");
      });
    });

    it("shows generic error when no error message provided", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");
      const { toast } = await import("sonner");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: false,
        json: async () => ({}),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          "Failed to create checkout session",
        );
      });
    });

    it("clears loading state on error", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: false,
        json: async () => ({ error: "Error" }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
      });
    });

    it("handles network errors gracefully", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");
      const { toast } = await import("sonner");

      vi.mocked(fetchWithToasts).mockRejectedValue(new Error("Network error"));

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Network error");
      });
    });

    it("handles non-Error exceptions", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");
      const { toast } = await import("sonner");

      vi.mocked(fetchWithToasts).mockRejectedValue("String error");

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          "Failed to start subscription process",
        );
      });
    });
  });

  describe("UI Elements", () => {
    it("shows checkmark icons for features", () => {
      const { container } = render(<PricingTiers />);

      const checkIcons = container.querySelectorAll("svg");
      expect(checkIcons.length).toBeGreaterThan(0);
    });

    it("displays period labels correctly", () => {
      render(<PricingTiers />);

      const monthLabels = screen.getAllByText(/\/month/);
      expect(monthLabels).toHaveLength(3);
    });
  });

  describe("Multiple Tier Interactions", () => {
    beforeEach(() => {
      vi.mocked(supabase.auth.getUser).mockResolvedValue({
        data: {
          user: {
            id: "user123",
            email: "test@example.com",
            aud: "authenticated",
            created_at: "",
          },
        },
        error: null,
      });
    });

    it("only shows loading for clicked tier", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({
                    success: true,
                    data: { sessionUrl: "https://checkout.stripe.com/test" },
                  }),
                } as Response),
              100,
            );
          }),
      );

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });
      await user.click(subscribeButtons[0]); // Click Plus

      // Only Plus button should show loading
      expect(subscribeButtons[0]).toHaveTextContent("Loading...");
      expect(subscribeButtons[1]).not.toHaveTextContent("Loading...");
    });

    it("allows clicking different tiers in sequence", async () => {
      const user = userEvent.setup();
      const { fetchWithToasts } = await import("@/lib/api");

      vi.mocked(fetchWithToasts).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: { sessionUrl: "https://checkout.stripe.com/test" },
        }),
      } as Response);

      render(<PricingTiers />);

      const subscribeButtons = screen.getAllByRole("button", {
        name: /subscribe/i,
      });

      // Click Plus
      await user.click(subscribeButtons[0]);

      await waitFor(() => {
        expect(fetchWithToasts).toHaveBeenCalledWith(
          expect.anything(),
          expect.objectContaining({
            body: JSON.stringify({ tier: "plus", interval: "monthly" }),
          }),
        );
      });
    });
  });
});
