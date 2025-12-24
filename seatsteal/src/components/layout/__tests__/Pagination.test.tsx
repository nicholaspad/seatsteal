import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pagination } from "../Pagination";

describe("Pagination", () => {
  describe("Rendering", () => {
    it("does not render when totalPages is 1", () => {
      const { container } = render(
        <Pagination currentPage={1} totalPages={1} onPageChange={vi.fn()} />,
      );

      expect(container.firstChild).toBeNull();
    });

    it("does not render when totalPages is 0", () => {
      const { container } = render(
        <Pagination currentPage={1} totalPages={0} onPageChange={vi.fn()} />,
      );

      expect(container.firstChild).toBeNull();
    });

    it("renders with 2 pages", () => {
      render(
        <Pagination currentPage={1} totalPages={2} onPageChange={vi.fn()} />,
      );

      expect(screen.getByLabelText("Go to page 1")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 2")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to previous page")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to next page")).toBeInTheDocument();
    });

    it("renders page numbers with default siblingCount", () => {
      render(
        <Pagination currentPage={5} totalPages={10} onPageChange={vi.fn()} />,
      );

      // With siblingCount=1 and currentPage=5, should show 4, 5, 6
      expect(screen.getByLabelText("Go to page 4")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 5")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 6")).toBeInTheDocument();
    });

    it("renders with custom siblingCount", () => {
      render(
        <Pagination
          currentPage={5}
          totalPages={20}
          onPageChange={vi.fn()}
          siblingCount={2}
        />,
      );

      // With siblingCount=2 and currentPage=5, should show 3, 4, 5, 6, 7
      expect(screen.getByLabelText("Go to page 3")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 4")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 5")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 6")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 7")).toBeInTheDocument();
    });
  });

  describe("Navigation Buttons", () => {
    it("disables Previous button on first page", () => {
      render(
        <Pagination currentPage={1} totalPages={5} onPageChange={vi.fn()} />,
      );

      const prevButton = screen.getByLabelText("Go to previous page");
      expect(prevButton).toBeDisabled();
    });

    it("enables Previous button when not on first page", () => {
      render(
        <Pagination currentPage={2} totalPages={5} onPageChange={vi.fn()} />,
      );

      const prevButton = screen.getByLabelText("Go to previous page");
      expect(prevButton).not.toBeDisabled();
    });

    it("disables Next button on last page", () => {
      render(
        <Pagination currentPage={5} totalPages={5} onPageChange={vi.fn()} />,
      );

      const nextButton = screen.getByLabelText("Go to next page");
      expect(nextButton).toBeDisabled();
    });

    it("enables Next button when not on last page", () => {
      render(
        <Pagination currentPage={4} totalPages={5} onPageChange={vi.fn()} />,
      );

      const nextButton = screen.getByLabelText("Go to next page");
      expect(nextButton).not.toBeDisabled();
    });

    it("calls onPageChange with previous page when Previous is clicked", async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={3}
          totalPages={5}
          onPageChange={onPageChange}
        />,
      );

      const prevButton = screen.getByLabelText("Go to previous page");
      await user.click(prevButton);

      expect(onPageChange).toHaveBeenCalledWith(2);
    });

    it("calls onPageChange with next page when Next is clicked", async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={3}
          totalPages={5}
          onPageChange={onPageChange}
        />,
      );

      const nextButton = screen.getByLabelText("Go to next page");
      await user.click(nextButton);

      expect(onPageChange).toHaveBeenCalledWith(4);
    });
  });

  describe("Page Number Clicks", () => {
    it("calls onPageChange with correct page when page number is clicked", async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={1}
          totalPages={5}
          onPageChange={onPageChange}
        />,
      );

      // With currentPage=1 and siblingCount=1, page 2 should be visible
      const page2Button = screen.getByLabelText("Go to page 2");
      await user.click(page2Button);

      expect(onPageChange).toHaveBeenCalledWith(2);
    });

    it("highlights current page", () => {
      render(
        <Pagination currentPage={3} totalPages={5} onPageChange={vi.fn()} />,
      );

      const currentPageButton = screen.getByLabelText("Go to page 3");
      expect(currentPageButton).toHaveAttribute("aria-current", "page");
    });
  });

  describe("Ellipsis Display", () => {
    it("shows ellipsis for pages with gaps", () => {
      const { container } = render(
        <Pagination currentPage={8} totalPages={15} onPageChange={vi.fn()} />,
      );

      // With siblingCount=1, currentPage=8 gives startPage=7
      // Ellipsis should appear (rendered as MoreHorizontal icon)
      const ellipsisContainers = container.querySelectorAll(
        ".flex.h-8.w-8.items-center.justify-center",
      );
      expect(ellipsisContainers.length).toBeGreaterThan(0);
    });

    it("shows ellipsis when there are many pages", () => {
      const { container } = render(
        <Pagination currentPage={3} totalPages={15} onPageChange={vi.fn()} />,
      );

      // With siblingCount=1, currentPage=3 gives endPage=4
      // Right ellipsis should appear since endPage (4) < totalPages - 1 (14)
      const ellipsisContainers = container.querySelectorAll(
        ".flex.h-8.w-8.items-center.justify-center",
      );
      expect(ellipsisContainers.length).toBeGreaterThan(0);
    });

    it("shows no ellipsis for small totalPages", () => {
      const { container } = render(
        <Pagination currentPage={2} totalPages={4} onPageChange={vi.fn()} />,
      );

      const ellipsisContainers = container.querySelectorAll(
        ".flex.h-8.w-8.items-center.justify-center",
      );
      expect(ellipsisContainers.length).toBe(0);
    });
  });

  describe("showFirstLast Prop", () => {
    it("shows first and last page buttons when showFirstLast is true", () => {
      render(
        <Pagination
          currentPage={5}
          totalPages={10}
          onPageChange={vi.fn()}
          showFirstLast={true}
        />,
      );

      expect(screen.getByLabelText("Go to page 1")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 10")).toBeInTheDocument();
    });

    it("does not duplicate first page button when currentPage is 1", () => {
      render(
        <Pagination
          currentPage={1}
          totalPages={10}
          onPageChange={vi.fn()}
          showFirstLast={true}
        />,
      );

      const page1Buttons = screen.getAllByLabelText("Go to page 1");
      // Should only have one button for page 1
      expect(page1Buttons).toHaveLength(1);
    });

    it("does not duplicate last page button when currentPage is last", () => {
      render(
        <Pagination
          currentPage={10}
          totalPages={10}
          onPageChange={vi.fn()}
          showFirstLast={true}
        />,
      );

      const page10Buttons = screen.getAllByLabelText("Go to page 10");
      // Should only have one button for page 10
      expect(page10Buttons).toHaveLength(1);
    });
  });

  describe("Edge Cases", () => {
    it("handles currentPage = 1, totalPages = 2", () => {
      const onPageChange = vi.fn();
      render(
        <Pagination
          currentPage={1}
          totalPages={2}
          onPageChange={onPageChange}
        />,
      );

      expect(screen.getByLabelText("Go to page 1")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 2")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to previous page")).toBeDisabled();
      expect(screen.getByLabelText("Go to next page")).not.toBeDisabled();
    });

    it("handles currentPage = totalPages", () => {
      render(
        <Pagination currentPage={5} totalPages={5} onPageChange={vi.fn()} />,
      );

      expect(screen.getByLabelText("Go to previous page")).not.toBeDisabled();
      expect(screen.getByLabelText("Go to next page")).toBeDisabled();
    });

    it("handles large totalPages (100)", () => {
      render(
        <Pagination
          currentPage={50}
          totalPages={100}
          onPageChange={vi.fn()}
        />,
      );

      // Should show pages around 50 (49, 50, 51 with siblingCount=1)
      expect(screen.getByLabelText("Go to page 49")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 50")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 51")).toBeInTheDocument();

      // Should not show all 100 pages
      expect(screen.queryByLabelText("Go to page 1")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Go to page 100")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA labels", () => {
      render(
        <Pagination currentPage={3} totalPages={5} onPageChange={vi.fn()} />,
      );

      expect(screen.getByLabelText("Go to previous page")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to next page")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 2")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 3")).toBeInTheDocument();
      expect(screen.getByLabelText("Go to page 4")).toBeInTheDocument();
    });

    it("has navigation landmark", () => {
      render(
        <Pagination currentPage={1} totalPages={3} onPageChange={vi.fn()} />,
      );

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveAttribute("aria-label", "Pagination");
    });

    it("marks current page with aria-current", () => {
      render(
        <Pagination currentPage={3} totalPages={5} onPageChange={vi.fn()} />,
      );

      const currentPage = screen.getByLabelText("Go to page 3");
      expect(currentPage).toHaveAttribute("aria-current", "page");

      const otherPage = screen.getByLabelText("Go to page 2");
      expect(otherPage).not.toHaveAttribute("aria-current");
    });
  });

  describe("Custom className", () => {
    it("applies custom className to container", () => {
      const { container } = render(
        <Pagination
          currentPage={1}
          totalPages={3}
          onPageChange={vi.fn()}
          className="custom-pagination"
        />,
      );

      const nav = container.querySelector("nav");
      expect(nav).toHaveClass("custom-pagination");
    });
  });
});
