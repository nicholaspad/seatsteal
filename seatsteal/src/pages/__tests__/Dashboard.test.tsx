import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import Dashboard from "../Dashboard";
import { renderAuthenticated } from "@/test/utils";
import {
  mockSubscriptionData,
  mockTrendsResponse,
  mockMultipleSubscriptions,
  mockEmptyTrendsResponse,
} from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// Import toast after mocking to get the mocked version
import { toast } from "sonner";

describe("Dashboard Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("shows loading skeleton while tier is loading", () => {
      renderAuthenticated(<Dashboard />, { tierLoading: true });

      // The loading skeleton has animate-pulse class
      const skeleton = document.querySelector(".animate-pulse");
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe("Rendering", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: [mockSubscriptionData] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        if (url.includes("/api/referrals")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  referralCode: "ABC123",
                  referralUrl: "https://seatsteal.app/?ref=ABC123",
                  totalReferrals: 0,
                  successfulReferrals: 0,
                },
              }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("renders the dashboard container", async () => {
      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByTestId("ion-page")).toBeInTheDocument();
      });
    });

    it("passes correct tier to UserDashboard", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });
  });

  describe("Tier Display", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/referrals")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  referralCode: "ABC123",
                  referralUrl: "https://seatsteal.app/?ref=ABC123",
                  totalReferrals: 0,
                  successfulReferrals: 0,
                },
              }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: [] }),
        } as Response);
      });
    });

    it("renders with free tier", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "free" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });

    it("renders with plus tier", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });

    it("renders with pro tier", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "pro" });

      await waitFor(() => {
        expect(screen.getByTestId("ion-content")).toBeInTheDocument();
      });
    });
  });

  describe("Subscriptions Display", () => {
    it("displays subscription cards with course info when subscriptions exist", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: mockMultipleSubscriptions,
              }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        if (url.includes("/api/referrals")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  referralCode: "ABC123",
                  referralUrl: "https://seatsteal.app/?ref=ABC123",
                  totalReferrals: 0,
                  successfulReferrals: 0,
                },
              }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        // Should show course codes from subscriptions
        expect(screen.getByText("CS101")).toBeInTheDocument();
        expect(screen.getByText("CS102")).toBeInTheDocument();
        expect(screen.getByText("CS201")).toBeInTheDocument();
      });
    });

    it("shows No Subscriptions Yet empty state with Browse Courses button", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText("No Subscriptions Yet")).toBeInTheDocument();
        expect(screen.getByText("Browse Courses")).toBeInTheDocument();
      });
    });

    it("displays Unsubscribe button on subscription cards", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: [mockSubscriptionData] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText("Unsubscribe")).toBeInTheDocument();
      });
    });
  });

  describe("Weekly Trend Chart", () => {
    it("displays recent notification trend chart", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({ success: true, data: [mockSubscriptionData] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        // Should show "Today" label for the most recent day
        expect(screen.getByText("Today")).toBeInTheDocument();
        // Should show the chart title
        expect(screen.getByText("Recent Notifications")).toBeInTheDocument();
      });
    });

    it("shows No recent notifications when all bars are zero", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(
          screen.getByText("No recent notifications."),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Tier Badge Display", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: [] }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("shows free tier badge for free tier users", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "free" });

      await waitFor(() => {
        expect(screen.getByText("Free")).toBeInTheDocument();
      });
    });

    it("shows plus tier badge for plus tier users", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

      await waitFor(() => {
        expect(screen.getByText("PLUS")).toBeInTheDocument();
      });
    });

    it("shows pro tier badge for pro tier users", async () => {
      renderAuthenticated(<Dashboard />, { subscriptionTier: "pro" });

      await waitFor(() => {
        expect(screen.getByText("PRO")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("shows error card with Try Again button when subscription fetch fails", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/subscriptions")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () =>
              Promise.resolve({ success: false, error: "Server error" }),
          } as Response);
        }
        if (url.includes("/api/notifications/trends")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyTrendsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText("Error Loading Dashboard")).toBeInTheDocument();
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });
    });
  });

  describe("Manage Subscription Button", () => {
    describe("NO_STRIPE_CUSTOMER Error Handling", () => {
      beforeEach(() => {
        mockFetchWithToasts.mockImplementation((url: string) => {
          if (url.includes("/api/subscriptions")) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, data: [] }),
            } as Response);
          }
          if (url.includes("/api/notifications/trends")) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(mockEmptyTrendsResponse),
            } as Response);
          }
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true }),
          } as Response);
        });
      });

      it("shows custom toast with pricing link when no Stripe customer exists", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        // Wait for dashboard to render
        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock portal session API to return 404 with NO_STRIPE_CUSTOMER code
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: false,
            status: 404,
            json: () =>
              Promise.resolve({
                detail: {
                  code: "NO_STRIPE_CUSTOMER",
                  message:
                    "No Stripe customer found. Please create a subscription first.",
                },
              }),
          } as Response),
        );

        // Click Manage button
        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        // Wait for API call and toast
        await waitFor(() => {
          expect(toast.error).toHaveBeenCalled();
        });

        // Verify toast was called with correct duration
        const toastCall = (toast.error as any).mock.calls[0];
        expect(toastCall).toBeDefined();
        expect(toastCall[1]).toEqual({ duration: 5000 });

        // Verify the toast contains a React element (the JSX with the message and button)
        expect(toastCall[0]).toBeDefined();
      });

      it("shows generic error toast for 404 without NO_STRIPE_CUSTOMER code", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock portal session API to return generic 404
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: false,
            status: 404,
            json: () =>
              Promise.resolve({
                detail: "Some other 404 error",
              }),
          } as Response),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith(
            "Failed to create portal session",
          );
        });
      });

      it("shows generic error for 404 with detail.code that is not NO_STRIPE_CUSTOMER", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock portal session API to return 404 with different error code
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: false,
            status: 404,
            json: () =>
              Promise.resolve({
                detail: {
                  code: "SOME_OTHER_ERROR",
                  message: "Some other error message",
                },
              }),
          } as Response),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith(
            "Failed to create portal session",
          );
        });
      });

      it("handles JSON parse error gracefully", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock portal session API to return 404 with invalid JSON
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: false,
            status: 404,
            json: () => Promise.reject(new Error("Invalid JSON")),
          } as Response),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith(
            "Failed to create portal session",
          );
        });
      });

      it("shows generic error for non-404 errors", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock portal session API to return 500 error
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: false,
            status: 500,
            json: () =>
              Promise.resolve({
                detail: "Internal server error",
              }),
          } as Response),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith(
            "Failed to create portal session",
          );
        });
      });
    });

    describe("Successful Portal Session", () => {
      beforeEach(() => {
        mockFetchWithToasts.mockImplementation((url: string) => {
          if (url.includes("/api/subscriptions")) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, data: [] }),
            } as Response);
          }
          if (url.includes("/api/notifications/trends")) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(mockEmptyTrendsResponse),
            } as Response);
          }
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true }),
          } as Response);
        });
      });

      it("redirects to Stripe portal on success", async () => {
        // Mock window.location.href
        const originalLocation = window.location;
        delete (window as any).location;
        window.location = { href: "" } as any;

        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock successful portal session creation
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  sessionUrl: "https://billing.stripe.com/session/test123",
                },
              }),
          } as Response),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        await waitFor(() => {
          expect(window.location.href).toBe(
            "https://billing.stripe.com/session/test123",
          );
        });

        // Restore original location
        window.location = originalLocation;
      });

      it("shows error for invalid Stripe URL", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock portal session with invalid URL
        mockFetchWithToasts.mockImplementationOnce(() =>
          Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: {
                  sessionUrl: "https://malicious-site.com/fake-stripe",
                },
              }),
          } as Response),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith(
            "Invalid portal session URL",
          );
        });
      });
    });

    describe("Loading State", () => {
      beforeEach(() => {
        mockFetchWithToasts.mockImplementation((url: string) => {
          if (url.includes("/api/subscriptions")) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, data: [] }),
            } as Response);
          }
          if (url.includes("/api/notifications/trends")) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(mockEmptyTrendsResponse),
            } as Response);
          }
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true }),
          } as Response);
        });
      });

      it("shows loading state when manage button is clicked", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock a slow portal session creation
        mockFetchWithToasts.mockImplementationOnce(
          () =>
            new Promise((resolve) =>
              setTimeout(
                () =>
                  resolve({
                    ok: true,
                    json: () =>
                      Promise.resolve({
                        success: true,
                        data: {
                          sessionUrl:
                            "https://billing.stripe.com/session/test123",
                        },
                      }),
                  } as Response),
                100,
              ),
            ),
        );

        const manageButton = screen.getByText("Manage");
        fireEvent.click(manageButton);

        // Should show Loading... text
        await waitFor(() => {
          expect(screen.getByText("Loading...")).toBeInTheDocument();
        });
      });

      it("disables button while loading", async () => {
        renderAuthenticated(<Dashboard />, { subscriptionTier: "plus" });

        await waitFor(() => {
          expect(screen.getByText("Manage")).toBeInTheDocument();
        });

        // Mock a slow portal session creation
        mockFetchWithToasts.mockImplementationOnce(
          () =>
            new Promise((resolve) =>
              setTimeout(
                () =>
                  resolve({
                    ok: true,
                    json: () =>
                      Promise.resolve({
                        success: true,
                        data: {
                          sessionUrl:
                            "https://billing.stripe.com/session/test123",
                        },
                      }),
                  } as Response),
                100,
              ),
            ),
        );

        const manageButton = screen.getByText("Manage") as HTMLButtonElement;
        fireEvent.click(manageButton);

        // Button should be disabled while loading
        await waitFor(() => {
          const loadingButton = screen
            .getByText("Loading...")
            .closest("button") as HTMLButtonElement;
          expect(loadingButton).toBeDisabled();
        });
      });
    });
  });
});
