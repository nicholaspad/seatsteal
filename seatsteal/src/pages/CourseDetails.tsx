import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { IonPage, IonContent } from "@ionic/react";
import { CourseDetailsClient } from "@/components/course/course-details-client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import type { CourseWithClasses, CourseDetailsApiResponse } from "@/types/api";

export default function CourseDetails() {
  const { id } = useParams<{ id: string }>();
  const [course, setCourse] = useState<CourseWithClasses | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCourseData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetchWithToasts(`/api/courses/${id}`);
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Course not found");
          }
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: CourseDetailsApiResponse = await response.json();
        if (!data.success || !data.data) {
          throw new Error(data.error || "Failed to fetch course details");
        }

        setCourse(data.data);
      } catch (err) {
        if (err instanceof ServerErrorWithToast) {
          setError("Failed to load course details");
          return;
        }
        setError(
          err instanceof Error ? err.message : "Failed to load course details",
        );
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchCourseData();
    }
  }, [id]);

  if (loading) {
    return (
      <IonPage>
        <IonContent>
          <div className="container mx-auto px-4 py-8">
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <Spinner className="size-12" />
                  <p className="text-lg text-muted-foreground">
                    Loading course details...
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </IonContent>
      </IonPage>
    );
  }

  if (error || !course) {
    return (
      <IonPage>
        <IonContent>
          <div className="container mx-auto px-4 py-8">
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <AlertCircle className="h-12 w-12 text-destructive" />
                  <h3 className="text-xl font-semibold">
                    {error || "Course not found"}
                  </h3>
                  <p className="text-muted-foreground">
                    The course you're looking for could not be loaded.
                  </p>
                  <Button onClick={() => window.history.back()}>Go Back</Button>
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
        <CourseDetailsClient course={course} />
      </IonContent>
    </IonPage>
  );
}
