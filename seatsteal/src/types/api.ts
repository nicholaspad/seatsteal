// Base database types (replicated from backend schema)
export interface College {
  id: number;
  name: string;
  shortName: string;
  domain: string | null;
  termCode: string | null;
  termName: string | null;
  emailEnabled: boolean;
  smsEnabled: boolean;
  createdAt: string;
  isActive: boolean;
}

export interface Course {
  id: number;
  collegeId: number;
  courseCode: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
}

export interface Class {
  classId: number;
  courseId: number;
  classNumber: string;
  sectionCode: string | null;
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
}

export interface Enrollment {
  id: number;
  collegeId: number;
  classId: number;
  enrollmentStatus: string;
  scrapedAt: string;
  rawText: string | null;
}

export interface Profile {
  id: string;
  collegeId: number | null;
  role: string;
  email: string;
  phone: string | null;
}

export interface Subscription {
  id: number;
  collegeId: number;
  userId: string;
  classId: number;
  isActive: boolean;
  lastNotified: string | null;
  notificationCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface NotificationLog {
  id: number;
  collegeId: number;
  subscriptionId: number;
  notificationType: string;
  message: string;
  status: string;
  seatsRemaining: number | null;
  enrollmentStatus: string | null;
  sentAt: string;
}

// Generic API response wrapper
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

// Course search parameters
export interface CourseSearchParams {
  q?: string;
  collegeId?: number;
  enrollment?: "open" | "closed" | "all";
  page?: number;
  limit?: number;
}

// Enhanced types with relationships
export interface CourseWithCollege extends Course {
  college: College;
  classCount?: number;
}

export interface ClassWithEnrollment extends Class {
  currentEnrollment?: {
    enrollmentStatus: string;
    scrapedAt: string;
  };
}

export interface CourseWithClasses extends CourseWithCollege {
  classes: ClassWithEnrollment[];
  lastScraperUpdate?: string;
}

export interface ClassWithCourse extends ClassWithEnrollment {
  course: CourseWithCollege;
}

// Subscription types
export interface SubscriptionRequest {
  classId: number;
  collegeId: number;
  // userId will come from auth session on server-side
}

export interface SubscriptionWithDetails extends Subscription {
  class: ClassWithCourse;
}

// Pagination
export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// API route specific types
export type CollegesApiResponse = ApiResponse<College[]>;

export type CoursesApiResponse = ApiResponse<
  PaginatedResponse<CourseWithCollege>
>;

export type CourseDetailsApiResponse = ApiResponse<CourseWithClasses>;

export type ClassDetailsApiResponse = ApiResponse<ClassWithCourse>;

export type SubscriptionsApiResponse = ApiResponse<SubscriptionWithDetails[]>;

export type SubscriptionApiResponse = ApiResponse<SubscriptionWithDetails>;
