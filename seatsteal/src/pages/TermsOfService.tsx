import { IonContent, IonPage } from "@ionic/react";
import { Link } from "react-router-dom";

export default function TermsOfService() {
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

            <h1 className="text-4xl font-bold mb-8">Terms of Service</h1>
            <p className="text-muted-foreground mb-8">
              Last updated: December 2, 2024
            </p>

            <div className="prose prose-invert max-w-none space-y-8">
              {/* Introduction */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  1. Acceptance of Terms
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  Welcome to SeatSteal. By accessing or using our course seat
                  notification service at seatsteal.app (the "Service"), you
                  agree to be bound by these Terms of Service ("Terms"). If you
                  do not agree to these Terms, please do not use our Service.
                </p>
              </section>

              {/* Description of Service */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  2. Description of Service
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  SeatSteal provides a course seat availability monitoring and
                  notification service for college and university students. Our
                  Service allows you to:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    Search for courses at supported colleges and universities
                  </li>
                  <li>
                    Subscribe to notifications for specific class sections
                  </li>
                  <li>
                    Receive email and/or SMS notifications when seats become
                    available in subscribed classes
                  </li>
                </ul>
              </section>

              {/* Account Registration */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  3. Account Registration
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  To use certain features of our Service, you must create an
                  account. When creating an account, you agree to:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    Provide accurate, current, and complete information during
                    registration
                  </li>
                  <li>
                    Maintain and promptly update your account information to
                    keep it accurate
                  </li>
                  <li>
                    Maintain the security of your account credentials and not
                    share them with others
                  </li>
                  <li>
                    Accept responsibility for all activities that occur under
                    your account
                  </li>
                  <li>
                    Notify us immediately of any unauthorized access to or use
                    of your account
                  </li>
                </ul>
              </section>

              {/* SMS Notifications */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  4. SMS/Text Message Notifications
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  By providing your phone number and subscribing to course
                  notifications, you expressly consent to receive SMS text
                  messages from SeatSteal regarding seat availability. You
                  acknowledge and agree that:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">
                      Message Frequency:
                    </strong>{" "}
                    You will receive one SMS notification per subscription when
                    a seat becomes available. Your subscription for that class
                    section automatically ends after notification.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Message and Data Rates:
                    </strong>{" "}
                    Standard message and data rates may apply depending on your
                    mobile carrier and plan.
                  </li>
                  <li>
                    <strong className="text-foreground">Opt-Out:</strong> You
                    can opt out of SMS notifications at any time by
                    unsubscribing from classes on your Dashboard or the course
                    page, or by removing your phone number from your account
                    settings.
                  </li>
                  <li>
                    <strong className="text-foreground">No Guarantees:</strong>{" "}
                    We do not guarantee delivery of SMS messages. Carrier
                    delays, network issues, or other factors outside our control
                    may affect message delivery.
                  </li>
                </ul>
              </section>

              {/* Subscription Plans */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  5. Subscription Plans and Payments
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  SeatSteal offers both free and paid subscription tiers. By
                  purchasing a paid subscription, you agree to the following:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">Billing:</strong> You
                    authorize us to charge your payment method on a recurring
                    basis (monthly or as specified) until you cancel.
                  </li>
                  <li>
                    <strong className="text-foreground">Cancellation:</strong>{" "}
                    You may cancel your subscription at any time. Cancellation
                    will take effect at the end of your current billing period.
                  </li>
                  <li>
                    <strong className="text-foreground">No Refunds:</strong>{" "}
                    Subscription fees are non-refundable except as required by
                    law.
                  </li>
                  <li>
                    <strong className="text-foreground">Price Changes:</strong>{" "}
                    We reserve the right to change subscription prices. We will
                    provide notice of price changes before they take effect.
                  </li>
                </ul>
              </section>

              {/* Acceptable Use */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  6. Acceptable Use Policy
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  You agree not to use our Service to:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    Violate any applicable laws, regulations, or these Terms
                  </li>
                  <li>
                    Attempt to gain unauthorized access to our systems or other
                    users' accounts
                  </li>
                  <li>
                    Interfere with or disrupt the operation of our Service
                  </li>
                  <li>
                    Use automated means (bots, scrapers, etc.) to access our
                    Service without our express written permission
                  </li>
                  <li>
                    Resell, redistribute, or commercially exploit our Service
                    without authorization
                  </li>
                  <li>Submit false, inaccurate, or misleading information</li>
                  <li>Harass, abuse, or harm other users or our staff</li>
                </ul>
              </section>

              {/* Disclaimer */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  7. Disclaimer of Warranties
                </h2>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT
                  WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. WE
                  SPECIFICALLY DISCLAIM:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
                  <li>
                    <strong className="text-foreground">
                      No Guarantee of Enrollment:
                    </strong>{" "}
                    We do not guarantee that you will be able to enroll in any
                    course. Receiving a notification does not guarantee seat
                    availability at the time you attempt to enroll.
                  </li>
                  <li>
                    <strong className="text-foreground">Data Accuracy:</strong>{" "}
                    While we strive to provide accurate information, course
                    data, seat availability, and enrollment statuses are sourced
                    from university systems and may not always be current or
                    accurate.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Service Availability:
                    </strong>{" "}
                    We do not guarantee uninterrupted access to our Service.
                    Maintenance, updates, or unforeseen issues may cause
                    temporary unavailability.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Notification Delivery:
                    </strong>{" "}
                    We do not guarantee that notifications will be delivered
                    instantly or at all due to factors beyond our control.
                  </li>
                </ul>
              </section>

              {/* Limitation of Liability */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  8. Limitation of Liability
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, SEATSTEAL AND ITS
                  OFFICERS, DIRECTORS, EMPLOYEES, AND AGENTS SHALL NOT BE LIABLE
                  FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR
                  PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF
                  PROFITS, DATA, USE, OR OTHER INTANGIBLE LOSSES, RESULTING FROM
                  (A) YOUR USE OR INABILITY TO USE THE SERVICE; (B) FAILURE TO
                  RECEIVE NOTIFICATIONS OR SECURE ENROLLMENT IN ANY COURSE; (C)
                  UNAUTHORIZED ACCESS TO OR ALTERATION OF YOUR DATA; OR (D) ANY
                  OTHER MATTER RELATING TO THE SERVICE.
                </p>
              </section>

              {/* Indemnification */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  9. Indemnification
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  You agree to indemnify, defend, and hold harmless SeatSteal
                  and its officers, directors, employees, and agents from and
                  against any claims, liabilities, damages, losses, and
                  expenses, including reasonable attorneys' fees, arising out of
                  or in any way connected with your access to or use of the
                  Service, your violation of these Terms, or your violation of
                  any rights of any third party.
                </p>
              </section>

              {/* Termination */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">10. Termination</h2>
                <p className="text-muted-foreground leading-relaxed">
                  We reserve the right to suspend or terminate your account and
                  access to the Service at any time, with or without cause, and
                  with or without notice. Upon termination, your right to use
                  the Service will immediately cease. You may also delete your
                  account at any time by contacting us at{" "}
                  <a
                    href="mailto:support@seatsteal.app"
                    className="text-white underline hover:text-gray-300"
                  >
                    support@seatsteal.app
                  </a>
                  .
                </p>
              </section>

              {/* Intellectual Property */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  11. Intellectual Property
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  The Service and its original content, features, and
                  functionality are owned by SeatSteal and are protected by
                  international copyright, trademark, patent, trade secret, and
                  other intellectual property laws. You may not copy, modify,
                  distribute, sell, or lease any part of our Service without our
                  prior written consent.
                </p>
              </section>

              {/* Changes to Terms */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  12. Changes to These Terms
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  We reserve the right to modify these Terms at any time. We
                  will notify you of any changes by posting the new Terms on
                  this page and updating the "Last updated" date. Your continued
                  use of the Service after any such changes constitutes your
                  acceptance of the new Terms.
                </p>
              </section>

              {/* Governing Law */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  13. Governing Law
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  These Terms shall be governed by and construed in accordance
                  with the laws of the United States, without regard to its
                  conflict of law provisions. Any disputes arising under or in
                  connection with these Terms shall be subject to the exclusive
                  jurisdiction of the courts located in the United States.
                </p>
              </section>

              {/* Severability */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">
                  14. Severability
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  If any provision of these Terms is found to be unenforceable
                  or invalid, that provision shall be limited or eliminated to
                  the minimum extent necessary so that these Terms shall
                  otherwise remain in full force and effect.
                </p>
              </section>

              {/* Contact Us */}
              <section>
                <h2 className="text-2xl font-semibold mb-4">15. Contact Us</h2>
                <p className="text-muted-foreground leading-relaxed">
                  If you have any questions about these Terms of Service, please
                  contact us at:
                </p>
                <div className="mt-4 p-4 bg-muted/30 rounded-lg">
                  <p className="text-foreground">
                    <strong>SeatSteal</strong>
                  </p>
                  <p className="text-muted-foreground">
                    Email:{" "}
                    <a
                      href="mailto:support@seatsteal.app"
                      className="text-white underline hover:text-gray-300"
                    >
                      support@seatsteal.app
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
        </div>
      </IonContent>
    </IonPage>
  );
}
