import { useEffect, useState, useRef } from "react";

export function IPhoneMockup() {
  const [showNotification, setShowNotification] = useState(false);
  const [hasTriggered, setHasTriggered] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (hasTriggered) return;

    // Find the IonContent's shadow DOM scroll container
    const ionContent = document.querySelector("ion-content");
    if (!ionContent) return;

    const handleScroll = (e: Event) => {
      const scrollEl = e.target as HTMLElement;
      // Require scrolling down at least 250px before showing notification
      if (!hasTriggered && scrollEl.scrollTop > 250) {
        setShowNotification(true);
        setHasTriggered(true);
      }
    };

    // IonContent uses a shadow DOM, need to get the scroll element
    ionContent.getScrollElement().then((scrollEl) => {
      scrollEl.addEventListener("scroll", handleScroll, {
        passive: true,
      });
    });

    return () => {
      ionContent.getScrollElement().then((scrollEl) => {
        scrollEl.removeEventListener("scroll", handleScroll);
      });
    };
  }, [hasTriggered]);

  return (
    <div
      ref={containerRef}
      className="relative mx-auto w-[320px] md:w-[380px] z-20"
    >
      {/* iPhone Frame */}
      <div className="relative">
        {/* Phone body with gradient border for depth */}
        <div className="relative bg-gradient-to-b from-zinc-700 via-zinc-800 to-zinc-900 rounded-[3rem] p-[3px] shadow-2xl shadow-black/50">
          {/* Inner frame */}
          <div className="bg-black rounded-[2.8rem] overflow-hidden">
            {/* Screen content */}
            <div className="relative aspect-[9/19.5] overflow-hidden">
              {/* Dark blue gradient wallpaper */}
              <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950">
                {/* Subtle gradient orbs for depth */}
                <div className="absolute top-[10%] left-[20%] w-32 h-32 bg-blue-800/30 rounded-full blur-3xl animate-pulse-slow"></div>
                <div className="absolute top-[30%] right-[10%] w-40 h-40 bg-indigo-700/20 rounded-full blur-3xl animate-pulse-slower"></div>
                <div className="absolute bottom-[20%] left-[30%] w-36 h-36 bg-blue-600/20 rounded-full blur-3xl animate-pulse-slow"></div>
              </div>

              {/* Dynamic Island */}
              <div className="absolute top-3 left-1/2 -translate-x-1/2 w-[100px] h-[32px] bg-black rounded-full z-30"></div>

              {/* Push Notification */}
              <div
                className={`absolute top-14 left-3 right-3 z-40 transition-all duration-500 ease-out ${
                  showNotification
                    ? "opacity-100 translate-y-0"
                    : "opacity-0 -translate-y-4"
                }`}
              >
                <div className="bg-white/90 backdrop-blur-xl rounded-2xl p-3 shadow-lg">
                  <div className="flex items-start gap-3">
                    {/* iMessage icon */}
                    <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                      <svg
                        className="w-6 h-6 text-white"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-gray-900 uppercase tracking-wide">
                          SeatSteal
                        </span>
                        <span className="text-xs text-gray-500">now</span>
                      </div>
                      <p className="text-sm font-medium text-gray-900 mt-0.5">
                        🎉 Seat available in Intro to CS!
                      </p>
                      <p className="text-sm text-gray-600 leading-snug">
                        Intro to CS (CS 103) 01 at Rutgers is OPEN!
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Date widget area */}
              <div className="absolute top-24 left-0 right-0 text-center text-white z-10 mt-8">
                <p className="text-sm font-medium opacity-90">
                  {new Date().toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  })}
                </p>
              </div>

              {/* App icons grid - showing top portion */}
              <div className="absolute bottom-0 left-0 right-0 px-6 pb-8">
                <div className="grid grid-cols-4 gap-4">
                  {/* Row of apps */}
                  <AppIcon
                    gradient="from-green-400 to-green-600"
                    icon={
                      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="white">
                        <path d="M20 15.5c-1.25 0-2.45-.2-3.57-.57-.35-.11-.74-.03-1.02.24l-2.2 2.2c-2.83-1.44-5.15-3.75-6.59-6.59l2.2-2.21c.28-.26.36-.65.25-1C8.7 6.45 8.5 5.25 8.5 4c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1 0 9.39 7.61 17 17 17 .55 0 1-.45 1-1v-3.5c0-.55-.45-1-1-1z" />
                      </svg>
                    }
                  />
                  <AppIcon
                    gradient="from-blue-400 to-blue-600"
                    icon={
                      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="white">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                      </svg>
                    }
                  />
                  <AppIcon
                    gradient="from-orange-400 to-red-500"
                    icon={
                      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="white">
                        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
                      </svg>
                    }
                  />
                  <AppIcon
                    gradient="from-purple-500 to-pink-500"
                    icon={
                      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="white">
                        <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 8h2v8H9zm4 0h2v8h-2z" />
                      </svg>
                    }
                  />
                </div>

                {/* Dock */}
                <div className="mt-4 bg-white/20 backdrop-blur-xl rounded-3xl p-3">
                  <div className="grid grid-cols-4 gap-4">
                    <AppIcon
                      gradient="from-green-400 to-green-600"
                      icon={
                        <svg
                          className="w-7 h-7"
                          viewBox="0 0 24 24"
                          fill="white"
                        >
                          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
                        </svg>
                      }
                    />
                    <AppIcon
                      gradient="from-blue-500 to-cyan-400"
                      icon={
                        <svg
                          className="w-7 h-7"
                          viewBox="0 0 24 24"
                          fill="white"
                        >
                          <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
                        </svg>
                      }
                    />
                    <AppIcon
                      gradient="from-blue-600 to-blue-700"
                      icon={
                        <svg
                          className="w-7 h-7"
                          viewBox="0 0 24 24"
                          fill="white"
                        >
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
                        </svg>
                      }
                    />
                    <AppIcon
                      gradient="from-indigo-500 to-purple-600"
                      icon={
                        <svg
                          className="w-7 h-7"
                          viewBox="0 0 24 24"
                          fill="white"
                        >
                          <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
                        </svg>
                      }
                    />
                  </div>
                </div>
              </div>

              {/* Home indicator */}
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-white/50 rounded-full"></div>
            </div>
          </div>
        </div>

        {/* Subtle reflection/glow effect */}
        <div className="absolute -inset-4 bg-gradient-to-t from-blue-500/20 via-transparent to-transparent blur-2xl -z-10 opacity-60"></div>
      </div>
    </div>
  );
}

function AppIcon({
  gradient,
  icon,
}: {
  gradient: string;
  icon: React.ReactNode;
}) {
  return (
    <div
      className={`aspect-square bg-gradient-to-br ${gradient} rounded-2xl flex items-center justify-center shadow-lg`}
    >
      {icon}
    </div>
  );
}
