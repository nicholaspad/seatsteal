import { CourseDetailsWrapper } from "./course-details-wrapper";
import type { CourseWithClasses } from "@/types/api";

interface CourseDetailsClientProps {
  course: CourseWithClasses;
}

export function CourseDetailsClient({ course }: CourseDetailsClientProps) {
  return <CourseDetailsWrapper course={course} />;
}
