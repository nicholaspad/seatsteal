import { IonContent, IonPage } from "@ionic/react";
import { useState, useEffect } from "react";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { toast } from "sonner";

export default function Courses() {
  const [loading, setLoading] = useState(true);
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await fetchWithToasts("/api/courses");
        if (response.ok) {
          const data = await response.json();
          setCourses(data.courses || []);
        }
      } catch (err) {
        if (!(err instanceof ServerErrorWithToast)) {
          toast.error("Failed to load courses");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="container mx-auto py-8">
          <h1 className="text-3xl font-bold mb-6">Browse Courses</h1>
          {loading ? (
            <div className="text-center py-12">Loading courses...</div>
          ) : (
            <div className="text-muted-foreground">
              {courses.length === 0
                ? "No courses available"
                : `Found ${courses.length} courses`}
            </div>
          )}
        </div>
      </IonContent>
    </IonPage>
  );
}
