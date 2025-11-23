import { LoaderIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function Spinner({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof LoaderIcon>) {
  return (
    <LoaderIcon
      role="status"
      aria-label="Loading"
      className={cn("size-4 animate-spin text-white", className)}
      {...props}
    />
  );
}
