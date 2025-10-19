import { IonContent, IonPage } from "@ionic/react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { ArrowRight, Bell, Search, Shield } from "lucide-react";

export default function Home() {
  return (
    <IonPage>
      <IonContent>
        {/* Hero Section */}
        <section className="relative py-20 px-4 text-center bg-gradient-to-b from-background to-muted/20">
          <div className="container mx-auto max-w-4xl space-y-6">
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
              Never Miss a Seat Again
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Get instant notifications when seats open up in your favorite
              classes. SeatSteal helps you register for the courses you need.
            </p>
            <div className="flex gap-4 justify-center pt-4">
              <Button asChild size="lg">
                <Link to="/login">
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/courses">Browse Courses</Link>
              </Button>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-20 px-4">
          <div className="container mx-auto max-w-6xl">
            <h2 className="text-3xl font-bold text-center mb-12">
              How It Works
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <div className="p-4 bg-primary/10 rounded-full">
                    <Search className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <h3 className="text-xl font-semibold">Search for Classes</h3>
                <p className="text-muted-foreground">
                  Browse available courses at your college and find the classes
                  you need.
                </p>
              </div>
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <div className="p-4 bg-primary/10 rounded-full">
                    <Bell className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <h3 className="text-xl font-semibold">Get Notified</h3>
                <p className="text-muted-foreground">
                  Receive instant notifications when a seat becomes available in
                  your class.
                </p>
              </div>
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <div className="p-4 bg-primary/10 rounded-full">
                    <Shield className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <h3 className="text-xl font-semibold">Register Fast</h3>
                <p className="text-muted-foreground">
                  Beat the rush and register for your courses before they fill
                  up again.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 px-4 bg-muted/20">
          <div className="container mx-auto max-w-3xl text-center space-y-6">
            <h2 className="text-3xl font-bold">Ready to Get Started?</h2>
            <p className="text-muted-foreground text-lg">
              Join students already using SeatSteal to get into their dream
              classes.
            </p>
            <Button asChild size="lg">
              <Link to="/login">Sign Up Now</Link>
            </Button>
          </div>
        </section>
      </IonContent>
    </IonPage>
  );
}
