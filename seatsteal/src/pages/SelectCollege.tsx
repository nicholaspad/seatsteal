import { IonContent, IonPage } from "@ionic/react";
import { CollegeSelectionForm } from "@/components/auth/CollegeSelectionForm";
import { GraduationCap } from "lucide-react";

export default function SelectCollege() {
  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <div className="space-y-2 text-center">
              <div className="flex justify-center mb-4">
                <GraduationCap className="w-12 h-12 text-primary" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">
                Welcome to SeatSteal
              </h1>
              <p className="text-muted-foreground">
                Select your college to get started
              </p>
            </div>
            <CollegeSelectionForm />
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
