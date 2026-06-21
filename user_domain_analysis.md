# User Domain Intelligence Analysis
### Nexora Admin — Senior Architect Review

---

## 1. User Data Inventory

The user domain is richer than it appears at first glance. Below is a complete inventory of every field and relationship available per entity.

### `User` (core identity)
| Field | Type | Utilized? |
|---|---|---|
| `id` | PK | ✅ |
| `email` | String | ✅ |
| `name` | String(nullable) | ✅ |
| `password_hash` | Text | — (security, not displayed) |
| `google_id` | Text (nullable) | ❌ Not surfaced in admin |
| `provider` | Text (`'google'`/`'local'`) | ✅ Shown in inspect |
| `created_at` | DateTime | ✅ |
| `is_admin` | Boolean | ✅ |
| `is_active` | Boolean | ✅ |
| `is_verified` | Boolean | ✅ Shown in inspect |
| `verified_at` | DateTime | ✅ Shown in inspect |
| `verification_sent_at` | DateTime | ❌ Never surfaced |
| `last_login_at` | DateTime | ✅ |
| `password_changed_at` | DateTime | ✅ Shown in inspect |

### `NewsletterSubscriber`
| Field | Type | Utilized? |
|---|---|---|
| `is_confirmed` | Boolean | ❌ Only `is_active` property shown |
| `created_at` | DateTime | ❌ Subscription date never surfaced |
| `unsubscribed_at` | DateTime | ❌ Never surfaced |
| `confirmation_token` | String | — (internal) |
| `unsubscribe_token` | String | — (internal) |
| `user_id` | FK (nullable) | ✅ Linked to user |

### `UserInterest`
| Field | Type | Utilized? |
|---|---|---|
| `target_type` | String (`'item'`/`'article'`) | ✅ Rendered in inspect |
| `target_id` | Integer | ✅ |
| `interaction_count` | Integer | ✅ Displayed |
| `last_interaction_at` | DateTime | ❌ Never surfaced |

### `UserEntityInterest` (taxonomy affinity scores)
| Field | Type | Utilized? |
|---|---|---|
| `brand_id` | FK → Brand | ✅ Fetched one-by-one (N+1 risk) |
| `category_id` | FK → Category | ✅ Fetched one-by-one (N+1 risk) |
| `topic_id` | FK → Topic | ✅ Fetched one-by-one (N+1 risk) |
| `score` | Float | ✅ Displayed |

### Interaction models (all linked to `User.id`)
| Model | Fields | Additional Unused Metadata |
|---|---|---|
| `View` | user_id, target_type, target_id, created_at | `ip_address` (for anonymous segmentation) |
| `Comment` | user_id, target_type, target_id, content, created_at, sentiment, confidence, parent_id, like_count, dislike_count, replies_count | `sentiment`/`confidence` per-user never aggregated |
| `Reaction` | user_id, target_type, target_id, type, created_at | Reaction type breakdown per-user unused |
| `Save` | user_id, target_type, target_id, created_at | Save composition (content vs items) unused |
| `Share` | user_id, target_type, target_id, channel, created_at | `channel` breakdown per-user unused |
| `ItemClick` | user_id, item_store_link_id, country, user_agent, referrer, created_at | `country`, `referrer` per-user unused |
| `RecommendationImpression` | user_id, entity_ids, entity_type, context_id, created_at | Rec exposure never cross-referenced with user |
| `RecommendationClick` | user_id, entity_id, entity_type, context_id, created_at | Rec CTR per-user never computed |

> [!NOTE]
> `RecommendationClick` is imported in the admin but **never queried or displayed** for individual users.

---

## 2. User Relationship Map

```
User (core)
 ├── NewsletterSubscriber (0..1)
 ├── UserInterest (0..N)
 │    └── UserEntityInterest (0..N) ──→ Category | Topic | Brand
 ├── View (0..N) ──→ Content | Item
 ├── Reaction (0..N) ──→ Content | Item | Comment
 ├── Comment (0..N) ──→ Content | Item
 │    └── Comment (nested replies)
 ├── Save (0..N) ──→ Content | Item
 ├── Share (0..N) ──→ Content | Item
 ├── ItemClick (0..N) ──→ ItemStoreLink
 ├── RecommendationImpression (0..N)
 └── RecommendationClick (0..N)
```

