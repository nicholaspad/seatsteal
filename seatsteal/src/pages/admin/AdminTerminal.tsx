import { IonContent, IonPage } from "@ionic/react";
import { AdminLayout } from "@/components/admin/admin-layout";
import { TerminalClient } from "@/components/admin/terminal-client";

const AdminTerminal: React.FC = () => {
  return (
    <IonPage>
      <IonContent>
        <AdminLayout>
          <TerminalClient />
        </AdminLayout>
      </IonContent>
    </IonPage>
  );
};

export default AdminTerminal;
