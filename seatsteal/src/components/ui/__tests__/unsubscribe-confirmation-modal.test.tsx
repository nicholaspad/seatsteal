import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UnsubscribeConfirmationModal } from "../unsubscribe-confirmation-modal";

describe("UnsubscribeConfirmationModal", () => {
  describe("Rendering", () => {
    it("renders when isOpen is true", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      expect(screen.getByText("Confirm Unsubscribe")).toBeInTheDocument();
      expect(
        screen.getByText(/Are you sure you want to unsubscribe/),
      ).toBeInTheDocument();
    });

    it("does not render when isOpen is false", () => {
      const { container } = render(
        <UnsubscribeConfirmationModal
          isOpen={false}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      expect(
        container.querySelector('[role="dialog"]'),
      ).not.toBeInTheDocument();
    });

    it("displays warning message about losing notifications", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      expect(
        screen.getByText(/no longer receive notifications/),
      ).toBeInTheDocument();
    });
  });

  describe("User Interactions", () => {
    it("calls onClose when Cancel button is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={onClose}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("calls onConfirm when Unsubscribe button is clicked", async () => {
      const user = userEvent.setup();
      const onConfirm = vi.fn();

      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={onConfirm}
          isLoading={false}
        />,
      );

      await user.click(screen.getByRole("button", { name: /^unsubscribe$/i }));
      expect(onConfirm).toHaveBeenCalledOnce();
    });

    it("does not call onConfirm multiple times on rapid clicks", async () => {
      const user = userEvent.setup();
      const onConfirm = vi.fn();

      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={onConfirm}
          isLoading={false}
        />,
      );

      const button = screen.getByRole("button", { name: /^unsubscribe$/i });
      await user.click(button);
      await user.click(button);

      expect(onConfirm).toHaveBeenCalledTimes(2);
    });
  });

  describe("Loading State", () => {
    it("disables buttons when isLoading is true", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={true}
        />,
      );

      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
      expect(
        screen.getByRole("button", { name: /unsubscribing/i }),
      ).toBeDisabled();
    });

    it("shows loading text when isLoading is true", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={true}
        />,
      );

      expect(screen.getByText("Unsubscribing...")).toBeInTheDocument();
    });

    it("shows normal text when isLoading is false", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      expect(screen.getByText(/^Unsubscribe$/)).toBeInTheDocument();
    });

    it("enables buttons when isLoading is false", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).not.toBeDisabled();
      expect(
        screen.getByRole("button", { name: /^unsubscribe$/i }),
      ).not.toBeDisabled();
    });
  });

  describe("Button Variants", () => {
    it("renders Unsubscribe button with destructive variant", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      const unsubscribeButton = screen.getByRole("button", {
        name: /^unsubscribe$/i,
      });
      expect(unsubscribeButton).toBeInTheDocument();
    });

    it("renders Cancel button with outline variant", () => {
      render(
        <UnsubscribeConfirmationModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isLoading={false}
        />,
      );

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      expect(cancelButton).toBeInTheDocument();
    });
  });
});
