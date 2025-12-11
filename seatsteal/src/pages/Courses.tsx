import { IonContent, IonPage } from "@ionic/react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { CourseCard } from "@/components/course/course-card";
import { BlurredCourseCard } from "@/components/course/blurred-course-card";
import { FullWidthCTA } from "@/components/course/full-width-cta";
import { CourseFilters } from "@/components/course/course-filters";
import { PaginationLinks } from "@/components/layout/PaginationLinks";
import { BookOpen } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { useSession } from "@/components/providers/SessionProvider";
import type { CourseWithClasses } from "@/types/api";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { useSearchParams } from "@/hooks/use-search-params";
import { logError } from "@/lib/logger";
import { useDocumentTitle, SEO_CONFIGS } from "@/hooks/use-document-title";

interface CoursesData {
  courses: CourseWithClasses[];
  totalCourses: number;
  currentPage: number;
  totalPages: number;
  error: string | null;
}

async function getCoursesData(
  searchParams: URLSearchParams,
  isLoggedOut: boolean,
): Promise<CoursesData> {
  try {
    const page = parseInt(searchParams.get("page") || "1");
    const limit = isLoggedOut ? 3 : 12;

    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });

    if (searchParams.get("q")) params.set("q", searchParams.get("q")!);
    if (searchParams.get("college") && searchParams.get("college") !== "all")
      params.set("collegeId", searchParams.get("college")!);
    if (searchParams.get("sort")) params.set("sort", searchParams.get("sort")!);

    const response = await fetchWithToasts(`/api/courses?${params.toString()}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const coursesData = await response.json();
    if (!coursesData.success) {
      throw new Error(coursesData.error || "Failed to fetch courses");
    }

    const courses: CourseWithClasses[] = coursesData.data?.data || [];
    const pagination = coursesData.data?.pagination;

    return {
      courses,
      totalCourses: pagination?.total || 0,
      currentPage: pagination?.page || 1,
      totalPages: pagination?.totalPages || 1,
      error: null,
    };
  } catch (error) {
    if (!(error instanceof ServerErrorWithToast)) {
      logError("Failed to load courses", error);
    }
    return {
      courses: [],
      totalCourses: 0,
      currentPage: 1,
      totalPages: 1,
      error: error instanceof Error ? error.message : "Failed to load courses",
    };
  }
}

interface SearchSummaryProps {
  searchParams: URLSearchParams;
  totalCourses: number;
  selectedCollege?: { name: string; shortName: string } | null;
}

function SearchSummary({
  searchParams,
  totalCourses,
  selectedCollege,
}: SearchSummaryProps) {
  const hasFilters = searchParams.get("q");

  if (!hasFilters) {
    const subtitle = selectedCollege
      ? `Browse ${totalCourses.toLocaleString()} courses at ${selectedCollege.name}`
      : `Browse ${totalCourses.toLocaleString()} courses`;

    return (
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-semibold">Courses</h2>
        <p className="text-muted-foreground">{subtitle}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h2 className="text-2xl font-semibold">Search Results</h2>
      <div className="flex flex-wrap gap-2">
        {searchParams.get("q") && (
          <Badge variant="secondary">
            Query: &quot;{searchParams.get("q")}&quot;
          </Badge>
        )}
      </div>
      <p className="text-sm text-muted-foreground">
        {totalCourses} course{totalCourses !== 1 ? "s" : ""} found
      </p>
    </div>
  );
}

export default function Courses() {
  const searchParams = useSearchParams();
  const { user, profile, profileLoading, loading: authLoading } = useSession();

  // SEO: Set document title and meta description
  useDocumentTitle(SEO_CONFIGS.courses);

  // All hooks must be declared before any conditional returns
  const isLoggedOut = !user;
  const [data, setData] = useState<CoursesData>({
    courses: [],
    totalCourses: 0,
    currentPage: 1,
    totalPages: 1,
    error: null,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Wait for auth to load before fetching data
    // This prevents race condition where API call happens before auth completes
    if (authLoading || (user && profileLoading)) {
      return;
    }

    setLoading(true);
    getCoursesData(searchParams, isLoggedOut).then((result) => {
      setData(result);
      setLoading(false);
    });
  }, [searchParams.toString(), isLoggedOut, authLoading, user, profileLoading]);

  const { courses, totalCourses, currentPage, totalPages, error } = data;

  const selectedCollege =
    searchParams.get("college") &&
    searchParams.get("college") !== "all" &&
    courses.length > 0
      ? courses[0].college
      : null;

  // Show loading spinner while auth is initializing
  if (authLoading) {
    return (
      <IonPage>
        <IonContent>
          <div className="container mx-auto px-4 py-8">
            <div className="text-center py-12">
              <Spinner className="size-12 mx-auto" />
              <p className="mt-4 text-muted-foreground">Loading...</p>
            </div>
          </div>
        </IonContent>
      </IonPage>
    );
  }

  // Wait for profile to load before rendering to get correct initial college filter
  if (user && profileLoading) {
    return (
      <IonPage>
        <IonContent>
          <div className="container mx-auto px-4 py-8">
            <div className="text-center py-12">
              <Spinner className="size-12 mx-auto" />
              <p className="mt-4 text-muted-foreground">Loading...</p>
            </div>
          </div>
        </IonContent>
      </IonPage>
    );
  }

  if (error) {
    return (
      <IonPage>
        <IonContent>
          <div className="container mx-auto px-4 py-8">
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <div className="text-center py-8">
                  <h3 className="font-medium text-destructive mb-1">
                    Error Loading Courses
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">{error}</p>
                  <Button
                    variant="outline"
                    onClick={() => window.location.reload()}
                  >
                    Try Again
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </IonContent>
      </IonPage>
    );
  }

  return (
    <IonPage>
      <IonContent>
        <div className="container mx-auto px-4 py-8 space-y-8">
          {/* Breadcrumb Navigation */}
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to="/">Home</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Courses</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Filters Sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-8">
                <CourseFilters
                  initialValues={{
                    q: searchParams.get("q") || undefined,
                    college:
                      searchParams.get("college") ||
                      profile?.collegeId?.toString() ||
                      undefined,
                    sort: searchParams.get("sort") || undefined,
                  }}
                />
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3 space-y-6">
              {/* Search Summary */}
              {!loading && (
                <SearchSummary
                  searchParams={searchParams}
                  totalCourses={totalCourses}
                  selectedCollege={selectedCollege}
                />
              )}

              {/* Results */}
              {loading ? (
                <div className="text-center py-12">
                  <Spinner className="size-12 mx-auto" />
                  <p className="mt-4 text-muted-foreground">
                    Loading courses...
                  </p>
                </div>
              ) : courses.length === 0 ? (
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-center py-12">
                      <BookOpen className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                      <h3 className="text-lg font-medium mb-2">
                        No Courses Found
                      </h3>
                      <p className="text-muted-foreground mb-6">
                        {searchParams.get("q")
                          ? "Try adjusting your search criteria or filters."
                          : "No courses are currently available."}
                      </p>
                      <Button asChild variant="outline">
                        <Link to="/courses">Clear Filters</Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <>
                  {isLoggedOut ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                      {courses.map((course) => (
                        <CourseCard
                          key={course.id}
                          course={course}
                          classes={course.classes}
                        />
                      ))}
                      <FullWidthCTA />
                      {Array.from({ length: 6 }, (_, i) => (
                        <BlurredCourseCard key={`blurred-${i}`} />
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                      {courses.map((course) => (
                        <CourseCard
                          key={course.id}
                          course={course}
                          classes={course.classes}
                        />
                      ))}
                    </div>
                  )}

                  {!isLoggedOut && totalPages > 1 && (
                    <div className="flex justify-center pt-8">
                      <PaginationLinks
                        currentPage={currentPage}
                        totalPages={totalPages}
                        basePath="/courses"
                        searchParams={
                          new URLSearchParams({
                            ...(searchParams.get("q") && {
                              q: searchParams.get("q")!,
                            }),
                            ...(searchParams.get("college") && {
                              college: searchParams.get("college")!,
                            }),
                            ...(searchParams.get("sort") && {
                              sort: searchParams.get("sort")!,
                            }),
                          })
                        }
                        showFirstLast={true}
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
