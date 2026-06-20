"""
nutrabay_tinyfish_fetch.py  —  Enhanced scraper using TinyFish FETCH API
Useful when direct Amazon scraping is blocked (captcha / 503).
TinyFish Fetch renders the page in a real browser and returns clean HTML.

Endpoint: POST https://api.fetch.tinyfish.ai
Docs    : https://tinyfish.ai/docs/fetch

Usage:
    export TINYFISH_API_KEY="your_api_key_here"
    python nutrabay_tinyfish_fetch.py
"""

import os
import csv
import time
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TINYFISH_API_KEY   = os.getenv("TINYFISH_API_KEY", "your_api_key_here")
TINYFISH_SEARCH    = "https://api.search.tinyfish.ai"
TINYFISH_FETCH     = "https://api.fetch.tinyfish.ai"   # Rendered HTML fetch
OUTPUT_CSV         = "nutrabay_amazon_products.csv"
DELAY              = 2  # polite delay between requests

SEARCH_QUERIES = [
    "Nutrabay whey protein amazon.in",
    "Nutrabay protein powder amazon india",
    "Nutrabay supplement amazon.in",
    "Nutrabay creatine amazon india",
    "Nutrabay BCAA amazon.in",
    "Nutrabay pre-workout amazon india",
    "Nutrabay mass gainer amazon.in",
    "Nutrabay multivitamin amazon india",
    "Nutrabay omega amazon.in",
    "Nutrabay collagen amazon india",
]

AUTH_HEADER = {"X-API-Key": TINYFISH_API_KEY}

# ─────────────────────────────────────────────
# SEARCH PHASE
# ─────────────────────────────────────────────

def search(query: str, page: int = 0) -> list[str]:
    """Return Amazon.in product URLs from TinyFish Search API."""
    params = {"query": query, "page": page, "location": "IN", "language": "en"}
    try:
        r = requests.get(TINYFISH_SEARCH, headers=AUTH_HEADER, params=params, timeout=15)
        r.raise_for_status()
        urls = []
        for item in r.json().get("results", []):
            url = item.get("url", "")
            if "amazon.in" in url and "/dp/" in url:
                urls.append(url.split("?")[0])
        return list(dict.fromkeys(urls))   # deduplicate preserving order
    except Exception as e:
        print(f"  [Search Error] {e}")
        return []


# ─────────────────────────────────────────────
# FETCH PHASE  (TinyFish Fetch — real browser)
# ─────────────────────────────────────────────

