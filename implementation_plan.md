# Nexora — Full Platform Implementation Plan

## Executive Summary

After a deep analysis of every backend file, frontend template, CSS stylesheet, and JS module, the following issues and improvements have been identified. They are grouped by **priority** and **area**.

---

## 🔴 Critical Bugs (Must Fix First)

### 1. Hardcoded `rating` and `review_count` on `Item` model
**File:** `app/models.py` — lines 323–324 & 576–581

The `Item` model declares `rating` and `review_count` as real DB columns at lines 323–324, then **redefines them as `@property` methods** that return hardcoded values (4.7 and 982). The properties silently shadow the real columns, so no matter what is stored in the DB, users always see fake data.

**Fix:** Remove the fake `@property` definitions and let the real columns serve the data. Only fall back to a computed value if the column is `None`.

---

### 2. `item-page.html` — Wrong attribute access on `ItemImage`
**File:** `app/templates/item-page.html` — lines 24–25

```jinja
{% for img in item.images[:3] %}
"{{ img.url }}"   {# ← WRONG: model uses img.image_url #}
```
The `ItemImage` model defines the field as `image_url`, not `url`. This silently outputs empty strings in the JSON-LD schema, breaking SEO structured data.

**Fix:** Change to `img.image_url`.

---

### 3. Duplicate template import in `article-page.html`
**File:** `app/templates/article-page.html` — lines 6–7

```jinja
{% from "components/ui/badge.html" import badge %}
{% from "components/ui/badge.html" import badge %}  {# ← duplicate #}
```

**Fix:** Remove the second import.

---

### 4. `record_view` called with wrong signature in `interactions.py`
**File:** `app/routes/interactions.py` — line 297

```python
result = record_view(target_type, target_id)   # ← missing user/ip args
```
The `record_view` function in `interaction_service.py` expects `(target, target_type, user, ip_address)`. This route will throw a `TypeError` at runtime whenever someone hits `POST /view`.

**Fix:** Align arguments with the actual function signature.

---

### 5. Deprecated `datetime.utcnow()` calls
**Files:** `app/routes/interactions.py` — lines 116, 138, 243; `app/scrapers/runner.py` — line 103

Python 3.12+ deprecates `datetime.utcnow()`. All calls must be replaced with `datetime.now(timezone.utc)`.

---

### 6. Deprecated `User.query.get()` in user loader
**File:** `app/__init__.py` — line 52

```python
return User.query.get(int(user_id))  # ← deprecated in SQLAlchemy 2.0
```

**Fix:** Replace with `db.session.get(User, int(user_id))`.

---

### 7. `ContactMessage` model has no `__tablename__`
**File:** `app/models.py` — line 979

Without `__tablename__`, SQLAlchemy auto-names it `contact_message` (singular) instead of the expected `contact_messages` (plural). This can cause table-not-found errors after migrations if the convention changes.

**Fix:** Add `__tablename__ = 'contact_messages'`.

---

### 8. "Forgot Password?" link is empty
**File:** `app/templates/components/base-auth.html` — line 51

```html
<a href="" class="redirect-link">Forgot password?</a>
```
This link does nothing—clicking it reloads the page. The entire password-reset flow is missing.

---

### 9. Registration collects "Full Name" but User model has no `name` field
**File:** `app/templates/components/base-auth.html` — line 27

The auth form renders a `name` input for new users, but `app/routes/auth.py` never reads it and the `User` model has no `name` column. This is dead/misleading UI.

**Fix:** Either add a `name` field to the `User` model and save it, OR remove the full-name field from the form.

---

## 🟠 Security Gaps

### 10. No email verification on registration
**File:** `app/routes/auth.py` — `register()` route

Users can register and immediately access all authenticated features without verifying their email address. `MAIL_ENABLED = False` in `config.py` means the entire email system is off.

**Enhancements needed:**
- Add `is_verified` boolean to `User` model.
- On registration, generate a verification token, send verification email, and mark the account as unverified.
- Block login for unverified accounts (or restrict certain features).
- Add `/verify-email/<token>` route.
- Re-send verification email flow.

---

### 11. No Password Reset / Forgot Password flow
The entire feature is absent. Required routes:
- `GET /forgot-password` — form to enter email.
- `POST /forgot-password` — generates a secure timed token and sends reset email.
- `GET /reset-password/<token>` — validates token (expire after 1hr), shows new password form.
- `POST /reset-password/<token>` — saves hashed new password, invalidates token.

**Model changes:** Add `reset_token` and `reset_token_expires_at` to `User`.

