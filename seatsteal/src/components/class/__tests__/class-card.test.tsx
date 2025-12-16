import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { ClassCard } from "../class-card";
import { customRender, mockUser, mockProfile } from "@/test/utils";
import type { ClassWithEnrollment } from "@/types/api";
import type { SubscriptionStatus } from "@/types/api";

// Mock the API module
vi.mock("@/lib/api", () => ({
  fetchWithToasts: vi.fn(),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

// Create a mock closed class
const mockClosedClass: ClassWithEnrollment = {
  classId: 1,
  courseId: 1,
  classNumber: "12345",
  sectionCode: "001",
  isActive: true,
  currentEnrollment: {
    enrollmentStatus: "closed",
    scrapedAt: "2024-01-01",
  },
};

// Create a mock open class
const mockOpenClass: ClassWithEnrollment = {
  ...mockClosedClass,
  currentEnrollment: {
    enrollmentStatus: "open",
    scrapedAt: "2024-01-01",
  },
};

// Create subscription status that allows subscribing (free tier, 0/1)
const canSubscribeStatus: SubscriptionStatus = {
  currentCount: 0,
  maxSubscriptions: 1,
  tier: "free",
  canSubscribe: true,
};

// Create subscription status at limit (free tier, 1/1)
const atLimitStatusFree: SubscriptionStatus = {
  currentCount: 1,
  maxSubscriptions: 1,
  tier: "free",
  canSubscribe: false,
};

// Create subscription status at limit (plus tier, 5/5)
const atLimitStatusPlus: SubscriptionStatus = {
  currentCount: 5,
  maxSubscriptions: 5,
  tier: "plus",
  canSubscribe: false,
};

// Create subscription status at limit (pro tier, 20/20)
const atLimitStatusPro: SubscriptionStatus = {
  currentCount: 20,
  maxSubscriptions: 20,
  tier: "pro",
  canSubscribe: false,
};

describe("ClassCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Subscription Button Visibility", () => {
    it("shows subscription button for closed classes when showSubscriptionButton is true", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
        },
      );

      expect(screen.getByText("Subscribe")).toBeInTheDocument();
    });

    it("does not show subscription button when showSubscriptionButton is false", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={false}
          subscriptionsLoading={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
        },
      );

      expect(screen.queryByText("Subscribe")).not.toBeInTheDocument();
    });
  });

  describe("Subscription Limit Behavior", () => {
    it("enables subscribe button when user can subscribe", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "free",
        },
      );

      const subscribeButton = screen.getByRole("button", {
        name: /subscribe/i,
      });
      expect(subscribeButton).not.toBeDisabled();
    });

    it("disables subscribe button when user is at limit", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: atLimitStatusFree,
          subscriptionTier: "free",
        },
      );

      // When at limit, the button has the limit message as aria-label
      const subscribeButton = screen.getByRole("button", {
        name: /reached your limit/i,
      });
      expect(subscribeButton).toBeDisabled();
    });

    it("shows unsubscribe button and keeps it enabled when user is at limit but already subscribed", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={true}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: atLimitStatusFree,
          subscriptionTier: "free",
        },
      );

      const unsubscribeButton = screen.getByRole("button", {
        name: /unsubscribe/i,
      });
      expect(unsubscribeButton).not.toBeDisabled();
    });
  });

  describe("Subscription Limit Tooltip Messages", () => {
    it("shows correct tooltip message for free tier at limit", async () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: atLimitStatusFree,
          subscriptionTier: "free",
        },
      );

      // The disabled button should have aria-label with the limit message
      const subscribeButton = screen.getByRole("button", {
        name: /reached your limit/i,
      });
      expect(subscribeButton).toHaveAttribute(
        "aria-label",
        expect.stringContaining("reached your limit of 1 subscription"),
      );
      expect(subscribeButton).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Upgrade to Plus/Pro"),
      );
    });

    it("shows correct tooltip message for plus tier at limit", async () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: atLimitStatusPlus,
          subscriptionTier: "plus",
        },
      );

      const subscribeButton = screen.getByRole("button", {
        name: /reached your limit/i,
      });
      expect(subscribeButton).toHaveAttribute(
        "aria-label",
        expect.stringContaining("reached your limit of 5 subscriptions"),
      );
      expect(subscribeButton).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Upgrade to Pro"),
      );
    });

    it("shows correct tooltip message for pro tier at limit (no upgrade suggestion)", async () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: atLimitStatusPro,
          subscriptionTier: "pro",
        },
      );

      const subscribeButton = screen.getByRole("button", {
        name: /reached your limit/i,
      });
      expect(subscribeButton).toHaveAttribute(
        "aria-label",
        expect.stringContaining("reached your limit of 20 subscriptions"),
      );
      // Pro tier should not have upgrade suggestion
      expect(subscribeButton).not.toHaveAttribute(
        "aria-label",
        expect.stringContaining("Upgrade"),
      );
    });
  });

  describe("Subscription Actions", () => {
    it("calls onSubscriptionChange when unsubscribing", async () => {
      const mockOnSubscriptionChange = vi.fn().mockResolvedValue(undefined);

      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={true}
          onSubscriptionChange={mockOnSubscriptionChange}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "free",
        },
      );

      const unsubscribeButton = screen.getByRole("button", {
        name: /unsubscribe/i,
      });
      fireEvent.click(unsubscribeButton);

      expect(mockOnSubscriptionChange).toHaveBeenCalledWith(
        mockClosedClass.classId,
        false,
      );
    });

    it("does not call onSubscriptionChange when at limit and trying to subscribe", async () => {
      const mockOnSubscriptionChange = vi.fn().mockResolvedValue(undefined);

      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
          onSubscriptionChange={mockOnSubscriptionChange}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: atLimitStatusFree,
          subscriptionTier: "free",
        },
      );

      // When at limit, the button has the limit message as aria-label
      const subscribeButton = screen.getByRole("button", {
        name: /reached your limit/i,
      });
      fireEvent.click(subscribeButton);

      expect(mockOnSubscriptionChange).not.toHaveBeenCalled();
    });
  });

  describe("Open Classes", () => {
    it("does not show subscription card for open classes", () => {
      customRender(
        <ClassCard
          class={mockOpenClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
        },
      );

      expect(
        screen.queryByText("Get notified when seats open"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Watcher Count Badge", () => {
    it("shows watcher count badge with 0 for pro users when watcher count is 0", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
          watcherCount={0}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "pro",
        },
      );

      expect(screen.getByText("0")).toBeInTheDocument();
    });

    it("shows watcher count badge with 1 when user is the only subscriber", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={true}
          watcherCount={1}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "pro",
        },
      );

      // Should show 1 total subscription
      expect(screen.getByText("1")).toBeInTheDocument();
    });

    it("shows watcher count badge with correct count when user is subscribed with others", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={true}
          watcherCount={5}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "pro",
        },
      );

      // Should show 5 total subscriptions
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("shows watcher count badge with correct count when user is not subscribed", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
          watcherCount={7}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "pro",
        },
      );

      expect(screen.getByText("7")).toBeInTheDocument();
    });

    it("does not show watcher count badge for non-pro users", () => {
      customRender(
        <ClassCard
          class={mockClosedClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
          watcherCount={5}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "free",
        },
      );

      // Should not show the eye icon badge with count
      expect(screen.queryByText("5")).not.toBeInTheDocument();
    });

    it("does not show watcher count badge for open classes", () => {
      customRender(
        <ClassCard
          class={mockOpenClass}
          showSubscriptionButton={true}
          subscriptionsLoading={false}
          isSubscribed={false}
          watcherCount={5}
        />,
        {
          user: mockUser,
          profile: mockProfile,
          subscriptionStatus: canSubscribeStatus,
          subscriptionTier: "pro",
        },
      );

      // Should not show the eye icon badge with count for open classes
      expect(screen.queryByText("5")).not.toBeInTheDocument();
    });
  });
});
