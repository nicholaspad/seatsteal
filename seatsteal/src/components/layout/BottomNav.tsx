import { IonTabBar, IonTabButton, IonIcon, IonLabel } from "@ionic/react";
import { useLocation, useHistory } from "react-router-dom";
import {
  bookOutline,
  gridOutline,
  homeOutline,
  book,
  grid,
  home,
} from "ionicons/icons";
import { useSession } from "@/components/providers/SessionProvider";

export function BottomNav() {
  const location = useLocation();
  const history = useHistory();
  const { user, profile } = useSession();

  const coursesHref = profile?.collegeId
    ? `/courses?college=${profile.collegeId}`
    : "/courses";

  const tabs = [
    {
      name: "Home",
      href: "/",
      icon: homeOutline,
      iconActive: home,
      matchExact: true,
    },
    {
      name: "Courses",
      href: coursesHref,
      basePath: "/courses",
      icon: bookOutline,
      iconActive: book,
      matchExact: false,
    },
    ...(user
      ? [
          {
            name: "Dashboard",
            href: "/dashboard",
            basePath: "/dashboard",
            icon: gridOutline,
            iconActive: grid,
            matchExact: true,
          },
        ]
      : []),
  ];

  const isActive = (tab: (typeof tabs)[0]) => {
    if (tab.matchExact) {
      return location.pathname === tab.href;
    }
    return location.pathname.startsWith(tab.basePath || tab.href);
  };

  const handleTabClick = (href: string) => {
    // Handle Home link - scroll to top if already on homepage
    if (href === "/" && location.pathname === "/") {
      const ionContent = document.querySelector("ion-content");
      if (ionContent) {
        ionContent.scrollToTop(300);
      }
      return;
    }
    history.push(href);
  };

  return (
    <IonTabBar slot="bottom" className="bottom-nav">
      {tabs.map((tab) => {
        const active = isActive(tab);
        return (
          <IonTabButton
            key={tab.href}
            tab={tab.name.toLowerCase()}
            onClick={() => handleTabClick(tab.href)}
            className={active ? "tab-selected" : ""}
          >
            <IonIcon
              icon={active ? tab.iconActive : tab.icon}
              className="tab-icon"
            />
            <IonLabel>{tab.name}</IonLabel>
          </IonTabButton>
        );
      })}
    </IonTabBar>
  );
}
