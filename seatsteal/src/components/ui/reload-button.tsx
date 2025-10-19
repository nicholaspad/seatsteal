"use client";

import { Button } from "@/components/ui/button";

interface ReloadButtonProps {
  children: React.ReactNode;
  variant?:
    | "default"
    | "destructive"
    | "outline"
    | "secondary"
    | "ghost"
    | "link";
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
}

export function ReloadButton({
  children,
  variant = "outline",
  size = "default",
  className,
}: ReloadButtonProps) {
  return (
    <Button
      variant={variant}
      size={size}
      className={className}
      onClick={() => window.location.reload()}
    >
      {children}
    </Button>
  );
}
