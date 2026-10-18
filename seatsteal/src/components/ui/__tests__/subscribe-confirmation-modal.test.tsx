import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SubscribeConfirmationModal } from "../subscribe-confirmation-modal";

describe("SubscribeConfirmationModal", () => {
  it("promises SMS only where available", () => {
    render(
      <SubscribeConfirmationModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
      />,
    );

    expect(screen.getByText(/one email notification/i)).toBeInTheDocument();
    expect(
      screen.getByText(/one SMS notification where available/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/you will also receive/)).not.toBeInTheDocument();
  });
});
