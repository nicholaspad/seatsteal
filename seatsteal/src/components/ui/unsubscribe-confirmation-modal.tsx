"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CollegeBadge } from "@/components/college/CollegeBadge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { College } from "@/types/api";

interface UnsubscribeConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  courseCode: string;
  courseTitle: string;
  sectionCode?: string;
  college: College;
}

export function UnsubscribeConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  courseCode,
  courseTitle,
  sectionCode,
  college,
}: UnsubscribeConfirmationModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-6">
        <DialogHeader>
          <DialogTitle>Confirm Unsubscribe</DialogTitle>
          <DialogDescription>
            Are you sure you want to unsubscribe from this course? You will no
            longer receive notifications when seats become available.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-semibold">{courseCode}</h3>
            {sectionCode && (
              <Badge variant="outline" className="text-xs">
                {sectionCode}
              </Badge>
            )}
            <CollegeBadge college={college} className="text-xs" />
          </div>
          <p className="text-sm text-muted-foreground">{courseTitle}</p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? "Unsubscribing..." : "Unsubscribe"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