A `User` entity has **10 direct relationship arms** in the database, yet the admin list view surfaces only **7 data points** and the inspect page renders **~14 flat fields**. No relationship is displayed as interactive cross-links to the relevant domain pages.

---

## 3. User Activity Visibility — Gaps & Findings

### What the current system shows
- `last_login_at` as a raw timestamp in both list and inspect pages
- A single-line "recent activity" field that checks only the latest comment OR save

### What it misses
1. **Activity recency tier** — No classification: "Active Today", "Active This Week", "Dormant 30+ days", "Churned 90+ days"
2. **Activity frequency** — No interactions-per-week or interactions-per-month trend
3. **Activity breadth** — User engages with only comments? Only saves? Full spectrum engagement is not distinguished
4. **Activity gap detection** — No flag for users who were once highly engaged and have gone silent
5. **Session density** — `RecommendationImpression` with `created_at` could be used as a proxy for session frequency, but is never queried this way
6. **Recent activity only checks 2 sources** — Comments and saves. Views, reactions, shares, and item clicks are excluded from the "recent activity" summary, producing an incomplete and misleading signal

> [!WARNING]
> The `recent_activity` field in `build_user_inspect_data()` only checks `Comment` and `Save`. A user who primarily views, shares, or clicks items will always show "—" for recent activity, creating a false "inactive" impression.

---

## 4. User Lifecycle Visibility — Gaps & Findings

The `User` model captures a complete lifecycle sequence:

```
registered (created_at)
  → verified (verified_at)       ← email confirmation
  → first_login (last_login_at)  ← approximated; not a true "first login" field
  → password_changed (password_changed_at)
  → subscribed (newsletter: created_at)
  → unsubscribed (newsletter: unsubscribed_at)
  → deactivated (is_active = False)
```

### Current state
- Registration date ✅ shown
- Verification status ✅ shown
- Last login ✅ shown

### Missing lifecycle signals
1. **`verification_sent_at`** — Exists in the model, never shown. Useful for identifying users who registered but never verified: `verified_at IS NULL AND verification_sent_at IS NOT NULL`.
2. **Unverified users cohort** — No filter in the user list for `is_verified = False`. These are low-quality registrations.
3. **Days-to-verify** — `verified_at - created_at` is computable and illuminates onboarding friction.
4. **Days-since-last-login** — Not computed as a human-readable "X days ago" value.
5. **Subscriber lifecycle** — `subscription.created_at` and `subscription.unsubscribed_at` are never shown in the user inspect page. Admins cannot see when a user subscribed, or confirm that the subscriber is the same as the registered user.
6. **Account age** — `created_at` is shown as a date but never expressed as "Member for 2 years, 3 months".
7. **No "churn risk" flag** — There is no computed field or badge for users whose last login was >60 days ago and have never deeply engaged.

---

## 5. User Engagement Visibility — Gaps & Findings

### What exists
An engagement score is computed using weighted counts across 5 interaction types:
```python
ENGAGEMENT_WEIGHTS = {
    'views': 1, 'clicks': 2, 'saves': 3, 'reactions': 2, 'comments': 4
}
```
The score is shown in both the list view and the inspect page. An engagement profile (top action type) is also computed.

