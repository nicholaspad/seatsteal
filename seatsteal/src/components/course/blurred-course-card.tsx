import { memo } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface BlurredCourseCardProps {
  className?: string;
}

const mockCourses = [
  {
    collegeShortName: "PRINCETON",
    courseCode: "COS 126",
    title: "Computer Science: An Interdisciplinary Approach",
    sections: 3,
    openSections: 1,
    closedSections: 2,
  },
  {
    collegeShortName: "PRINCETON",
    courseCode: "ECO 100",
    title: "Introduction to Microeconomics",
    sections: 4,
    openSections: 2,
    closedSections: 2,
  },
  {
    collegeShortName: "PRINCETON",
    courseCode: "PSY 101",
    title: "Introduction to Psychology",
    sections: 2,
    openSections: 0,
    closedSections: 2,
  },
  {
    collegeShortName: "PRINCETON",
    courseCode: "MAT 201",
    title: "Multivariable Calculus",
    sections: 5,
    openSections: 3,
    closedSections: 2,
  },
  {
    collegeShortName: "PRINCETON",
    courseCode: "PHY 103",
    title: "General Physics I",
    sections: 3,
    openSections: 1,
    closedSections: 2,
  },
  {
    collegeShortName: "PRINCETON",
    courseCode: "CHM 201",
    title: "General Chemistry",
    sections: 4,
    openSections: 2,
    closedSections: 2,
  },
];

const BlurredCourseCard = memo(function BlurredCourseCard({
  className,
}: BlurredCourseCardProps) {
  const mockCourse =
    mockCourses[Math.floor(Math.random() * mockCourses.length)];

  // Generate random class data for more realistic variation
  const generateRandomClasses = () => {
    const numClasses = Math.floor(Math.random() * 4) + 1; // 1-4 classes
    const classes = [];

    const sectionCodes = [
      "L01",
      "L02",
      "L03",
      "P01",
      "P02",
      "S01",
      "B01",
      "B02",
    ];
    const classNumbers = [
      "12345",
      "12346",
      "12347",
      "18898",
      "22567",
      "31849",
      "22248",
      "20645",
    ];

    for (let i = 0; i < numClasses; i++) {
      const isOpen = Math.random() > 0.6; // 40% chance of being open
      classes.push({
        sectionCode:
          sectionCodes[Math.floor(Math.random() * sectionCodes.length)],
        classNumber:
          classNumbers[Math.floor(Math.random() * classNumbers.length)],
        isOpen,
      });
    }

    return classes;
  };

  const randomClasses = generateRandomClasses();
  const openCount = randomClasses.filter((c) => c.isOpen).length;
  const closedCount = randomClasses.length - openCount;

  return (
    <Card
      className={cn(
        "hover:shadow-md transition-shadow duration-200 flex flex-col relative",
        "blur-[4px] opacity-40 pointer-events-none select-none",
        className,
      )}
    >
      <CardHeader className="pb-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="inline-flex items-center px-2 py-1 bg-muted rounded-full">
              <span className="text-xs font-medium text-muted-foreground">
                {mockCourse.collegeShortName}
              </span>
            </div>
            <h3 className="font-semibold text-lg leading-none tracking-tight">
              {mockCourse.courseCode}
            </h3>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">
            {mockCourse.title}
          </p>
        </div>
      </CardHeader>

      <CardContent className="pt-0 pb-3 flex-1">
        <div className="space-y-3">
          {/* Enrollment summary */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">
                {randomClasses.length} section
                {randomClasses.length !== 1 ? "s" : ""}
              </span>
            </div>

            {openCount > 0 && (
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-green-700">{openCount} open</span>
              </div>
            )}

            {closedCount > 0 && (
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                <span className="text-red-700">{closedCount} closed</span>
              </div>
            )}
          </div>

          {/* Random class sections preview */}
          <div className="space-y-2 min-h-[6rem]">
            {randomClasses.slice(0, 2).map((classItem, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-2 rounded-md bg-muted/50"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {classItem.sectionCode}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    • {classItem.classNumber}
                  </span>
                </div>
                <div
                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    classItem.isOpen
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {classItem.isOpen ? "OPEN" : "CLOSED"}
                </div>
              </div>
            ))}

            {randomClasses.length > 2 && (
              <div className="text-center">
                <span className="text-xs text-muted-foreground">
                  +{randomClasses.length - 2} more section
                  {randomClasses.length - 2 !== 1 ? "s" : ""}
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-3">
        <Button variant="outline" className="w-full">
          Classes
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
});

export { BlurredCourseCard };
