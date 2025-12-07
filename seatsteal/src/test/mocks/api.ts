import { vi } from "vitest";

export const mockFetchResponse = (data: unknown, ok = true, status = 200) => {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(data),
  });
};

export const mockFetchWithToasts = vi.fn();

export const resetApiMocks = () => {
  mockFetchWithToasts.mockReset();
};

// Common mock responses
export const mockCollegesResponse = {
  success: true,
  data: [
    {
      id: 1,
      name: "Test University",
      shortName: "TU",
      isActive: true,
      currentTerm: "Spring 2025",
    },
    {
      id: 2,
      name: "Sample College",
      shortName: "SC",
      isActive: true,
      currentTerm: "Spring 2025",
    },
  ],
};

export const mockCourseData = {
  id: 1,
  courseCode: "CS101",
  title: "Introduction to Computer Science",
  collegeId: 1,
  isActive: true,
  createdAt: "2024-01-01",
  updatedAt: "2024-01-01",
  college: { id: 1, name: "Test University", shortName: "TU" },
  classes: [
    {
      classId: 1,
      courseId: 1,
      classNumber: "12345",
      sectionCode: "001",
      isActive: true,
      currentEnrollment: { enrollmentStatus: "open", scrapedAt: "2024-01-01" },
    },
    {
      classId: 2,
      courseId: 1,
      classNumber: "12346",
      sectionCode: "002",
      isActive: true,
      currentEnrollment: {
        enrollmentStatus: "closed",
        scrapedAt: "2024-01-01",
      },
    },
  ],
};

export const mockCoursesResponse = {
  success: true,
  data: {
    data: [mockCourseData],
    pagination: { page: 1, limit: 12, total: 1, totalPages: 1 },
  },
};

export const mockSubscriptionsResponse = {
  success: true,
  data: [],
};

export const mockSubscriptionData = {
  id: 1,
  classId: 1,
  collegeId: 1,
  userId: "test-user",
  isActive: true,
  lastNotified: "2024-01-15",
  notificationCount: 3,
  createdAt: "2024-01-01",
  updatedAt: "2024-01-15",
  class: {
    classId: 1,
    courseId: 1,
    classNumber: "12345",
    sectionCode: "001",
    currentEnrollment: { enrollmentStatus: "open", scrapedAt: "2024-01-15" },
    course: {
      id: 1,
      courseCode: "CS101",
      title: "Intro to CS",
      college: { id: 1, name: "Test University", shortName: "TU" },
    },
  },
};

export const mockSettingsResponse = {
  success: true,
  data: {
    email: "test@university.edu",
    phone: "1234567890",
    collegeId: 1,
    collegeName: "Test University",
  },
};

export const mockTrendsResponse = {
  success: true,
  data: [
    { day: "Mon", notifications: 2, courses: ["CS101"] },
    { day: "Tue", notifications: 0, courses: [] },
    { day: "Wed", notifications: 1, courses: ["CS102"] },
    { day: "Thu", notifications: 0, courses: [] },
    { day: "Fri", notifications: 3, courses: ["CS101", "CS102"] },
    { day: "Sat", notifications: 0, courses: [] },
    { day: "Sun", notifications: 0, courses: [] },
  ],
};

// Multiple subscriptions for pagination and list testing
export const mockMultipleSubscriptions = [
  mockSubscriptionData,
  {
    ...mockSubscriptionData,
    id: 2,
    classId: 2,
    class: {
      ...mockSubscriptionData.class,
      classId: 2,
      sectionCode: "002",
      course: {
        ...mockSubscriptionData.class.course,
        courseCode: "CS102",
        title: "Data Structures",
      },
    },
  },
  {
    ...mockSubscriptionData,
    id: 3,
    classId: 3,
    class: {
      ...mockSubscriptionData.class,
      classId: 3,
      sectionCode: "003",
      course: {
        ...mockSubscriptionData.class.course,
        courseCode: "CS201",
        title: "Algorithms",
      },
    },
  },
];

// Empty trends for edge case testing
export const mockEmptyTrendsResponse = {
  success: true,
  data: [
    { day: "Mon", notifications: 0, courses: [] },
    { day: "Tue", notifications: 0, courses: [] },
    { day: "Wed", notifications: 0, courses: [] },
    { day: "Thu", notifications: 0, courses: [] },
    { day: "Fri", notifications: 0, courses: [] },
    { day: "Sat", notifications: 0, courses: [] },
    { day: "Sun", notifications: 0, courses: [] },
  ],
};

// Course with closed class for subscription testing
export const mockCourseWithClosedClass = {
  ...mockCourseData,
  classes: [
    {
      classId: 1,
      courseId: 1,
      classNumber: "12345",
      sectionCode: "001",
      isActive: true,
      currentEnrollment: {
        enrollmentStatus: "closed",
        scrapedAt: "2024-01-01",
      },
    },
  ],
};

// Course with multiple classes for filtering tests
export const mockCourseWithMultipleClasses = {
  ...mockCourseData,
  classes: [
    {
      classId: 1,
      courseId: 1,
      classNumber: "12345",
      sectionCode: "001",
      isActive: true,
      currentEnrollment: { enrollmentStatus: "open", scrapedAt: "2024-01-01" },
    },
    {
      classId: 2,
      courseId: 1,
      classNumber: "12346",
      sectionCode: "002",
      isActive: true,
      currentEnrollment: {
        enrollmentStatus: "closed",
        scrapedAt: "2024-01-01",
      },
    },
    {
      classId: 3,
      courseId: 1,
      classNumber: "12347",
      sectionCode: "003",
      isActive: true,
      currentEnrollment: {
        enrollmentStatus: "closed",
        scrapedAt: "2024-01-01",
      },
    },
  ],
};

// Courses response with pagination for testing multi-page scenarios
export const mockCoursesResponseWithPagination = {
  success: true,
  data: {
    data: [mockCourseData],
    pagination: { page: 1, limit: 12, total: 25, totalPages: 3 },
  },
};