---

### 12. No password confirmation field on registration
Users type a password once. A typo means they're locked out of their account (no reset flow exists either). A "Confirm Password" field must be added with client-side and server-side validation.

---

### 13. "Remember Me" checkbox has no backend logic
**File:** `app/routes/auth.py` — `login()` route

The checkbox is rendered but `request.form.get('remember')` is never read. `login_user(user)` is not passed `remember=True`.

**Fix:** Pass `remember=remember_me` to `login_user()`.

---

### 14. `MAIL_ENABLED = False` hardcoded in config
**File:** `config.py` — line 27

Email is disabled at the code level with a comment "I changed it for some reason after I deployed to Render." All email flows (newsletter confirmation, future password reset, email verification) are silently skipped. This should be driven by environment variable only.

**Fix:**
```python
MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "False") == "True"
```

---

### 15. Missing `SESSION_COOKIE_HTTPONLY`
**File:** `config.py`

`SESSION_COOKIE_SECURE = True` is set but `SESSION_COOKIE_HTTPONLY = True` is missing. Without it, JavaScript can access the session cookie, opening XSS attack surfaces.

---

### 16. No account lockout message on rate limit
**File:** `app/routes/auth.py` — `@limiter.limit("5 per minute")`

The rate limiter will return a generic 429 response. A friendly, branded error page for rate-limited auth attempts should be added via `@app.errorhandler(429)`.

---

## 🟡 Full Responsive CSS Overhaul

> [!WARNING]
> The entire 87KB `style.css` file contains **fewer than 5 media query breakpoints** — most of the layout has **zero responsive rules**. The site is essentially a fixed-width desktop layout on mobile. This is the most visible UX failure.

**Current state (confirmed by search):**
- Only 2 `@media` breakpoints found: one for detail-page grid at `1024px`, one for detail-page title at `768px`.
- The header, navigation, card grids, listing pages, footer, auth forms, comparison page — all lack responsive rules.

**Required breakpoint system (mobile-first):**

| Token | Width | Usage |
|---|---|---|
| `sm` | 480px | Small phones |
| `md` | 768px | Tablets / large phones |
| `lg` | 1024px | Laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1400px | Large screens |

**Files to update:**

#### [MODIFY] `app/static/css/style.css`
The following sections need mobile-first rules added:

1. **`.container`** — needs `max-width` + responsive horizontal padding
2. **`.site-header` / `.header`** — height, padding adjustments per breakpoint
3. **`.main-nav`** — hidden on mobile (already has `md:flex` class hint but no CSS rule for it)
4. **`.mobile-nav`** — needs `display: none` by default and `display: flex` when `.active`
5. **`.hero-slider`** — slide title font size, image aspect ratio for mobile
6. **`.cards-grid` / carousel** — 1 column on mobile, 2 on tablet, 3 on desktop
7. **`.listing-page`** — sidebar collapsed/drawer on mobile
8. **`.catalog-sidebar`** — toggle-able on mobile, always visible on desktop
9. **`.detail-page .container`** — already has 1024px grid rule, but needs intermediate 768px rule
10. **`.footer-grid`** — 1 column on mobile, 2 on tablet, 4 on desktop
11. **`.auth-section` / `.auth-wrapper`** — full-width on mobile, max-width card on desktop
12. **`.compare-page`** — horizontal scroll on mobile
13. **`.search-results`** — stacked on mobile
14. **`.newsletter-block`** — stacked form vs side-by-side

---

## 🟡 UX & Feature Enhancements

### 17. Pagination on catalog and section pages
**Files:** `app/routes/catalog.py`, `app/templates/catalog-page.html`

All listing queries use hard limits (`limit(50)`, `limit(40)`) without pagination. Users cannot see more results. Add SQLAlchemy `.paginate()` and render page controls.

---

### 18. Breadcrumbs on detail pages
**Files:** `app/templates/article-page.html`, `app/templates/item-page.html`, `app/templates/components/detail-page.html`

Users have no visual context of where they are in the site hierarchy. Add breadcrumbs: `Home > Reviews > Article Title`.

---

### 19. Skeleton loaders for AJAX responses
**Files:** `app/static/js/forms.js`, relevant templates

When search results, comments, or subscriptions are loading, there is no loading state. Users see a blank area. Add CSS skeleton loaders for cards and comment lists.

---

### 20. "Back to top" button
A floating button that appears when scrolling past the fold, with smooth scroll-to-top. Pure CSS + minimal JS.

---

### 21. Price filter validation in `/deals`
**File:** `app/routes/catalog.py` — lines 197–200

