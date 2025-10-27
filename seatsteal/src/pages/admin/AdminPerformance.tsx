import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { PerformanceDashboardClient } from "@/components/admin/performance-dashboard-client";

const AdminPerformance: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <PerformanceDashboardClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default AdminPerformance;
