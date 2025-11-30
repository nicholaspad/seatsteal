import { IonContent, IonPage } from "@ionic/react";
import { Link } from "react-router-dom";
import { Footer } from "@/components/layout/Footer";

export default function PrivacyPolicy() {
  return (
    <IonPage>
      <IonContent>
        <div className="min-h-screen bg-black text-foreground">
          <div className="container mx-auto px-4 py-12 max-w-4xl">
            {/* Header */}
            <div className="mb-8">
              <Link
                to="/"
                className="text-muted-foreground hover:text-foreground transition-colors text-sm"
              >
                ← Back to Home
              </Link>
            </div>

            <h1 className="text-4xl font-bold mb-8">Privacy Policy</h1>
            <p className="text-muted-foreground mb-8">
              Last updated: November 30, 2024
            </p>

            <div className="prose prose-invert max-w-none space-y-8">
              {/* Introduction */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
                <p className="text-muted-foreground leading-relaxed">
                  Welcome to SeatSteal ("we," "our," or "us"). We are committed
                  to protecting your privacy and ensuring transparency about how
                  we collect, use, and safeguard your personal information. This
                  Privacy Policy explains our practices regarding the data we
                  collect when you use our course seat notification service at
                  seatsteal.app (the "Service").
                </p>
              </section>

              {/* Information We Collect */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  2. Information We Collect
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  We collect the following types of information:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">Email Address:</strong>{" "}
                    Collected when you create an account or sign in. Used for
                    account authentication and optional email notifications.
                  </li>
                  <li>
                    <strong className="text-foreground">Phone Number:</strong>{" "}
                    Collected when you opt in to receive SMS notifications. Used
                    exclusively for sending text message alerts about course
                    seat availability.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      College/University Selection:
                    </strong>{" "}
                    The college or university you select to help filter and
                    display relevant courses.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Course Subscription Data:
                    </strong>{" "}
                    The courses and class sections you subscribe to for seat
                    availability notifications.
                  </li>
                </ul>
              </section>

              {/* How We Use Your Information */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  3. How We Use Your Information
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  We use the information we collect for the following purposes:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">
                      SMS Notifications:
                    </strong>{" "}
                    To send you text message alerts when a seat becomes
                    available in a course section you have subscribed to.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Service Delivery:
                    </strong>{" "}
                    To provide, maintain, and improve our course seat monitoring
                    and notification service.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Account Management:
                    </strong>{" "}
                    To authenticate your account and manage your subscription
                    preferences.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Customer Support:
                    </strong>{" "}
                    To respond to your inquiries and provide assistance.
                  </li>
                </ul>
              </section>

              {/* SMS/Text Message Communications */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  4. SMS/Text Message Communications
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  When you provide your phone number and subscribe to course
                  notifications, you consent to receive SMS text messages from
                  SeatSteal. Here's what you need to know:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">
                      Message Content:
                    </strong>{" "}
                    Messages will notify you when a seat becomes available in a
                    course section you've subscribed to. Example: "🎉 Seat
                    available in CS123! Section P01 at Cornell University is now
                    open."
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Message Frequency:
                    </strong>{" "}
                    You will receive one SMS notification per subscription when
                    a seat becomes available. After notification, your
                    subscription for that specific class section is
                    automatically ended.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Standard Rates Apply:
                    </strong>{" "}
                    Message and data rates may apply depending on your mobile
                    carrier and plan.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      No Sharing for Marketing:
                    </strong>{" "}
                    We will never sell, rent, or share your phone number with
                    third parties for marketing purposes.
                  </li>
                </ul>
              </section>

              {/* How to Opt Out */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  5. How to Opt Out of SMS Notifications
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  You can opt out of SMS notifications at any time using any of
                  the following methods:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">
                      Via the Dashboard:
                    </strong>{" "}
                    Log in to your account, navigate to your{" "}
                    <Link
                      to="/dashboard"
                      className="text-white underline hover:text-gray-300"
                    >
                      Dashboard
                    </Link>
                    , and click "Unsubscribe" on any active subscription.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Via the Course Page:
                    </strong>{" "}
                    Navigate to the course page and click the "Unsubscribe"
                    button on the class section you no longer wish to be
                    notified about.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Automatic Unsubscription:
                    </strong>{" "}
                    After you receive a notification that a seat is available,
                    your subscription for that class section is automatically
                    ended.
                  </li>
                  <li>
                    <strong className="text-foreground">Contact Us:</strong>{" "}
                    Email us at{" "}
                    <a
                      href="mailto:privacy@seatsteal.app"
                      className="text-white underline hover:text-gray-300"
                    >
                      privacy@seatsteal.app
                    </a>{" "}
                    to request removal of your phone number from our system.
                  </li>
                </ul>
              </section>

              {/* Third-Party Services */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  6. Third-Party Services
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  We use the following third-party services to operate
                  SeatSteal:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">Twilio:</strong> We use
                    Twilio to send SMS text messages. When we send you an SMS,
                    your phone number is transmitted to Twilio for message
                    delivery. Twilio's privacy practices are governed by their{" "}
                    <a
                      href="https://www.twilio.com/legal/privacy"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-white underline hover:text-gray-300"
                    >
                      Privacy Policy
                    </a>
                    .
                  </li>
                  <li>
                    <strong className="text-foreground">Supabase:</strong> We
                    use Supabase for authentication and data storage.
                  </li>
                  <li>
                    <strong className="text-foreground">Vercel:</strong> We use
                    Vercel for hosting and analytics.
                  </li>
                </ul>
              </section>

              {/* Data Retention */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  7. Data Retention
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  We retain your personal information for as long as your
                  account is active or as needed to provide you with our
                  services. You may request deletion of your account and
                  associated data at any time by contacting us at{" "}
                  <a
                    href="mailto:privacy@seatsteal.app"
                    className="text-white underline hover:text-gray-300"
                  >
                    privacy@seatsteal.app
                  </a>
                  . Upon account deletion, we will remove your personal
                  information from our systems, except where retention is
                  required by law or for legitimate business purposes (such as
                  fraud prevention).
                </p>
              </section>

              {/* Data Security */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  8. Data Security
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  We implement industry-standard security measures to protect
                  your personal information, including encryption of data in
                  transit and at rest, secure authentication practices, and
                  regular security assessments. However, no method of
                  transmission over the Internet or electronic storage is 100%
                  secure, and we cannot guarantee absolute security.
                </p>
              </section>

              {/* Your Rights */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">9. Your Rights</h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  Depending on your location, you may have the following rights:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">Access:</strong> The
                    right to request a copy of the personal information we hold
                    about you.
                  </li>
                  <li>
                    <strong className="text-foreground">Correction:</strong> The
                    right to request correction of inaccurate personal
                    information.
                  </li>
                  <li>
                    <strong className="text-foreground">Deletion:</strong> The
                    right to request deletion of your personal information.
                  </li>
                  <li>
                    <strong className="text-foreground">Opt-Out:</strong> The
                    right to opt out of marketing communications and SMS
                    notifications.
                  </li>
                </ul>
                <p className="text-muted-foreground leading-relaxed mt-4">
                  To exercise any of these rights, please contact us at{" "}
                  <a
                    href="mailto:privacy@seatsteal.app"
                    className="text-white underline hover:text-gray-300"
                  >
                    privacy@seatsteal.app
                  </a>
                  .
                </p>
              </section>

              {/* Children's Privacy */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  10. Children's Privacy
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  Our Service is intended for users who are at least 13 years of
                  age. We do not knowingly collect personal information from
                  children under 13. If we become aware that we have collected
                  personal information from a child under 13, we will take steps
                  to delete such information.
                </p>
              </section>

              {/* Changes to This Policy */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  11. Changes to This Privacy Policy
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  We may update this Privacy Policy from time to time. We will
                  notify you of any changes by posting the new Privacy Policy on
                  this page and updating the "Last updated" date. We encourage
                  you to review this Privacy Policy periodically for any
                  changes.
                </p>
              </section>

              {/* Contact Us */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">12. Contact Us</h2>
                <p className="text-muted-foreground leading-relaxed">
                  If you have any questions about this Privacy Policy or our
                  data practices, please contact us at:
                </p>
                <div className="mt-4 p-4 bg-muted/30 rounded-lg">
                  <p className="text-foreground">
                    <strong>SeatSteal</strong>
                  </p>
                  <p className="text-muted-foreground">
                    Email:{" "}
                    <a
                      href="mailto:privacy@seatsteal.app"
                      className="text-white underline hover:text-gray-300"
                    >
                      privacy@seatsteal.app
                    </a>
                  </p>
                  <p className="text-muted-foreground">
                    Website:{" "}
                    <a
                      href="https://seatsteal.app"
                      className="text-white underline hover:text-gray-300"
                    >
                      seatsteal.app
                    </a>
                  </p>
                </div>
              </section>
            </div>
          </div>

          {/* Footer */}
          <Footer />
        </div>
      </IonContent>
    </IonPage>
  );
}
