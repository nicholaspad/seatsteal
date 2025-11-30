import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Minus } from "lucide-react";
import { getSubscriptionFeatures } from "@/lib/subscription-constants";
import type { College } from "@/types/api";

interface FAQSectionProps {
  colleges: College[];
}

export function FAQSection({ colleges }: FAQSectionProps) {
  const [openItems, setOpenItems] = useState<number[]>([]);

  // Get subscription features for pricing info
  const freeFeatures = getSubscriptionFeatures("free");
  const plusFeatures = getSubscriptionFeatures("plus");
  const proFeatures = getSubscriptionFeatures("pro");

  // Generate colleges list
  const collegesList =
    colleges.length > 0 ? colleges.map((college) => college.name) : [];

  const faqs: Array<{
    question: string;
    answer: React.ReactNode;
    colleges?: string[];
  }> = [
    {
      question: "Which universities and colleges do you currently support?",
      answer:
        collegesList.length > 0
          ? "We currently support the following universities:"
          : "We currently support multiple universities. We're continuously adding support for more institutions. Contact us to request your school!",
      colleges: collegesList,
    },
    {
      question: "How does SeatSteal work?",
      answer:
        "Subscribe to classes, and SeatSteal continually monitors enrollment status and notifies you when seats become available.",
    },
    {
      question: "Can I monitor multiple courses at once?",
      answer: `Free users can subscribe to ${freeFeatures.maxSubscriptions} course, Plus users can subscribe to ${plusFeatures.maxSubscriptions} courses, and Pro users can subscribe to ${proFeatures.maxSubscriptions} courses.`,
    },
    {
      question: "Can I cancel my subscription anytime?",
      answer:
        "Yes, you can cancel your subscription at any time. You'll maintain access until the end of your billing period.",
    },
    {
      question: "Is my information secure?",
      answer: (
        <>
          Yes. We collect only the information needed to send notifications and
          never ask for your university credentials. Read our{" "}
          <Link to="/privacy" className="underline hover:text-foreground">
            Privacy Policy
          </Link>{" "}
          for more details.
        </>
      ),
    },
  ];

  const toggleItem = (index: number) => {
    setOpenItems((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index],
    );
  };

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {faqs.map((faq, index) => (
        <Card key={index} className="overflow-hidden">
          <CardHeader
            className="cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => toggleItem(index)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-medium text-left">
                {faq.question}
              </CardTitle>
              {openItems.includes(index) ? (
                <Minus className="h-5 w-5 text-muted-foreground" />
              ) : (
                <Plus className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
          {openItems.includes(index) && (
            <CardContent className="pt-0">
              <p className="text-muted-foreground">{faq.answer}</p>
              {faq.colleges && faq.colleges.length > 0 && (
                <div className="mt-3">
                  <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                    {faq.colleges.map((college, collegeIndex) => (
                      <li key={collegeIndex}>{college}</li>
                    ))}
                  </ul>
                  <p className="text-muted-foreground mt-3">
                    We regularly add support for more universities. If you don't
                    see your school,{" "}
                    <a
                      href="https://form.typeform.com/to/oPSf8iXX"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline"
                    >
                      let us know
                    </a>
                    !
                  </p>
                </div>
              )}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}