### Weaknesses in the current scoring
1. **`shares` are excluded from the score.** Shares are a high-intent action (the user is endorsing and amplifying). They are queried and counted for inspect display but **not included in the weighted score formula**.
2. **`RecommendationClick` is never counted.** This is a strong personalization signal.
3. **Score is lifetime-cumulative.** A user who was active 2 years ago and dormant since scores higher than a recently-joined active user. The score has no time-decay or recency weighting.
4. **No engagement tier / label** — The raw number (e.g. 342) is meaningless without context. A tiered label ("Low", "Medium", "High", "Power User") relative to the entire user population would be actionable.
5. **No trend** — Score today vs. 30 days ago is not computed. Rising or falling engagement is invisible.
6. **Recommendation CTR is unused** — `RecommendationImpression` count is shown, but `RecommendationClick` (a direct signal of recommendation quality and user engagement) is never counted per user.
7. **Sentiment of comments not aggregated** — Each comment carries `sentiment` and `confidence`. Per-user, the admin cannot see whether a user consistently writes positive or negative content.
8. **Reaction type not broken down** — Only total reactions are counted. A user who only ever dislikes content produces the same signal as one who only likes. The `like` vs `dislike` ratio is never computed.
9. **Share channel breakdown unused** — `Share.channel` exists but is never aggregated per-user, so there's no way to see that a specific user almost exclusively shares to Twitter vs. WhatsApp.

---

## 6. User List View — Improvements

### Current columns (7 total)
`Name / Email` · `Role` · `Subscription` · `Status` · `Joined` · `Last Active` · `Engagement Score`

### What the list view is missing
1. **Activity recency badge** — Color-coded chip: 🟢 Active (last 7 days), 🟡 Recent (last 30), 🔴 Dormant (30+ days)
2. **Verification status filter** — No way to list unverified users
3. **Subscriber filter** — "Subscribed" in the row exists but cannot be filtered from the toolbar
4. **Provider filter** — Cannot filter Google vs. local users
5. **Engagement tier column** — A "Low / Medium / High" label is more actionable than a raw number
6. **Sortable columns** — Currently sorted by `User.id DESC` only. No UI column sort by engagement, join date, or last active
7. **Summary bar** — The list has no summary row (total users, total active, total admins, total subscribers). Other domain list pages have `admin_summary_bar`. Users list does not.

> [!IMPORTANT]
> The `admin_summary_bar` macro is already used on every interaction tab (comments, reactions, views, clicks, saves, shares) but is **absent from the users list**. This is the most immediately addressable gap.

---

## 7. User Inspect Page — Improvements

### Current inspect structure
The page renders a **flat key-value table** via `_inspect.html` with one generic `admin-card`. All fields are plain text or raw HTML injected as strings.

### Missing inspect-page capabilities
1. **Interests section is raw HTML injected as a string** — `interests_html` is built by concatenating `<div>` strings server-side with N+1 queries (one `db.session.get` per brand/category/topic). This should be a structured data section with visual bars or chips.
2. **No chart or visualization** — The inspect page has zero visual data representation. For a user with 500+ interactions, a small bar chart of engagement breakdown (views / saves / comments) would be far more readable than six raw integers.
3. **No activity timeline** — There is no chronological view of the user's recent actions. Admins cannot tell in what order actions occurred.
4. **No content affinity section** — While taxonomy entity scores are displayed, there is no listing of the specific articles or items the user has engaged with most.
5. **No linked navigation** — The inspect page has no "See all comments by this user" or "See all saves by this user" deep-links into the Interactions page filtered by this user. The data is there; the navigation is not.
6. **Actions are limited to 4 items** — Toggle Admin / Toggle Active / Debug Personalization / Delete. There is no "Reset Password", "Resend Verification Email", or "Manage Subscription" action.
7. **`verification_sent_at` is never shown** — The field exists on the model and is relevant for diagnosing stuck registrations.
8. **`recent_activity` is only 2 sources** — As noted above, views, reactions, shares and clicks are excluded.
9. **`RecommendationClick` count is never fetched or shown** — `build_user_inspect_data()` imports and queries `RecommendationImpression` but never queries `RecommendationClick`.

---

## 8. Subscriber Insights — Gaps & Findings

### Current state
The user list shows a binary "subscribed / not subscribed" column derived from:
```python
u.newsletter_subscription and u.newsletter_subscription.is_active
```
The `is_active` property evaluates `is_confirmed AND unsubscribed_at IS None`.

