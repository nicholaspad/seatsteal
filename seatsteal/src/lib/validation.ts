import { z } from "zod";

// Common validation schemas
export const IdSchema = z.number().int().positive();
export const UuidSchema = z.string().uuid();
export const EmailSchema = z
  .string()
  .email()
  .refine(
    (email) => !email.includes("+"),
    "Email addresses with + characters are not allowed",
  )
  .refine((email) => {
    const localPart = email.split("@")[0];
    return !localPart.includes(".");
  }, "Email addresses with . characters in the username are not allowed");
export const PhoneSchema = z
  .string()
  .regex(/^\+?[\d\s\-\(\)]{10,15}$/, "Invalid phone number format")
  .optional();

// Subscription validation schemas
export const SubscriptionRequestSchema = z.object({
  classId: IdSchema,
  collegeId: IdSchema,
});

export const SubscriptionUpdateSchema = z.object({
  isActive: z.boolean().optional(),
});

// User management validation schemas
export const UserUpdateSchema = z.object({
  role: z.enum(["user", "admin"]).optional(),
  collegeId: IdSchema.optional(),
  phone: PhoneSchema,
});

export const CollegeUpdateSchema = z.object({
  collegeId: IdSchema,
});

// Query parameter validation schemas
export const PaginationSchema = z.object({
  page: z
    .string()
    .optional()
    .default("1")
    .transform((val) => Number(val))
    .pipe(z.number().min(1)),
  limit: z
    .string()
    .optional()
    .default("10")
    .transform((val) => Number(val))
    .pipe(z.number().min(1).max(100)),
  search: z.string().max(100).optional(),
  role: z.enum(["user", "admin", "all"]).optional(),
});

export const CourseQuerySchema = z.object({
  page: z
    .string()
    .optional()
    .default("1")
    .transform((val) => Number(val))
    .pipe(z.number().min(1)),
  limit: z
    .string()
    .optional()
    .default("20")
    .transform((val) => Number(val))
    .pipe(z.number().min(1).max(50)),
  search: z.string().max(100).optional(),
  collegeId: z
    .string()
    .optional()
    .transform((val) => (val ? Number(val) : undefined))
    .pipe(IdSchema.optional()),
});

// Notification validation schemas
export const NotificationRequestSchema = z.object({
  type: z.enum(["email", "sms"]),
  message: z.string().min(1).max(1000),
  subscriptionIds: z.array(IdSchema).min(1),
});

// Type exports for TypeScript
export type SubscriptionRequest = z.infer<typeof SubscriptionRequestSchema>;
export type SubscriptionUpdate = z.infer<typeof SubscriptionUpdateSchema>;
export type UserUpdate = z.infer<typeof UserUpdateSchema>;
export type CollegeUpdate = z.infer<typeof CollegeUpdateSchema>;
export type PaginationQuery = z.infer<typeof PaginationSchema>;
export type CourseQuery = z.infer<typeof CourseQuerySchema>;
export type NotificationRequest = z.infer<typeof NotificationRequestSchema>;
