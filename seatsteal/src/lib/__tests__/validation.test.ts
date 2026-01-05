import { describe, it, expect } from "vitest";
import {
  IdSchema,
  UuidSchema,
  EmailSchema,
  PhoneSchema,
  SubscriptionRequestSchema,
  SubscriptionUpdateSchema,
  UserUpdateSchema,
  CollegeUpdateSchema,
  PaginationSchema,
  CourseQuerySchema,
  NotificationRequestSchema,
} from "../validation";

describe("Validation Schemas", () => {
  describe("IdSchema", () => {
    it("accepts positive integers", () => {
      expect(IdSchema.parse(1)).toBe(1);
      expect(IdSchema.parse(100)).toBe(100);
      expect(IdSchema.parse(999999)).toBe(999999);
    });

    it("rejects zero", () => {
      expect(() => IdSchema.parse(0)).toThrow();
    });

    it("rejects negative integers", () => {
      expect(() => IdSchema.parse(-1)).toThrow();
      expect(() => IdSchema.parse(-100)).toThrow();
    });

    it("rejects floating point numbers", () => {
      expect(() => IdSchema.parse(1.5)).toThrow();
      expect(() => IdSchema.parse(3.14)).toThrow();
    });

    it("rejects strings", () => {
      expect(() => IdSchema.parse("1")).toThrow();
    });

    it("rejects null and undefined", () => {
      expect(() => IdSchema.parse(null)).toThrow();
      expect(() => IdSchema.parse(undefined)).toThrow();
    });
  });

  describe("UuidSchema", () => {
    it("accepts valid UUIDs", () => {
      const validUuid = "550e8400-e29b-41d4-a716-446655440000";
      expect(UuidSchema.parse(validUuid)).toBe(validUuid);
    });

    it("accepts UUIDs in different formats", () => {
      expect(
        UuidSchema.parse("123e4567-e89b-12d3-a456-426614174000"),
      ).toBeTruthy();
    });

    it("rejects invalid UUID formats", () => {
      expect(() => UuidSchema.parse("not-a-uuid")).toThrow();
      expect(() => UuidSchema.parse("123-456-789")).toThrow();
      expect(() => UuidSchema.parse("")).toThrow();
    });

    it("rejects non-string values", () => {
      expect(() => UuidSchema.parse(123)).toThrow();
      expect(() => UuidSchema.parse(null)).toThrow();
    });
  });

  describe("EmailSchema", () => {
    it("accepts valid email addresses", () => {
      expect(EmailSchema.parse("user@example.com")).toBe("user@example.com");
      expect(EmailSchema.parse("student@university.edu")).toBe(
        "student@university.edu",
      );
      expect(EmailSchema.parse("john@school.edu")).toBe("john@school.edu");
    });

    it("accepts emails with numbers", () => {
      expect(EmailSchema.parse("student123@university.edu")).toBe(
        "student123@university.edu",
      );
    });

    it("rejects emails with + character", () => {
      expect(() => EmailSchema.parse("user+tag@example.com")).toThrow();
      expect(() => EmailSchema.parse("student+tag@university.edu")).toThrow();
    });

    it("rejects emails with dots in username", () => {
      expect(() => EmailSchema.parse("first.last@example.com")).toThrow();
      expect(() => EmailSchema.parse("john.doe@school.edu")).toThrow();
    });

    it("allows dots in domain part", () => {
      expect(EmailSchema.parse("student@sub.university.edu")).toBe(
        "student@sub.university.edu",
      );
    });

    it("rejects invalid email formats", () => {
      expect(() => EmailSchema.parse("notanemail")).toThrow();
      expect(() => EmailSchema.parse("@example.com")).toThrow();
      expect(() => EmailSchema.parse("user@")).toThrow();
      expect(() => EmailSchema.parse("")).toThrow();
    });
  });

  describe("PhoneSchema", () => {
    describe("valid phone numbers", () => {
      it("accepts US phone numbers", () => {
        expect(PhoneSchema.parse("1234567890")).toBe("1234567890");
        expect(PhoneSchema.parse("123-456-7890")).toBe("123-456-7890");
      });

      it("accepts phone numbers with country code", () => {
        expect(PhoneSchema.parse("+11234567890")).toBe("+11234567890");
        expect(PhoneSchema.parse("+44 1234 567890")).toBe("+44 1234 567890");
      });

      it("accepts phone numbers with parentheses", () => {
        expect(PhoneSchema.parse("(123) 456-7890")).toBe("(123) 456-7890");
      });

      it("accepts phone numbers with spaces", () => {
        expect(PhoneSchema.parse("123 456 7890")).toBe("123 456 7890");
      });

      it("accepts undefined (optional)", () => {
        expect(PhoneSchema.parse(undefined)).toBeUndefined();
      });
    });

    describe("invalid phone numbers", () => {
      it("rejects too short numbers", () => {
        expect(() => PhoneSchema.parse("123")).toThrow();
        expect(() => PhoneSchema.parse("12345")).toThrow();
      });

      it("rejects too long numbers", () => {
        expect(() => PhoneSchema.parse("1234567890123456")).toThrow();
      });

      it("rejects numbers with invalid characters", () => {
        expect(() => PhoneSchema.parse("123-456-abcd")).toThrow();
        expect(() => PhoneSchema.parse("phone#123456")).toThrow();
      });

      it("rejects empty string", () => {
        expect(() => PhoneSchema.parse("")).toThrow();
      });
    });
  });

  describe("SubscriptionRequestSchema", () => {
    it("accepts valid subscription request", () => {
      const valid = { classId: 1, collegeId: 2 };
      expect(SubscriptionRequestSchema.parse(valid)).toEqual(valid);
    });

    it("rejects missing classId", () => {
      expect(() => SubscriptionRequestSchema.parse({ collegeId: 1 })).toThrow();
    });

    it("rejects missing collegeId", () => {
      expect(() => SubscriptionRequestSchema.parse({ classId: 1 })).toThrow();
    });

    it("rejects invalid IDs", () => {
      expect(() =>
        SubscriptionRequestSchema.parse({ classId: -1, collegeId: 1 }),
      ).toThrow();
      expect(() =>
        SubscriptionRequestSchema.parse({ classId: 1, collegeId: 0 }),
      ).toThrow();
    });
  });

  describe("SubscriptionUpdateSchema", () => {
    it("accepts valid isActive boolean", () => {
      expect(SubscriptionUpdateSchema.parse({ isActive: true })).toEqual({
        isActive: true,
      });
      expect(SubscriptionUpdateSchema.parse({ isActive: false })).toEqual({
        isActive: false,
      });
    });

    it("accepts empty object (all fields optional)", () => {
      expect(SubscriptionUpdateSchema.parse({})).toEqual({});
    });

    it("rejects non-boolean isActive", () => {
      expect(() =>
        SubscriptionUpdateSchema.parse({ isActive: "true" }),
      ).toThrow();
      expect(() => SubscriptionUpdateSchema.parse({ isActive: 1 })).toThrow();
    });
  });

  describe("UserUpdateSchema", () => {
    it("accepts valid user update with all fields", () => {
      const valid = {
        role: "admin" as const,
        collegeId: 5,
        phone: "123-456-7890",
      };
      expect(UserUpdateSchema.parse(valid)).toEqual(valid);
    });

    it("accepts partial updates", () => {
      expect(UserUpdateSchema.parse({ role: "user" })).toEqual({
        role: "user",
      });
      expect(UserUpdateSchema.parse({ collegeId: 10 })).toEqual({
        collegeId: 10,
      });
    });

    it("accepts empty object", () => {
      expect(UserUpdateSchema.parse({})).toEqual({});
    });

    it("rejects invalid role", () => {
      expect(() => UserUpdateSchema.parse({ role: "superadmin" })).toThrow();
    });

    it("rejects invalid collegeId", () => {
      expect(() => UserUpdateSchema.parse({ collegeId: -1 })).toThrow();
      expect(() => UserUpdateSchema.parse({ collegeId: 0 })).toThrow();
    });
  });

  describe("CollegeUpdateSchema", () => {
    it("accepts valid collegeId", () => {
      expect(CollegeUpdateSchema.parse({ collegeId: 1 })).toEqual({
        collegeId: 1,
      });
    });

    it("rejects missing collegeId", () => {
      expect(() => CollegeUpdateSchema.parse({})).toThrow();
    });

    it("rejects invalid collegeId", () => {
      expect(() => CollegeUpdateSchema.parse({ collegeId: 0 })).toThrow();
      expect(() => CollegeUpdateSchema.parse({ collegeId: -5 })).toThrow();
    });
  });

  describe("PaginationSchema", () => {
    describe("default values", () => {
      it("provides default page 1", () => {
        const result = PaginationSchema.parse({});
        expect(result.page).toBe(1);
      });

      it("provides default limit 10", () => {
        const result = PaginationSchema.parse({});
        expect(result.limit).toBe(10);
      });
    });

    describe("transforms", () => {
      it("transforms string page to number", () => {
        const result = PaginationSchema.parse({ page: "5" });
        expect(result.page).toBe(5);
        expect(typeof result.page).toBe("number");
      });

      it("transforms string limit to number", () => {
        const result = PaginationSchema.parse({ limit: "25" });
        expect(result.limit).toBe(25);
        expect(typeof result.limit).toBe("number");
      });
    });

    describe("validation", () => {
      it("accepts valid pagination parameters", () => {
        const result = PaginationSchema.parse({
          page: "2",
          limit: "50",
          search: "test",
          role: "admin",
        });
        expect(result).toEqual({
          page: 2,
          limit: 50,
          search: "test",
          role: "admin",
        });
      });

      it("rejects page less than 1", () => {
        expect(() => PaginationSchema.parse({ page: "0" })).toThrow();
        expect(() => PaginationSchema.parse({ page: "-1" })).toThrow();
      });

      it("rejects limit less than 1", () => {
        expect(() => PaginationSchema.parse({ limit: "0" })).toThrow();
      });

      it("rejects limit greater than 100", () => {
        expect(() => PaginationSchema.parse({ limit: "101" })).toThrow();
        expect(() => PaginationSchema.parse({ limit: "1000" })).toThrow();
      });

      it("rejects search longer than 100 characters", () => {
        const longSearch = "a".repeat(101);
        expect(() => PaginationSchema.parse({ search: longSearch })).toThrow();
      });

      it("accepts search up to 100 characters", () => {
        const maxSearch = "a".repeat(100);
        const result = PaginationSchema.parse({ search: maxSearch });
        expect(result.search).toBe(maxSearch);
      });

      it("rejects invalid role enum", () => {
        expect(() => PaginationSchema.parse({ role: "superadmin" })).toThrow();
      });

      it("accepts valid role enums", () => {
        expect(PaginationSchema.parse({ role: "user" }).role).toBe("user");
        expect(PaginationSchema.parse({ role: "admin" }).role).toBe("admin");
        expect(PaginationSchema.parse({ role: "all" }).role).toBe("all");
      });
    });
  });

  describe("CourseQuerySchema", () => {
    describe("default values", () => {
      it("provides default page 1", () => {
        const result = CourseQuerySchema.parse({});
        expect(result.page).toBe(1);
      });

      it("provides default limit 20", () => {
        const result = CourseQuerySchema.parse({});
        expect(result.limit).toBe(20);
      });
    });

    describe("transforms", () => {
      it("transforms string page to number", () => {
        const result = CourseQuerySchema.parse({ page: "3" });
        expect(result.page).toBe(3);
      });

      it("transforms string limit to number", () => {
        const result = CourseQuerySchema.parse({ limit: "30" });
        expect(result.limit).toBe(30);
      });

      it("transforms string collegeId to number", () => {
        const result = CourseQuerySchema.parse({ collegeId: "5" });
        expect(result.collegeId).toBe(5);
        expect(typeof result.collegeId).toBe("number");
      });

      it("transforms undefined collegeId to undefined", () => {
        const result = CourseQuerySchema.parse({});
        expect(result.collegeId).toBeUndefined();
      });
    });

    describe("validation", () => {
      it("accepts valid course query parameters", () => {
        const result = CourseQuerySchema.parse({
          page: "2",
          limit: "30",
          search: "computer science",
          collegeId: "10",
        });
        expect(result).toEqual({
          page: 2,
          limit: 30,
          search: "computer science",
          collegeId: 10,
        });
      });

      it("rejects page less than 1", () => {
        expect(() => CourseQuerySchema.parse({ page: "0" })).toThrow();
      });

      it("rejects limit less than 1", () => {
        expect(() => CourseQuerySchema.parse({ limit: "0" })).toThrow();
      });

      it("rejects limit greater than 50", () => {
        expect(() => CourseQuerySchema.parse({ limit: "51" })).toThrow();
        expect(() => CourseQuerySchema.parse({ limit: "100" })).toThrow();
      });

      it("rejects search longer than 100 characters", () => {
        const longSearch = "a".repeat(101);
        expect(() => CourseQuerySchema.parse({ search: longSearch })).toThrow();
      });

      it("rejects invalid collegeId", () => {
        expect(() => CourseQuerySchema.parse({ collegeId: "0" })).toThrow();
        expect(() => CourseQuerySchema.parse({ collegeId: "-1" })).toThrow();
      });
    });
  });

  describe("NotificationRequestSchema", () => {
    it("accepts valid email notification request", () => {
      const valid = {
        type: "email" as const,
        message: "Test message",
        subscriptionIds: [1, 2, 3],
      };
      expect(NotificationRequestSchema.parse(valid)).toEqual(valid);
    });

    it("accepts valid sms notification request", () => {
      const valid = {
        type: "sms" as const,
        message: "SMS message",
        subscriptionIds: [5],
      };
      expect(NotificationRequestSchema.parse(valid)).toEqual(valid);
    });

    it("rejects invalid notification type", () => {
      expect(() =>
        NotificationRequestSchema.parse({
          type: "push",
          message: "test",
          subscriptionIds: [1],
        }),
      ).toThrow();
    });

    it("rejects empty message", () => {
      expect(() =>
        NotificationRequestSchema.parse({
          type: "email",
          message: "",
          subscriptionIds: [1],
        }),
      ).toThrow();
    });

    it("rejects message longer than 1000 characters", () => {
      const longMessage = "a".repeat(1001);
      expect(() =>
        NotificationRequestSchema.parse({
          type: "email",
          message: longMessage,
          subscriptionIds: [1],
        }),
      ).toThrow();
    });

    it("accepts message up to 1000 characters", () => {
      const maxMessage = "a".repeat(1000);
      const result = NotificationRequestSchema.parse({
        type: "email",
        message: maxMessage,
        subscriptionIds: [1],
      });
      expect(result.message).toBe(maxMessage);
    });

    it("rejects empty subscriptionIds array", () => {
      expect(() =>
        NotificationRequestSchema.parse({
          type: "email",
          message: "test",
          subscriptionIds: [],
        }),
      ).toThrow();
    });

    it("rejects invalid subscription IDs", () => {
      expect(() =>
        NotificationRequestSchema.parse({
          type: "email",
          message: "test",
          subscriptionIds: [0, 1],
        }),
      ).toThrow();
      expect(() =>
        NotificationRequestSchema.parse({
          type: "email",
          message: "test",
          subscriptionIds: [-1],
        }),
      ).toThrow();
    });
  });
});
