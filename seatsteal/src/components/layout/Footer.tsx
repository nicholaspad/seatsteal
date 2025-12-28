import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

interface FooterProps {
  className?: string;
}

export function Footer({ className }: FooterProps) {
  return (
    <footer
      className={cn(
        "border-t bg-black pb-[env(safe-area-inset-bottom)]",
        className,
      )}
    >
      <div className="container mx-auto px-4 py-3">
        <div className="flex justify-center items-center">
          <div className="flex items-center space-x-6 text-xs">
            <Link
              to="/privacy"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Privacy
            </Link>
            <Link
              to="/terms"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Terms
            </Link>
            <a
              href="https://forms.gle/4SJq1aqGULZEBKi36"
              className="text-muted-foreground hover:text-foreground transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              Feedback
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
