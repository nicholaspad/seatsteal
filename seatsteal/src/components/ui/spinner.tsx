import { IonSpinner } from "@ionic/react";

import { cn } from "@/lib/utils";

export function Spinner({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"div">) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn("size-4", className)}
      {...props}
    >
      <IonSpinner name="crescent" />
    </div>
  );
}