### What is invisible to admins
1. **Unconfirmed subscribers** — Users who subscribed but never confirmed their email (`is_confirmed = False`). These exist in the DB but are invisible in the admin; they represent acquisition failures.
2. **Anonymous subscribers** — `NewsletterSubscriber.user_id` is nullable. Anonymous subscribers (not linked to a user account) are completely absent from the user administration view.
3. **Subscriber since date** — `subscription.created_at` is never shown anywhere in the admin.
4. **Unsubscribe date** — `subscription.unsubscribed_at` is never shown. Admins cannot see when someone churned out of the list.
5. **Subscriber-to-user conversion** — There is no view showing anonymous subscribers who later created accounts (matching by email).
6. **Subscription funnel** — No stats panel showing: Total Subscribed / Total Unconfirmed / Total Unsubscribed.
7. **Subscriber vs. engager overlap** — There is no cross-reference between newsletter subscribers and high-engagement users. Are our most-engaged users also subscribed? This is a key audience health metric.

---

## 9. Interest Profile Visibility — Gaps & Findings

### Current state
`UserInterest` records are rendered as concatenated HTML strings in the inspect page. Each interest shows the target name and interaction count. Each `UserEntityInterest` score is rendered beneath it with a label.

### Problems
1. **N+1 query pattern** — For each `UserEntityInterest`, a separate `db.session.get()` call is made for Brand, Category, and Topic. With 20 interest records and 3 entities each, this could generate 60 individual DB round-trips.
2. **No ranked view** — Interests are not sorted by score descending, so the user's strongest affinities are buried.
3. **No domain separation** — Item interests and article interests are mixed without visual distinction.
4. **`last_interaction_at` is never shown** — The model tracks when the interest was last reinforced. Stale interests (score: 80, last interaction: 14 months ago) look identical to fresh interests.
5. **No visualization** — A horizontal bar chart of top 5 entity scores (Brand A: 120 pts, Category B: 95 pts, Topic C: 60 pts) would be instantly comprehensible.
6. **No population context** — An entity score of 45 is meaningless without knowing: is this the highest score any user has for this category? Is this average? Population percentile context is absent.

---

## 10. Analytics Opportunities

These are net-new analytical computations that are fully derivable from existing data without any schema changes.

| Opportunity | Source Data | Description |
|---|---|---|
| **User growth chart** | `User.created_at` | Registrations per day/week/month |
| **Activation rate** | `created_at`, `verified_at` | % of users who verified within 24h, 72h, 7 days |
| **Engagement cohorts** | `created_at` + interaction counts | Group users by join month and track engagement over time |
| **Subscriber quality score** | `NewsletterSubscriber` + interaction counts | Do subscribers engage more than non-subscribers? |
| **Churn risk scoring** | `last_login_at`, engagement score | Users with falling scores and no recent login |
| **Power user identification** | Engagement score distribution | Top 5%, 10%, 25% by score — the "super fans" |
| **Interest freshness decay** | `UserInterest.last_interaction_at` | Identify stale interest profiles needing refresh |
| **Recommendation receptivity** | `RecommendationImpression` / `RecommendationClick` | Per-user CTR on recommendations |
| **Reaction sentiment ratio** | `Reaction.type` count per user | Like-to-dislike ratio as a positivity indicator |
| **Comment sentiment profile** | `Comment.sentiment` aggregated | Average positivity/negativity score per user |
| **Share channel preference** | `Share.channel` grouped by user | Preferred sharing platform per user |
| **Content vs. item affinity** | `UserInterest.target_type` ratio | Does a user primarily engage with articles or products? |
| **Cross-domain breadth score** | Count of distinct target_types across all interactions | Single-domain (articles only) vs. cross-domain users |
| **Days-to-first-engagement** | `created_at` vs. earliest interaction `created_at` | Onboarding effectiveness metric |

---

## 11. Visualization Opportunities

These are chart types directly appropriate to the existing data, ready to be implemented.

### For the Users List Page (aggregate)
| Chart | Type | Data Source |
|---|---|---|
| User growth over time | Line chart | `User.created_at` grouped by week |
| Role distribution | Donut chart | `is_admin` count |
| Active vs. Inactive | Donut chart | `is_active` count |
| Provider split (Google vs. Local) | Bar chart | `provider` count |
| Verification funnel | Funnel / stacked bar | `created_at`, `verified_at`, `is_active` |
| Engagement score distribution | Histogram | Engagement score buckets: 0, 1–50, 51–200, 200+ |
| Newsletter subscription rate | Trend line | `newsletter_subscribers.created_at` over time |

