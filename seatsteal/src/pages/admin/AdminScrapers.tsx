import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { ScrapersDashboardClient } from "@/components/admin/scrapers-dashboard-client";

const AdminScrapers: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <ScrapersDashboardClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default AdminScrapers;
