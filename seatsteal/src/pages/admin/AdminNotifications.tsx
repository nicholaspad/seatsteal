import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { NotificationsClient } from "@/components/admin/notifications-client";

const AdminNotifications: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <NotificationsClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default AdminNotifications;
