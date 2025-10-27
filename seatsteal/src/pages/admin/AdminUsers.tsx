import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { UserManagementClient } from "@/components/admin/user-management-client";

const AdminUsers: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <UserManagementClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default AdminUsers;
