import { Link } from "react-router-dom";
import { Heart } from "lucide-react";
import { cn } from "@/lib/utils";

interface FooterProps {
  className?: string;
}

export function Footer({ className }: FooterProps) {
  const currentYear = new Date().getFullYear();

  return (
    <footer className={cn("border-t bg-black", className)}>
      <div className="container mx-auto px-4 py-6 pb-10 md:pb-6">
        <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          {/* Brand */}
          <div className="flex items-center space-x-2">
            <Link to="/" className="flex items-center space-x-2">
              <span className="font-semibold text-sm">seatsteal</span>
            </Link>
          </div>

          {/* Links */}
          <div className="flex items-center space-x-6 text-sm">
            <Link
              to="/privacy"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Privacy Policy
            </Link>
            <a
              href="https://form.typeform.com/to/fz0mcjEn"
              className="text-muted-foreground hover:text-foreground transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              Feedback
            </a>
          </div>

          {/* Copyright */}
          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
            <span>© {currentYear}</span>
            <Heart className="h-3 w-3 text-red-500" />
          </div>
        </div>
      </div>
    </footer>
  );
}
