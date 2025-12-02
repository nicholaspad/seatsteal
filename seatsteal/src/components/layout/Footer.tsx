import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

interface FooterProps {
  className?: string;
}

export function Footer({ className }: FooterProps) {
  return (
    <footer className={cn("border-t bg-black", className)}>
      <div className="container mx-auto px-4 py-2">
        <div className="flex justify-center items-center">
          {/* Links */}
          <div className="flex items-center space-x-6 text-xs">
            <Link
              to="/privacy"
              className="text-gray-400 hover:text-white transition-colors"
            >
              Privacy
            </Link>
            <Link
              to="/terms"
              className="text-gray-400 hover:text-white transition-colors"
            >
              Terms
            </Link>
            <a
              href="https://form.typeform.com/to/fz0mcjEn"
              className="text-gray-400 hover:text-white transition-colors"
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