### For the User Inspect Page (per-user)
| Chart | Type | Data Source |
|---|---|---|
| Engagement breakdown | Horizontal bar | views / clicks / saves / reactions / comments / shares |
| Interest entity scores | Top-5 bar | `UserEntityInterest.score` descending |
| Content vs. item split | Donut | `UserInterest.target_type` ratio |
| Activity timeline | Sparkline or mini timeline | Last 30 days of interactions by type |
| Reaction sentiment | Pie | Like count vs. dislike count |

### For a New Subscriber Insights Page
| Chart | Type | Data Source |
|---|---|---|
| Subscription growth | Line | `newsletter_subscribers.created_at` |
| Confirmation funnel | Funnel | Signed up → Confirmed → Active |
| Subscriber vs. non-subscriber engagement | Grouped bar | Avg score for subscribed vs. not |

---

## 12. Existing Data Utilization Score

An honest assessment of how much of the available user-domain data is currently being surfaced and used.

| Domain Area | Fields Available | Fields Used | Utilization |
|---|---|---|---|
| Core User identity | 14 | 10 | **71%** |
| Newsletter Subscriber | 7 | 2 | **29%** |
| UserInterest | 5 | 3 | **60%** |
| UserEntityInterest | 4 | 3 | **75%** |
| View | 5 | 1 (count only) | **20%** |
| Reaction | 5 | 1 (count only) | **20%** |
| Comment | 9 | 2 (count + latest text) | **22%** |
| Save | 4 | 2 (count + latest title) | **50%** |
| Share | 5 | 1 (count only) | **20%** |
| ItemClick | 7 | 1 (count only) | **14%** |
| RecommendationImpression | 5 | 1 (count shown in inspect) | **20%** |
| RecommendationClick | 5 | **0** | **0%** |

**Overall estimated utilization: ~32%**

> [!CAUTION]
> Nearly **68% of the user-domain data that exists in the database is never surfaced to administrators.** The system is collecting rich behavioral signals but discarding them at the presentation layer.

---

## 13. Phased Implementation Roadmap

### Phase 1 — Quick Wins (1–2 sessions, zero schema changes)
*Fix gaps, add missing fields, harden inspect data.*

- [ ] **Add summary bar to Users list** — total users, active, admins, subscribed (mirrors the pattern already used on every interaction tab)
- [ ] **Add subscription filter to Users toolbar** — filter by `is_active` (subscribed / not subscribed / unconfirmed)
- [ ] **Add verification filter to Users toolbar** — filter by `is_verified` (verified / unverified)
- [ ] **Add provider filter to Users toolbar** — Google vs. Local
- [ ] **Expose `verification_sent_at` in inspect page** — helps diagnose stuck onboarding
- [ ] **Expose `subscription.created_at` and `subscription.unsubscribed_at`** in the inspect page subscriber section
- [ ] **Add engagement tier label** alongside the raw score — Low / Medium / High / Power User based on population percentiles
- [ ] **Fix `recent_activity`** to also check Views, Reactions, Shares, and ItemClicks
- [ ] **Add shares to engagement score formula** — the current `ENGAGEMENT_WEIGHTS` dict omits it
- [ ] **Add `RecommendationClick` count** to the inspect page data fetch (already imported, never queried)

---

### Phase 2 — Inspect Page Enrichment (2–3 sessions)
*Transform the flat inspect table into a structured, visual profile.*