```python
query = query.filter(ItemVariant.price >= float(active_filters['min_price']))
```
If `min_price` is `"abc"` or empty, this raises `ValueError` and returns a 500 error. Wrap in `try/except` with a graceful fallback.

---

### 22. Safe float casting utility
Create a shared `safe_float(value, default=None)` utility in `app/utils/parsing.py` and use it across all price filter code.

---

### 23. Infinite scroll or "Load More" on home page sections
The home page loads 10 items/articles per section. A "See More" button per section with lazy loading would significantly improve exploration.

---

### 24. Country selector UX
The country selector triggers a full page reload (`window.location.reload()`). This is noticeable and jarring. Use `history.replaceState` or AJAX instead.

---

### 25. JSON-LD schema bug in `item-page.html`
The schema includes `img.url` (wrong attribute, always empty). Fix together with bug #2 above.

---

### 26. Article `published_at` None crash
**File:** `app/templates/article-page.html` — line 73

```jinja
{{ article.published_at.strftime('%b %d, %Y') }}
```
If `published_at` is `None`, this raises `AttributeError`. The card template handles it with `if article.published_at else 'Recent'` but the detail page does not.

**Fix:** Add the same guard in `article-page.html`.

---

### 27. `/deals` route: multiple `.join()` on same table
**File:** `app/routes/catalog.py` — lines 192–206

When both a `store` filter and a `price` filter or a `sort` option are applied, the query joins `ItemVariant` multiple times, causing SQL ambiguity errors. Add `.distinct()` guards or restructure the joins.

---

## 🟢 Email System Overhaul

### 28. Replace raw `smtplib` with Flask-Mail
**File:** `app/utils/email.py`

`Flask-Mail` is already installed (`requirements.txt` line 4 and `extensions.py`). The custom `email.py` bypasses it entirely using raw `smtplib`. This means error handling, TLS negotiation, and retry logic is manual and fragile.

**Fix:** Rewrite `email.py` to use the `mail` extension from `app/extensions.py`. Use `Message` from `flask_mail`.

---

### 29. HTML email templates
The newsletter confirmation email and future password-reset email are plain text. Add basic HTML templates in `app/templates/emails/` for:
- `confirmation.html`
- `password_reset.html`
- `welcome.html`

---

## 🟢 Backend Cleanup & Improvements

### 30. Consolidate and clean up `fetch-all` CLI command
**File:** `app/__init__.py` — lines 99–104

The active `fetch-all` command only runs article fetch. The commented-out version with all 4 steps is the correct one. Clean this up and make it the single authoritative command.

---

### 31. Add `name` or `display_name` to `User` model
Several places would benefit from a user's name (e.g., newsletter greeting, comment author display). Either add a `name` column or derive a display name from the email prefix.

---

### 32. Scraping reliability improvement
**File:** `app/utils/article_extractor.py`

The current approach uses `cloudscraper` + `trafilatura`. For JS-heavy sites this fails silently (returns `None`). The minimum 400-character check is too strict and discards many valid short articles.

**Options (no new heavy deps required):**
- Lower minimum to 150 chars.
- Fall back to `description` field when content extraction fails (already stored from API).
- Add retry logic with a different User-Agent on first failure.

---

### 33. Sentiment API logging
**File:** `app/services/sentiment.py` — line 26

```python
print("Sentiment API error:", e)
```
Replace `print()` with `logger.warning()` for proper log capture in production (Gunicorn swallows stdout).

---

### 34. Remove dead code in `runner.py`
**File:** `app/scrapers/runner.py`

The `run_reddit_fetch()`, `run_amazon_discovery()` functions contain only commented-out code wrapped in docstrings. They are scheduled to run every 12/24h doing nothing. Either remove them from the scheduler or add a proper `pass` with clear status logging.

---

## 🟢 New Features to Add

### 35. User Profile Page
A simple `/profile` page where logged-in users can:
- View their email, join date
- Change their display name
- Change their password (with current password confirmation)
- View subscription status and resend confirmation

---

### 36. Admin notification on new contact message
**File:** `app/services/mailer.py`

The `send_admin_email()` function exists but sends no content about the actual message. Improve the email body to include the user's name, email, subject, and message.

---

### 37. `robots.txt` and `sitemap.xml` improvements
**File:** `app/static/robots.txt` (68 bytes) and `app/routes/base.py`

The sitemap uses `url_for` for items and articles but does NOT use slugs (uses `item_id` and `article_id` integers). This is acceptable, but add `<priority>` and `<changefreq>` tags. The current `sitemap_xml.html` template doesn't include them.

