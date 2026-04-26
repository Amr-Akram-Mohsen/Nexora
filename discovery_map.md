# 🗺️ Nexora Discovery & Source Alignment Map

This document serves as the master reference for how content is routed, queried, and enriched across the Nexora platform.

---

## 🧩 1. Source Strengths & Section Alignment

| Section | 🥇 Primary Source | 🥈 Secondary Source | Logic / Strategy |
| :--- | :--- | :--- | :--- |
| **News** | GNews / NewsAPI | RSS | Focus on high-signal announcements and launches. |
| **Reviews** | YouTube / RSS | Reddit | Technical depth + Visual testing + Real community sentiment. |
| **Tutorials** | YouTube | RSS | Focus on "How-to" and "Guide" content. |
| **Trends** | NewsAPI / GNews | Reddit | Market trends + Emerging community "hype." |
| **Community**| Reddit | — | Authentic user discussion and peer-to-peer feedback. |

---

## 🗂 2. Category Strategies

### 🔌 Electronics
*   **Strategy**: Multi-source blending.
*   **Sources**: NewsAPI (Launches) + YouTube (Reviews) + Reddit (Comparisons).
*   **Key Facets**: Battery life, Performance, Price Tier.

### 🌸 Perfumes
*   **Strategy**: **Reddit Dominant**.
*   **Sources**: Reddit (Primary) + YouTube (Influencers).
*   **Rule**: Skip NewsAPI (low signal). Focus on "Scent profile" and "Longevity."

### 👜 Accessories
*   **Strategy**: Community & Niche driven.
*   **Sources**: YouTube + RSS (Niche Blogs) + Reddit.
*   **Key Facets**: Material, Style, Gender.

---

## 🏗 3. Query Building Architecture

Every query is constructed using a layered approach:
`[Category/Brand] + [Intent Keyword] + [Year/Random Qualifier]`

### 🔹 Intent Keywords
*   **Review**: "review", "worth it", "hands on"
*   **News**: "launch", "release", "announcement"
*   **Tutorial**: "how to", "guide", "setup"
*   **Comparison**: "vs", "comparison"

---

## 🏷 4. Enrichment & Detection Logic

### 🧠 Brand Detector
*   Uses `TAXONOMY["brands"]` to find canonical names and aliases.
*   Strict word-boundary regex for high precision.

### 🎯 Facet Detector
*   **Intent**: Extracts unboxing, impressions, and guides.
*   **Gender**: Specific focus on Perfumes/Accessories (Men, Women, Unisex).
*   **Attributes**: Category-specific (e.g., "Long-lasting" for Perfumes, "Waterproof" for Tech).

---

## ⚠️ Maintenance Notes
*   **API Quotas**: YouTube (10k units), NewsAPI/GNews (100 req).
*   **Discovery**: Runs periodically via `DiscoveryManager`.
*   **Cleaning**: Aggressively strips tracking params and structural whitespace.