- [ ] **Engagement breakdown bar** — horizontal bar chart of all 7 interaction types for the selected user
- [ ] **Top entity interests visualization** — ranked horizontal bars for the top 5 brand/category/topic scores
- [ ] **Fix the N+1 query in interests** — batch-load all brands, categories, and topics in one query per type instead of per-record lookups
- [ ] **Sort interests by score descending**
- [ ] **Add `last_interaction_at` to each interest record** in the display
- [ ] **Add cross-navigation links** — "View all comments →" / "View all saves →" deep-linking to Interactions page filtered by this user's ID
- [ ] **Activity recency badge** on the inspect page header — color-coded "Active Today", "Dormant 14 days", etc.
- [ ] **Reaction like/dislike breakdown** — not just total reactions but the ratio
- [ ] **Comment sentiment summary** — average sentiment across all user comments

---

### Phase 3 — List View Intelligence (2–3 sessions)
*Upgrade the user list from a roster to an operational tool.*

- [ ] **Activity recency column** — replace raw "last active" date with a color-coded recency chip
- [ ] **Engagement tier column** — replace raw score with Low / Medium / High / Power User label
- [ ] **Sortable columns** — allow sorting by engagement score, join date, last active
- [ ] **User growth chart panel** — above the table, showing weekly registrations (mirrors the interaction analytics page)
- [ ] **Engagement distribution chart** — histogram of user engagement score buckets
- [ ] **Provider/role/verification status breakdown** — small donut charts in a stats row

---

### Phase 4 — Subscriber Intelligence Page (2–3 sessions)
*Dedicated subscriber management view (currently absent).*

- [ ] **Dedicated subscriber list** — shows all `NewsletterSubscriber` rows, both linked and anonymous, with status: Confirmed / Unconfirmed / Unsubscribed
- [ ] **Subscription funnel stats** — Total signed up / Confirmed / Active / Unsubscribed
- [ ] **Subscriber growth trend chart**
- [ ] **Subscriber engagement comparison** — avg engagement score for subscribed users vs. non-subscribed registered users
- [ ] **Anonymous subscribers panel** — subscribers with no linked user account (user_id IS NULL)
- [ ] **Subscriber-to-account conversion rate** — anonymous subscribers who later registered (matched by email)

---

### Phase 5 — Audience Analytics Dashboard (3–5 sessions)
*A read-only strategic analytics view for audience health.*

- [ ] **Cohort retention analysis** — users who joined in month X: how many were still active 30/60/90 days later?
- [ ] **Power user segmentation** — top 5% / 10% by engagement score with drill-down
- [ ] **Churn risk list** — users with high historical scores who have not logged in for 60+ days
- [ ] **Onboarding funnel** — registration → verification → first engagement → repeat engagement
- [ ] **Interest profile coverage** — what % of users have any `UserInterest` records? What % have entity scores?
- [ ] **Recommendation receptivity per user** — `RecommendationClick / RecommendationImpression` CTR per user tier
- [ ] **Share channel distribution** — aggregate chart of preferred share channels across all users
- [ ] **Geography heat map** — from `ItemClick.country` and `View.ip_address` (if GeoIP is applied)

---

## Summary Table — Opportunity Priority

| # | Opportunity | Effort | Impact | Phase |
|---|---|---|---|---|
| 1 | Add summary bar to users list | Very Low | High | 1 |
| 2 | Fix `recent_activity` multi-source | Low | High | 1 |
| 3 | Add shares to engagement score | Very Low | Medium | 1 |
| 4 | Add subscription/verification filters | Low | High | 1 |
| 5 | Add RecommendationClick to inspect | Very Low | Medium | 1 |
| 6 | Engagement tier label | Low | High | 1 |
| 7 | Inspect engagement breakdown chart | Medium | High | 2 |
| 8 | Fix N+1 interests query | Low | Medium | 2 |
| 9 | Cross-navigation deep-links in inspect | Low | High | 2 |
| 10 | Sortable user list columns | Medium | Medium | 3 |
| 11 | Activity recency chip in list | Low | High | 3 |
| 12 | User growth chart | Medium | High | 3 |
| 13 | Dedicated subscriber page | High | High | 4 |
| 14 | Subscriber funnel stats | Medium | High | 4 |
| 15 | Cohort retention analysis | High | Very High | 5 |
| 16 | Churn risk list | Medium | High | 5 |
| 17 | Recommendation receptivity CTR | Medium | Medium | 5 |
