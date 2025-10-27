import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { AdminDashboardClient } from "@/components/admin/admin-dashboard-client";

const Admin: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <AdminDashboardClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default Admin;
