"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface UnsubscribeConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
}

export function UnsubscribeConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
}: UnsubscribeConfirmationModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-6">
        <DialogHeader>
          <DialogTitle>Confirm Unsubscribe</DialogTitle>
          <DialogDescription>
            Are you sure you want to unsubscribe from this section? You will no
            longer receive notifications when seats become available.
          </DialogDescription>
        </DialogHeader>

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