def fetch_with_tinyfish(url: str) -> str | None:
    """
    Use TinyFish Fetch API to get fully-rendered HTML of a page.
    Falls back to plain requests if Fetch API fails.
    """
    payload = {
        "url": url,
        "render_js": True,        # Execute JavaScript
        "wait_for": "#productTitle",  # Wait until product title is in DOM
    }
    try:
        r = requests.post(TINYFISH_FETCH, headers=AUTH_HEADER, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("html") or data.get("content") or r.text
        # Fallback to plain requests
        return _plain_fetch(url)
    except Exception:
        return _plain_fetch(url)


def _plain_fetch(url: str) -> str | None:
    """Plain requests fallback."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


# ─────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────

def _t(soup: BeautifulSoup, selector: str, attr: str = None) -> str:
    """Safe selector → text or attribute."""
    el = soup.select_one(selector)
    if not el:
        return ""
    return (el.get(attr, "") or "").strip() if attr else el.get_text(strip=True)


def extract_asin(url: str) -> str:
    m = re.search(r"/dp/([A-Z0-9]{10})", url)
    return m.group(1) if m else ""


def parse(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    d = {}

    # ── Identifiers
    d["asin"]  = extract_asin(url)
    d["url"]   = url

    # ── Title & Brand
    d["title"] = _t(soup, "#productTitle")
    d["brand"] = _t(soup, "#bylineInfo")

    # ── Pricing
    d["price"]            = (_t(soup, "span.a-price span.a-offscreen")
                              or _t(soup, "#priceblock_ourprice")
                              or _t(soup, "#priceblock_dealprice"))
    d["mrp"]              = _t(soup, "span.a-price.a-text-price span.a-offscreen")
    d["discount_percent"] = _t(soup, "span.savingsPercentage") or _t(soup, "#savingsPercentage")

    # ── Ratings
    d["rating"]      = _t(soup, "#acrPopover", attr="title") or _t(soup, "span.a-icon-alt")
    d["num_ratings"] = _t(soup, "#acrCustomerReviewText")
    d["num_reviews"] = _t(soup, "#askATFLink span")

    # Star breakdown
    for i, star in enumerate([5, 4, 3, 2, 1], 1):
        sel = f"#histogramTable .a-histogram-row:nth-child({i}) .a-size-base"
        d[f"star_{star}"] = _t(soup, sel)

    # ── Availability
    d["availability"] = _t(soup, "#availability span")

    # ── Seller Info
    d["sold_by"]       = _t(soup, "#sellerProfileTriggerId") or _t(soup, "#merchant-info a")
    d["fulfilled_by"]  = _t(soup, "#fulfillerInfoFeature_feature_div .a-size-small")
    d["merchant_info"] = _t(soup, "#merchant-info")

    # ── Promotions
    d["coupon"]      = _t(soup, "#promotions_feature_div")
    d["deal_badge"]  = _t(soup, "#dealBadgeSupportingText")

    # ── Image
    img = soup.select_one("#imgTagWrapperId img") or soup.select_one("#landingImage")
    d["main_image_url"] = (img.get("src") or img.get("data-old-hires", "")) if img else ""

    # ── Bullet Points
    bullets = [b.get_text(strip=True) for b in soup.select("#feature-bullets li span.a-list-item")]
    d["about_item"] = " | ".join(bullets[:8])

    # ── Technical Specs
    specs = {}
    for row in soup.select("#prodDetails tr"):
        th, td = row.select_one("th"), row.select_one("td")
        if th and td:
            specs[th.get_text(strip=True)] = td.get_text(strip=True)
    for li in soup.select("#detailBulletsWrapper_feature_div li"):
        text = li.get_text(" ", strip=True)
        if ":" in text:
            k, v = text.split(":", 1)
            specs[k.strip()] = v.strip()

    d["weight"]              = specs.get("Item Weight", specs.get("Weight", ""))
    d["flavour"]             = specs.get("Flavour", specs.get("Flavor", ""))
    d["servings"]            = specs.get("Number of Servings", specs.get("Servings", ""))
    d["protein_per_serving"] = specs.get("Protein", "")
    d["item_form"]           = specs.get("Item Form", "")
    d["age_range"]           = specs.get("Age Range Description", "")
    d["diet_type"]           = specs.get("Diet Type", "")
    d["allergen_info"]       = specs.get("Allergen Information", "")
    d["country_of_origin"]   = specs.get("Country of Origin", "")
    d["manufacturer"]        = specs.get("Manufacturer", "")
    d["date_first_available"]= specs.get("Date First Available", "")
    d["best_seller_rank"]    = specs.get("Best Sellers Rank", "")
    d["all_specs_json"]      = json.dumps(specs, ensure_ascii=False)

    # ── Delivery & Category
    d["delivery_info"]        = _t(soup, "#mir-layout-DELIVERY_BLOCK")
    d["qa_count"]             = _t(soup, "#askATFLink")
    crumbs = [a.get_text(strip=True) for a in soup.select("#wayfinding-breadcrumbs_feature_div a")]
    d["category_breadcrumb"]  = " > ".join(crumbs)

    d["scraped_at"] = datetime.now().isoformat()
    return d


# ─────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────

FIELDS = [
    "asin","title","brand","price","mrp","discount_percent",
    "rating","num_ratings","num_reviews",
    "star_5","star_4","star_3","star_2","star_1",
    "availability","sold_by","fulfilled_by","merchant_info",
    "coupon","deal_badge",
    "weight","flavour","servings","protein_per_serving",
    "item_form","age_range","diet_type","allergen_info",
    "country_of_origin","manufacturer","date_first_available",
    "best_seller_rank","category_breadcrumb",
    "delivery_info","qa_count","about_item","main_image_url",
    "all_specs_json","url","scraped_at",
]

def save_csv(products: list[dict], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(products)
    print(f"\n✅ Saved {len(products)} rows → '{path}'")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 62)
    print("  Nutrabay Amazon Scraper  [TinyFish Search + Fetch]")
    print("=" * 62)

    if TINYFISH_API_KEY == "your_api_key_here":
        print("\n⚠️  Set your key:  export TINYFISH_API_KEY='sk-...'")
        return

    # ── 1. Collect URLs ───────────────────────────────────────────────
    all_urls: list[str] = []
    print("\n📡 Step 1 — Collecting Amazon.in URLs via Search API...")
    for q in SEARCH_QUERIES:
        print(f"  🔍 {q}")
        for page in range(2):
            urls = search(q, page)
            new  = [u for u in urls if u not in all_urls]
            all_urls.extend(new)
            print(f"      page {page} → {len(new)} new URLs")
            time.sleep(0.5)

    print(f"\n  Total unique URLs: {len(all_urls)}")

    # ── 2. Scrape each page ───────────────────────────────────────────
    products: list[dict] = []
    seen_asins: set[str] = set()
    print("\n🕷️  Step 2 — Scraping product pages...")

    for i, url in enumerate(all_urls, 1):
        asin = extract_asin(url)
        if asin in seen_asins:
            print(f"  [{i}/{len(all_urls)}] ⏭  Duplicate ASIN {asin}")
            continue

        print(f"  [{i}/{len(all_urls)}] {url}")
        html = fetch_with_tinyfish(url)

        if not html:
            print("    ⚠️  Empty response")
            continue

        details = parse(html, url)

        # Verify it's a Nutrabay product
        combo = (details.get("title","") + details.get("brand","")).lower()
        if "nutrabay" not in combo:
            print(f"    ⏭  Not Nutrabay: {details.get('title','?')[:55]}")
            continue

        seen_asins.add(asin)
        products.append(details)
        print(
            f"    ✅ {details['title'][:50]}... "
            f"| ₹{details['price']} | ⭐{details['rating']} "
            f"| 💬{details['num_ratings']}"
        )
        time.sleep(DELAY)

    # ── 3. Save ───────────────────────────────────────────────────────
    if products:
        save_csv(products, OUTPUT_CSV)
    else:
        print("\n⚠️  No products scraped. Try checking API key or queries.")

    print(f"\n{'='*62}")
    print(f"  Done! {len(products)} Nutrabay products saved to {OUTPUT_CSV}")
    print(f"{'='*62}")


if __name__ == "__main__":
    main()