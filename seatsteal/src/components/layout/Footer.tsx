import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

interface FooterProps {
  className?: string;
}

export function Footer({ className }: FooterProps) {
  return (
    <footer
      className={cn("border-t bg-black", className)}
      style={{
        paddingBottom: "max(2rem, env(safe-area-inset-bottom, 2rem))",
      }}
    >
      <div className="container mx-auto px-4 pt-2">
        <div className="flex justify-center items-center min-h-[40px]">
          {/* Links */}
          <div className="flex items-center gap-4 sm:gap-6 text-xs flex-wrap justify-center">
            <Link
              to="/privacy"
              className="text-gray-400 hover:text-white transition-colors whitespace-nowrap"
            >
              Privacy
            </Link>
            <Link
              to="/terms"
              className="text-gray-400 hover:text-white transition-colors whitespace-nowrap"
            >
              Terms
            </Link>
            <a
              href="https://form.typeform.com/to/fz0mcjEn"
              className="text-gray-400 hover:text-white transition-colors whitespace-nowrap"
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
