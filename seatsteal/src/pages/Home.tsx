import { IonContent, IonPage } from "@ionic/react";
import { useEffect, useState } from "react";
import { FAQSection } from "@/components/home/faq-section";
import { PricingTiers } from "@/components/home/pricing-tiers";
import type { College } from "@/types/api";
import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

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
      console.error("Failed to load colleges:", error);
    }
    return [];
  }
}

export default function Home() {
  const [colleges, setColleges] = useState<College[]>([]);

  useEffect(() => {
    // Handle hash scrolling for /#pricing links
    const handleHashScroll = () => {
      const hash = window.location.hash;
      if (hash) {
        const elementId = hash.substring(1);
        const element = document.getElementById(elementId);
        if (element) {
          setTimeout(() => {
            element.scrollIntoView({
              behavior: "smooth",
              block: "start",
            });
          }, 100);
        }
      }
    };

    handleHashScroll();
    window.addEventListener("popstate", handleHashScroll);

    // Fetch colleges data
    getColleges().then(setColleges);

    return () => {
      window.removeEventListener("popstate", handleHashScroll);
    };
  }, []);

  return (
    <IonPage>
      <IonContent>
        <div className="space-y-20 bg-background text-foreground">
          {/* Hero Section */}
          <section className="min-h-screen flex items-center justify-center relative overflow-hidden bg-black">
            <div className="absolute inset-0 bg-gradient-to-br from-black via-black to-black"></div>
            <div className="container mx-auto px-4 text-center space-y-8 relative z-10">
              <div className="space-y-6">
                <h1 className="text-6xl md:text-8xl lg:text-9xl font-bold tracking-tight text-white drop-shadow-lg">
                  Course full?
                </h1>
                <p className="text-2xl md:text-3xl text-gray-200 drop-shadow-md flex items-center justify-center gap-3">
                  <span className="relative">
                    <span className="block w-3 h-3 bg-green-500 rounded-full animate-ping"></span>
                    <span className="absolute inset-0 w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
                  </span>
                  Get notified when a spot opens.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mt-12">
                <Button
                  asChild
                  size="lg"
                  className="text-lg px-8 py-6 bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <a
                    href="https://form.typeform.com/to/mi3IrgGR"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Request early access
                  </a>
                </Button>
              </div>

              <div className="flex justify-center mt-4">
                <a
                  href="https://form.typeform.com/to/oPSf8iXX"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-300 hover:text-white transition-colors flex items-center gap-2 text-sm"
                >
                  Request a college
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
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
          <section id="pricing" className="bg-muted/30 py-16">
            <div className="container mx-auto px-4">
              <div className="text-center space-y-4 mb-12">
                <h2 className="text-3xl md:text-4xl font-bold">Plans</h2>
              </div>
              <PricingTiers />
            </div>
          </section>

          {/* FAQ */}
          <section className="container mx-auto px-4 pb-16">
            <div className="text-center space-y-4 mb-12">
              <h2 className="text-3xl md:text-4xl font-bold">FAQs</h2>
            </div>
            <FAQSection colleges={colleges} />
          </section>

          {/* Testimonials */}
          {/* <section className="bg-muted/30 py-16">
            <div className="container mx-auto px-4">
              <div className="text-center space-y-4 mb-12">
                <h2 className="text-3xl md:text-4xl font-bold">
                  What Students Say
                </h2>
                <p className="text-xl text-muted-foreground">
                  Real success stories from students who got their courses
                </p>
              </div>
              <Testimonials />
            </div>
          </section> */}
        </div>
      </IonContent>
    </IonPage>
  );
}
