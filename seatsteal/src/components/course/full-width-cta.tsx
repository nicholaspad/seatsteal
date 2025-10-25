import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Lock } from "lucide-react";

export function FullWidthCTA() {
  return (
    // Full-width component that spans all grid columns
    <div className="col-span-full">
      <Card className="border-2 border-primary/20 shadow-lg bg-gradient-to-r from-background to-muted/20">
        <CardContent className="pt-8 pb-8">
          <div className="max-w-2xl mx-auto text-center space-y-6">
            {/* Icon */}
            <div className="flex justify-center">
              <div className="p-4 bg-primary/10 rounded-full">
                <Lock className="h-10 w-10 text-primary" />
              </div>
            </div>

            {/* Heading */}
            <div className="space-y-3">
              {/* <h3 className="text-2xl font-bold">See All Courses</h3> */}
              <p className="text-muted-foreground text-lg">
                Login to browse{" "}
                <span className="font-semibold text-foreground">
                  10,000+ courses
                </span>{" "}
                and get notified when spots become available.
              </p>
            </div>

            {/* Benefits list
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-xl mx-auto text-sm">
              <div className="flex items-center justify-center gap-2">
                <Eye className="h-4 w-4 text-primary flex-shrink-0" />
                <span>View real-time enrollment data</span>
              </div>
              <div className="flex items-center justify-center gap-2">
                <Eye className="h-4 w-4 text-primary flex-shrink-0" />
                <span>Set up notifications for seat openings</span>
              </div>
              <div className="flex items-center justify-center gap-2">
                <Eye className="h-4 w-4 text-primary flex-shrink-0" />
                <span>Search and filter across all universities</span>
              </div>
            </div> */}

            {/* CTA Button */}
            <div>
              <Button
                asChild
                size="lg"
                className="text-lg px-8 py-3 bg-white text-black hover:bg-white/90"
              >
                <Link to="/login">Get started for free</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
