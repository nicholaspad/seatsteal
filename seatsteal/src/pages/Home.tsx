import { IonContent, IonPage } from "@ionic/react";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { FAQSection } from "@/components/home/faq-section";
import { PricingTiers } from "@/components/home/pricing-tiers";
import { ReferralAlert } from "@/components/referral/ReferralAlert";
import { IPhoneMockup } from "@/components/home/iphone-mockup";
import type { College } from "@/types/api";
import { Button } from "@/components/ui/button";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { logError } from "@/lib/logger";

async function getColleges(): Promise<College[]> {
  try {
    const response = await fetchWithToasts("/api/colleges?active=true");
    if (response.ok) {
      const data = await response.json();
      return data.data || [];
    }
    return [];
  } catch (error) {
    if (!(error instanceof ServerErrorWithToast)) {
      logError("Failed to load colleges", error);
    }
    return [];
  }
}

export default function Home() {
  const [colleges, setColleges] = useState<College[]>([]);
  const location = useLocation();

  useEffect(() => {
    // Fetch colleges data
    getColleges().then(setColleges);
  }, []);

  // Capture referral code from URL and store in localStorage
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const refCode = params.get("ref");
    if (refCode) {
      localStorage.setItem("referral_code", refCode.toUpperCase());
    }
  }, [location.search]);

  // Auto-scroll to plans section when #plans hash is present
  useEffect(() => {
    if (location.hash === "#plans") {
      // Small delay to ensure the DOM is ready
      const timeoutId = setTimeout(() => {
        const element = document.getElementById("plans");
        if (element) {
          element.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [location.hash]);

  return (
    <IonPage>
      <IonContent>
        <ReferralAlert />
        <div className="bg-black text-foreground">
          {/* Hero Section */}
          <section className="min-h-screen flex flex-col relative overflow-hidden bg-black">
            <div className="absolute inset-0 bg-gradient-to-br from-black via-black to-black"></div>

            {/* Main content - centered vertically */}
            <div className="flex-1 flex items-center justify-center">
              <div className="container mx-auto px-4 text-center space-y-8 relative z-10">
                <div className="space-y-4">
                  <h1
                    className="text-6xl md:text-8xl lg:text-9xl tracking-tight text-white drop-shadow-lg"
                    style={{ fontWeight: 800 }}
                  >
                    Course full?
                  </h1>
                  <p className="text-2xl md:text-3xl text-gray-200 drop-shadow-md flex items-center justify-center gap-3">
                    <span className="relative w-5 h-5">
                      {/* Radar sweep animation */}
                      <span className="absolute inset-0 rounded-full bg-green-500/20"></span>
                      <span className="absolute inset-0 rounded-full bg-gradient-conic from-transparent via-transparent to-green-400 animate-radar"></span>
                      <span className="absolute inset-[3px] rounded-full bg-black"></span>
                      <span className="absolute inset-[5px] rounded-full bg-green-400"></span>
                    </span>
                    Get notified when a seat opens up.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mt-12">
                  <Button
                    asChild
                    size="lg"
                    className="text-lg px-6 py-4 bg-white text-black hover:bg-white/90"
                  >
                    <a href="/login">Get started</a>
                  </Button>
                  <Button
                    asChild
                    size="lg"
                    variant="outline"
                    className="text-lg px-6 py-4 border-white bg-black text-white hover:bg-white/10"
                  >
                    <a
                      href="https://forms.gle/nh2T76j8Pysp1rax5"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Request a college
                    </a>
                  </Button>
                </div>
              </div>
            </div>

            {/* iPhone Mockup - positioned at bottom, only top visible */}
            <IPhoneMockup />
          </section>

          {/* Social Proof Stats */}
          {/* <section className="">
            <div className="container mx-auto px-4">
              <div className="text-center space-y-4 mb-12">
                <h2 className="text-3xl md:text-4xl font-bold">
                  Trusted by Students Everywhere
                </h2>
                <p className="text-xl text-muted-foreground">
                  Join the community that never misses out
                </p>
              </div>
              <Suspense fallback={<div className="h-32 bg-muted rounded"></div>}>
                <AnimatedStats />
              </Suspense>
            </div>
          </section> */}

          {/* Pricing */}
          <section id="plans" className="bg-muted/30 py-16">
            <div className="container mx-auto px-4">
              <div className="text-center space-y-4 mb-4">
                <h2 className="text-3xl md:text-4xl font-bold">Plans</h2>
              </div>
              <PricingTiers />
            </div>
          </section>

          {/* FAQ */}
          <section className="container mx-auto px-4 pb-16">
            <div className="text-center space-y-4 mb-4 mt-16">
              <h2 className="text-3xl md:text-4xl font-bold">FAQs</h2>
            </div>
            <FAQSection colleges={colleges} />
          </section>
        </div>
      </IonContent>
    </IonPage>
  );
}
