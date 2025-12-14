import { describe, it, expect } from "vitest";
import {
  hasPremiumAccess,
  hasProAccess,
  isProUser,
  getSubscriptionFeatures,
} from "../premium";

describe("Premium Utilities", () => {
  describe("hasPremiumAccess", () => {
    it("returns false for free tier", () => {
      expect(hasPremiumAccess("free")).toBe(false);
    });

    it("returns true for plus tier", () => {
      expect(hasPremiumAccess("plus")).toBe(true);
    });

    it("returns true for pro tier", () => {
      expect(hasPremiumAccess("pro")).toBe(true);
    });
  });

  describe("hasProAccess", () => {
    it("returns false for free tier", () => {
      expect(hasProAccess("free")).toBe(false);
    });

    it("returns false for plus tier", () => {
      expect(hasProAccess("plus")).toBe(false);
    });

    it("returns true for pro tier", () => {
      expect(hasProAccess("pro")).toBe(true);
    });
  });

  describe("isProUser", () => {
    it("returns false for free tier", () => {
      expect(isProUser("free")).toBe(false);
    });

    it("returns false for plus tier", () => {
      expect(isProUser("plus")).toBe(false);
    });

    it("returns true for pro tier", () => {
      expect(isProUser("pro")).toBe(true);
    });

    it("returns false for null", () => {
      expect(isProUser(null)).toBe(false);
    });

    it("returns false for undefined", () => {
      expect(isProUser(undefined)).toBe(false);
    });
  });

  describe("getSubscriptionFeatures", () => {
    it("returns correct features for free tier", () => {
      const features = getSubscriptionFeatures("free");
      expect(features.maxSubscriptions).toBe(1);
      expect(features.checkFrequency).toBe(30);
      expect(features.analyticsAccess).toBe(false);
      expect(features.watcherCountAccess).toBe(false);
      expect(features.priorityNotifications).toBe(false);
    });

    it("returns correct features for plus tier", () => {
      const features = getSubscriptionFeatures("plus");
      expect(features.maxSubscriptions).toBe(5);
      expect(features.checkFrequency).toBe(5);
      expect(features.analyticsAccess).toBe(false);
      expect(features.watcherCountAccess).toBe(false);
      expect(features.priorityNotifications).toBe(false);
    });

    it("returns correct features for pro tier", () => {
      const features = getSubscriptionFeatures("pro");
      expect(features.maxSubscriptions).toBe(20);
      expect(features.checkFrequency).toBe(1);
      expect(features.analyticsAccess).toBe(true);
      expect(features.watcherCountAccess).toBe(true);
      expect(features.priorityNotifications).toBe(true);
    });
  });
});
