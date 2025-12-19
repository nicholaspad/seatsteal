# SeatSteal Growth Opportunities

Analysis of low-hanging fruit to increase profitability and user stickiness.

## High-Impact, Low-Effort Opportunities

### 1. Upgrade CTAs in Dashboard (Profitability) ✅ Implemented
Add subtle upgrade prompts for free users - next to tier badge and when hitting subscription limits.

### 2. Annual Billing Option (Profitability) ✅ Implemented
Add annual plans with ~17% discount:
- Plus: $10/year (vs $12/year monthly)
- Pro: $40/year (vs $48/year monthly)

### 3. Referral Program (Growth) ✅ Implemented
Give both referrer and referee 1 week of Pro free via Stripe coupon.

### 4. Promo/Coupon Codes (Profitability)
Enable Stripe coupon codes for welcome discounts, seasonal promos, and partner promotions.

### 5. Empty Dashboard Onboarding (Stickiness)
Add getting started checklist, quick tips, and course discovery guide for new users.

### 6. Welcome Email Sequence (Stickiness)
Automated emails: welcome, "add your first course" reminder, weekly digest.

### 7. Expose Pro Features More Prominently (Profitability)
Show blurred Pro-only features (watcher count, analytics) with upgrade prompts.

### 8. Re-Engagement Emails (Stickiness)
Automated emails for inactive users, canceled subscriptions, dormant accounts.

## Medium-Effort Opportunities

### 9. Push Notifications (Stickiness)
Web push as free feature, keeping SMS as Plus+ upsell.

### 10. Weekly Digest Email (Stickiness)
Summary of seats opened, notifications received, upgrade nudge.

### 11. Free Trial Period (Profitability)
7-day Plus trial for new signups (15-25% typical conversion).

### 12. Watcher Count as Social Proof (Profitability)
Show "X students watching" on course pages to create FOMO.

## Impact Matrix

| Opportunity | Impact | Effort | Target |
|-------------|--------|--------|--------|
| Upgrade CTAs | High | Low | Profitability |
| Annual billing | High | Low | Profitability |
| Referral program | High | Medium | Growth |
| Promo codes | Medium | Low | Profitability |
| Onboarding | High | Low | Stickiness |
| Welcome emails | High | Medium | Stickiness |
| Pro feature exposure | High | Low | Profitability |
| Re-engagement emails | Medium | Medium | Stickiness |
| Push notifications | Medium | Medium | Stickiness |
| Weekly digest | Medium | Low | Stickiness |
| Free trial | High | Medium | Profitability |

---

## Manual Setup Required

### 1. Upgrade CTAs - No setup required
The upgrade button appears automatically for free users on the dashboard.

### 2. Annual Billing - Stripe Setup Required

You need to create annual price products in Stripe and add the price IDs to your environment:

1. Go to [Stripe Dashboard → Products](https://dashboard.stripe.com/products)
2. For each tier (Plus, Pro), add a new price:
   - **Plus Annual**: $10/year recurring
   - **Pro Annual**: $40/year recurring
3. Copy the price IDs (start with `price_`)
4. Add to your `.env` file:
   ```
   STRIPE_PLUS_ANNUAL_PRICE_ID=price_xxxxx
   STRIPE_PRO_ANNUAL_PRICE_ID=price_xxxxx
   ```
5. Redeploy the backend

**Note:** If annual price IDs are not set, the pricing page will still work but will fall back to monthly billing.

### 3. Referral Program - Database Migration + Stripe Setup

#### Database Migration
Run the Alembic migration to create the `referrals` table:
```bash
cd webapp
alembic upgrade head
```

#### How Referrals Work
1. Users get a unique referral code on their dashboard
2. They share their referral link: `https://seatsteal.app/?ref=ABCD1234`
3. New users who sign up via the link get the code stored
4. When the referee subscribes, both get 1 week of Pro free via Stripe coupon

#### Stripe Coupon Behavior
The referral system automatically creates Stripe coupons when rewards are applied:
- Creates a 100% off coupon for the next billing cycle
- Applied to the customer's Stripe account
- No manual Stripe coupon setup needed - coupons are created programmatically

---

## Files Changed

### Frontend
- `seatsteal/src/components/class/user-dashboard.tsx` - Added upgrade CTA for free users, added ReferralCard
- `seatsteal/src/components/home/pricing-tiers.tsx` - Added monthly/annual billing toggle
- `seatsteal/src/components/referral/ReferralCard.tsx` - New referral card component
- `seatsteal/src/lib/subscription-constants.ts` - Added annual pricing
- `seatsteal/src/pages/Home.tsx` - Captures referral code from URL
- `seatsteal/src/pages/AuthCallback.tsx` - Applies referral code after signup

### Backend
- `webapp/config.py` - Added annual price ID settings
- `webapp/utils/stripe_utils.py` - Updated for annual billing
- `webapp/api/routes/stripe.py` - Added interval parameter, referral reward logic
- `webapp/api/routes/referrals.py` - New referral API routes
- `webapp/models/referral.py` - New referral database model
- `webapp/models/__init__.py` - Registered Referral model
- `webapp/app.py` - Registered referrals router
- `webapp/alembic/versions/015_add_referrals_table.py` - Migration for referrals table
