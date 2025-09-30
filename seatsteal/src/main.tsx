import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { IonApp, IonRouterOutlet, setupIonicReact } from '@ionic/react';
import { IonReactRouter } from '@ionic/react-router';
import { Route } from 'react-router';

setupIonicReact();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <IonApp>
      <IonReactRouter>
        <IonRouterOutlet>
          <Route path="/" component={App} />
        </IonRouterOutlet>
      </IonReactRouter>
    </IonApp>
  </StrictMode>,
)
