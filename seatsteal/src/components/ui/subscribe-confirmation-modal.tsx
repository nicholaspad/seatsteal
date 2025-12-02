"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
} from "@/components/ui/dialog";
import { Mail, MessageSquare } from "lucide-react";

interface SubscribeConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
}

export function SubscribeConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
}: SubscribeConfirmationModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-6 max-w-md">
        <DialogHeader className="space-y-3">
          <DialogDescription className="text-center">
            By subscribing, you agree to receive notifications when a seat
            becomes available in this class section.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-4">
          <div className="flex items-start gap-3 text-sm">
            <Mail className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
            <p className="text-muted-foreground">
              You will receive{" "}
              <strong className="text-foreground">
                one email notification
              </strong>{" "}
              when a seat opens up.
            </p>
          </div>
          <div className="flex items-start gap-3 text-sm">
            <MessageSquare className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
            <p className="text-muted-foreground">
              If you have provided a phone number in your account settings, you
              will also receive{" "}
              <strong className="text-foreground">one SMS notification</strong>.
              Message and data rates may apply.
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
            <p>
              <strong className="text-foreground">How to opt out:</strong> You
              can unsubscribe at any time by clicking "Unsubscribe" on this page
              or from your Dashboard. After notification, your subscription for
              this class section is automatically ended.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={isLoading}>
            {isLoading ? "Subscribing..." : "Subscribe"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
