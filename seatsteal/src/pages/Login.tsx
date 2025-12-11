import { IonContent, IonPage } from "@ionic/react";
import { Redirect } from "react-router-dom";
import { LoginForm } from "@/components/auth/LoginForm";
import { useSession } from "@/components/providers/SessionProvider";
import { useDocumentTitle, SEO_CONFIGS } from "@/hooks/use-document-title";

export default function Login() {
  const { user, loading } = useSession();

  // SEO: Set document title and meta description
  useDocumentTitle(SEO_CONFIGS.login);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (user) {
    return <Redirect to="/courses" />;
  }

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md space-y-6">
            <LoginForm />
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
