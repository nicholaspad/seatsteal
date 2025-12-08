import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { CollegesClient } from "@/components/admin/colleges-client";

const AdminColleges: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <CollegesClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default AdminColleges;