---

## Proposed File Changes Summary

### Backend

| File | Type | Change |
|---|---|---|
| `app/models.py` | MODIFY | Remove hardcoded `rating`/`review_count` properties; add `name`, `is_verified`, `reset_token`, `reset_token_expires_at` to User; add `__tablename__` to ContactMessage |
| `app/routes/auth.py` | MODIFY | Add remember-me, email verification flow, forgot/reset password routes |
| `app/routes/catalog.py` | MODIFY | Fix `record_view` args, safe price casting, join deduplication, add pagination |
| `app/routes/interactions.py` | MODIFY | Fix `record_view` call, replace `datetime.utcnow()` |
| `app/__init__.py` | MODIFY | Fix `db.session.get()` user loader, clean up `fetch-all` CLI |
| `config.py` | MODIFY | Make `MAIL_ENABLED` env-driven, add `SESSION_COOKIE_HTTPONLY` |
| `app/utils/email.py` | MODIFY | Rewrite to use Flask-Mail, support HTML templates |
| `app/utils/parsing.py` | MODIFY | Add `safe_float()` utility |
| `app/services/sentiment.py` | MODIFY | Replace `print()` with `logger.warning()` |
| `app/services/mailer.py` | MODIFY | Improve admin email body |
| `app/templates/emails/` | NEW | `confirmation.html`, `password_reset.html`, `welcome.html` |
| `app/routes/` | ADD | `/forgot-password`, `/reset-password/<token>`, `/verify-email/<token>`, `/profile` routes |
| `app/scrapers/runner.py` | MODIFY | Fix `datetime.utcnow()`, clean up dead scheduler jobs |

### Frontend / Templates

| File | Type | Change |
|---|---|---|
| `app/templates/components/base-auth.html` | MODIFY | Add confirm-password field; wire forgot-password link; fix name field |
| `app/templates/article-page.html` | MODIFY | Remove duplicate badge import; fix `published_at` None guard |
| `app/templates/item-page.html` | MODIFY | Fix `img.url` → `img.image_url` in schema |
| `app/templates/index.html` | MODIFY | Add "Load More" / See All links per section |
| `app/templates/catalog-page.html` | MODIFY | Add pagination controls |
| `app/templates/components/detail-page.html` | MODIFY | Add breadcrumbs |
| `app/templates/partials/header.html` | MODIFY | Ensure mobile nav semantics are correct |
| `app/templates/forgot-password.html` | NEW | Forgot password form |
| `app/templates/reset-password.html` | NEW | Reset password form |
| `app/templates/verify-email.html` | NEW | Email verification success/failure page |
| `app/templates/profile.html` | NEW | User profile page |

### CSS & JS

| File | Type | Change |
|---|---|---|
| `app/static/css/style.css` | MODIFY | Add full mobile-first responsive system (breakpoints sm/md/lg/xl), fix card grids, header, footer, sidebar, auth, compare page |
| `app/static/js/main.js` | MODIFY | Add skeleton loader helpers, back-to-top button logic, sidebar mobile toggle |
| `app/static/js/forms.js` | MODIFY | Add client-side confirm-password validation, show skeleton loaders on AJAX |
| `app/static/js/auth.js` | MODIFY | Password strength indicator |

---

## Verification Plan

### Automated
- `flask db migrate && flask db upgrade` after model changes
- Run app and hit `/login`, `/register`, `/forgot-password`, `/deals?min_price=abc`, `/view` (POST) to confirm no 500 errors
- Check browser dev tools for layout at 375px, 768px, 1280px widths

### Manual
- Log in / register flow end-to-end
- Test responsive layout on Chrome DevTools in mobile emulation (iPhone 14, iPad, Galaxy S)
- Confirm email confirmation link works when `MAIL_ENABLED=True`
- Trigger a password reset and confirm token expires
- Visit `/items/1` and view-source to confirm JSON-LD has correct `image_url`
- Add `min_price=xyz` to `/deals` URL and confirm no crash

---

> [!IMPORTANT]
> **Recommended execution order:**
> 1. Critical bug fixes (#1–#9) — no migrations needed for most
> 2. Security fixes (#10–#16) — requires DB migration for new User fields
> 3. Responsive CSS overhaul (#17) — pure CSS, no risk
> 4. UX enhancements (#18–#27) — incremental, low risk
> 5. Email system (#28–#29) — requires env vars to be set
> 6. New features (#35–#37) — additive, no breaking changes

