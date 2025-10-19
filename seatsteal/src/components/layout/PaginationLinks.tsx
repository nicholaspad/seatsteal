import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaginationLinksProps {
  currentPage: number;
  totalPages: number;
  className?: string;
  showFirstLast?: boolean;
  siblingCount?: number;
  basePath?: string;
  searchParams?: URLSearchParams;
}

export function PaginationLinks({
  currentPage,
  totalPages,
  className,
  showFirstLast = false,
  siblingCount = 1,
  basePath = "",
  searchParams,
}: PaginationLinksProps) {
  // Don't render pagination if there's only one page or no pages
  if (totalPages <= 1) {
    return null;
  }

  const range = (start: number, end: number) => {
    const length = end - start + 1;
    return Array.from({ length }, (_, idx) => idx + start);
  };

  const startPage = Math.max(1, currentPage - siblingCount);
  const endPage = Math.min(totalPages, currentPage + siblingCount);

  const showLeftEllipsis = startPage > 2;
  const showRightEllipsis = endPage < totalPages - 1;

  const pageNumbers = range(startPage, endPage);

  const createPageUrl = (page: number) => {
    const url = new URLSearchParams(searchParams);
    if (page === 1) {
      url.delete("page");
    } else {
      url.set("page", page.toString());
    }
    const query = url.toString();
    return basePath + (query ? `?${query}` : "");
  };

  return (
    <nav
      className={cn("flex items-center justify-center gap-1", className)}
      aria-label="Pagination"
    >
      {/* Previous button */}
      <Button
        variant="outline"
        size="sm"
        asChild={currentPage > 1}
        disabled={currentPage <= 1}
        aria-label="Go to previous page"
        className="h-8 w-8 p-0"
      >
        {currentPage > 1 ? (
          <Link to={createPageUrl(currentPage - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Link>
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </Button>

      {/* First page */}
      {showFirstLast && currentPage > 2 && (
        <>
          <Button
            variant={1 === currentPage ? "default" : "outline"}
            size="sm"
            asChild
            className="h-8 w-8 p-0"
            aria-label="Go to page 1"
          >
            <Link to={createPageUrl(1)}>1</Link>
          </Button>
          {showLeftEllipsis && (
            <div className="flex h-8 w-8 items-center justify-center">
              <MoreHorizontal className="h-4 w-4" />
            </div>
          )}
        </>
      )}

      {/* Left ellipsis (without first page) */}
      {!showFirstLast && showLeftEllipsis && (
        <div className="flex h-8 w-8 items-center justify-center">
          <MoreHorizontal className="h-4 w-4" />
        </div>
      )}

      {/* Page numbers */}
      {pageNumbers.map((pageNumber) => (
        <Button
          key={pageNumber}
          variant={pageNumber === currentPage ? "default" : "outline"}
          size="sm"
          asChild={pageNumber !== currentPage}
          className="h-8 w-8 p-0"
          aria-label={`Go to page ${pageNumber}`}
          aria-current={pageNumber === currentPage ? "page" : undefined}
        >
          {pageNumber === currentPage ? (
            <span>{pageNumber}</span>
          ) : (
            <Link to={createPageUrl(pageNumber)}>{pageNumber}</Link>
          )}
        </Button>
      ))}

      {/* Right ellipsis (without last page) */}
      {!showFirstLast && showRightEllipsis && (
        <div className="flex h-8 w-8 items-center justify-center">
          <MoreHorizontal className="h-4 w-4" />
        </div>
      )}

      {/* Last page */}
      {showFirstLast && currentPage < totalPages - 1 && (
        <>
          {showRightEllipsis && (
            <div className="flex h-8 w-8 items-center justify-center">
              <MoreHorizontal className="h-4 w-4" />
            </div>
          )}
          <Button
            variant={totalPages === currentPage ? "default" : "outline"}
            size="sm"
            asChild
            className="h-8 w-8 p-0"
            aria-label={`Go to page ${totalPages}`}
          >
            <Link to={createPageUrl(totalPages)}>{totalPages}</Link>
          </Button>
        </>
      )}

      {/* Next button */}
      <Button
        variant="outline"
        size="sm"
        asChild={currentPage < totalPages}
        disabled={currentPage >= totalPages}
        aria-label="Go to next page"
        className="h-8 w-8 p-0"
      >
        {currentPage < totalPages ? (
          <Link to={createPageUrl(currentPage + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Link>
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
      </Button>
    </nav>
  );
}
