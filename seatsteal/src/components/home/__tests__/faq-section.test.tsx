import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { FAQSection } from "../faq-section";

describe("FAQSection", () => {
  it("describes alerts as email with SMS where available", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <FAQSection colleges={[]} />
      </MemoryRouter>,
    );

    await user.click(screen.getByText("How does SeatSteal work?"));

    expect(
      screen.getByText(/instant email notification \(SMS where available\)/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/via email or SMS/)).not.toBeInTheDocument();
  });
});
