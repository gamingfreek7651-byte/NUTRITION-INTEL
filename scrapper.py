"""
Nutrabay Amazon Product Scraper using TinyFish Search API
Fetches product details: title, price, rating, reviews, seller, ASIN, etc.
Saves results to a CSV file.

Requirements:
    pip install requests beautifulsoup4 lxml

Usage:
    export TINYFISH_API_KEY="your_api_key_here"
    python nutrabay_amazon_scraper.py
"""

import os
import sys
import argparse

# Ensure UTF-8 output encoding for terminal printing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import csv
import time
import json
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

# Load environment variables from .env file if it exists
def load_dotenv():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        v = v.split("#", 1)[0].strip()
                        if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                            v = v[1:-1]
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "your_api_key_here")
TINYFISH_SEARCH_URL = "https://api.search.tinyfish.ai"
TINYFISH_FETCH_URL = "https://api.fetch.tinyfish.ai"

HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

DELAY_BETWEEN_REQUESTS = 2  # seconds (be polite to Amazon)

# Brand configurations for search & validation
BRANDS_CONFIG = {
    "muscleblaze": {
        "search_name": "MuscleBlaze",
        "verify_terms": ["muscleblaze", "mb"],
        "csv_filename": "muscleblaze_amazon_products.csv",
    },
    "avvatar": {
        "search_name": "Avvatar",
        "verify_terms": ["avvatar"],
        "csv_filename": "avvatar_amazon_products.csv",
    },
    "optimum_nutrition": {
        "search_name": "Optimum Nutrition",
        "verify_terms": ["optimum nutrition", "optimum", "on"],
        "csv_filename": "optimum_nutrition_amazon_products.csv",
    },
    "nakpro": {
        "search_name": "Nakpro",
        "verify_terms": ["nakpro"],
        "csv_filename": "nakpro_amazon_products.csv",
    },
    "as-it-is": {
        "search_name": "AS-IT-IS",
        "verify_terms": ["as-it-is", "as it is", "asitis"],
        "csv_filename": "as-it-is_amazon_products.csv",
    }
}

# Generic query templates to cover each brand's product range on Amazon India
QUERY_TEMPLATES = [
    "{brand} protein site:amazon.in",
    "{brand} whey protein amazon.in",
    "{brand} protein powder amazon india",
    "{brand} supplement site:amazon.in",
    "{brand} supplement amazon.in",
    "{brand} creatine site:amazon.in",
    "{brand} creatine amazon india",
    "{brand} multivitamin site:amazon.in",
    "{brand} multivitamin amazon india",
    "{brand} pre workout site:amazon.in",
    "{brand} pre-workout amazon india",
    "{brand} BCAA site:amazon.in",
    "{brand} BCAA amazon.in",
    "{brand} mass gainer site:amazon.in",
    "{brand} mass gainer amazon.in",
    "{brand} omega amazon.in",
    "{brand} collagen amazon india",
    "{brand} fish oil site:amazon.in",
    "{brand} peanut butter site:amazon.in",
    "{brand} shilajit site:amazon.in",
    "{brand} ashwagandha site:amazon.in",
    "{brand} apple cider vinegar site:amazon.in",
    "{brand} glutamine site:amazon.in",
    "{brand} gainer site:amazon.in",
    "{brand} CLA site:amazon.in",
    "{brand} L-Carnitine site:amazon.in",
    "{brand} wellness site:amazon.in",
]

# ─────────────────────────────────────────────
# STEP 1: TinyFish Search API
# ─────────────────────────────────────────────

def check_connection_error(e: Exception, context: str):
    """Inspect exception for DNS/network resolution failure and print user friendly warnings."""
    err_str = str(e)
    if "getaddrinfo failed" in err_str or "Name or service not known" in err_str or "failed to resolve" in err_str.lower():
        print(f"  ❌ [{context} DNS Error] Failed to resolve host name. Please check your internet connection/DNS.")
    else:
        print(f"  [{context} Error] {e}")


def search_tinyfish(query: str, page: int = 0) -> list[dict]:
    """
    Call TinyFish Search API and return list of result dicts.
    Each dict has: position, site_name, title, snippet, url
    """
    headers = {"X-API-Key": TINYFISH_API_KEY}
    params = {
        "query": query,
        "page": page,
        "location": "IN",
        "language": "en",
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(TINYFISH_SEARCH_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except Exception as e:
            check_connection_error(e, f"Search Attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 3
                print(f"    Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return []
    return []


def extract_amazon_urls(results: list[dict]) -> list[str]:
    """Filter results to only Amazon.in product URLs."""
    amazon_urls = []
    for r in results:
        url = r.get("url", "")
        # Must be an Amazon.in product page (dp = detail page)
        if "amazon.in" in url and "/dp/" in url:
            # Normalise: strip query params
            clean_url = url.split("?")[0].split("&")[0]
            if clean_url not in amazon_urls:
                amazon_urls.append(clean_url)
    return amazon_urls


# ─────────────────────────────────────────────
# STEP 2: Amazon Page Scraper
# ─────────────────────────────────────────────

def fetch_amazon_page(url: str) -> BeautifulSoup | None:
    """
    Download an Amazon product page and return a BeautifulSoup object.
    Uses TinyFish Fetch API (real browser with JS execution) first,
    and falls back to direct requests if Fetch API fails.
    """
    html = None
    # 1. Attempt to fetch using TinyFish Fetch API
    payload = {
        "urls": [url],
        "format": "html"
    }
    headers = {"X-API-Key": TINYFISH_API_KEY}
    max_retries = 3

    # Try TinyFish Fetch first
    for attempt in range(max_retries):
        try:
            resp = requests.post(TINYFISH_FETCH_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results and isinstance(results, list):
                    html = results[0].get("text")
                if not html:
                    html = data.get("html") or data.get("content") or resp.text
                if html:
                    break
            elif resp.status_code in [400, 401, 403, 404]:
                print(f"  [TinyFish Fetch HTTP {resp.status_code}] Client error. Skipping retries.")
                break
            else:
                print(f"  [TinyFish Fetch HTTP {resp.status_code}] Attempt {attempt + 1}/{max_retries}")
        except Exception as e:
            check_connection_error(e, f"TinyFish Fetch Attempt {attempt + 1}/{max_retries}")
        
        if not html and attempt < max_retries - 1:
            sleep_time = (attempt + 1) * 3
            print(f"    Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

    # 2. Fallback to direct HTTP requests
    if not html:
        print("  ⚠️ TinyFish Fetch failed or was blocked. Falling back to direct HTTP requests...")
        # Direct requests get blocked quickly, so only try up to 2 times
        for attempt in range(2):
            try:
                resp = requests.get(url, headers=HEADERS_HTTP, timeout=15)
                if resp.status_code == 200:
                    html = resp.text
                    break
                elif resp.status_code in [403, 404]:
                    print(f"  [HTTP {resp.status_code}] Client error/blocked. Skipping retries.")
                    break
                else:
                    print(f"  [HTTP {resp.status_code}] Attempt {attempt + 1}/2 for {url}")
            except Exception as e:
                check_connection_error(e, f"Direct Fetch Attempt {attempt + 1}/2")
            
            if not html and attempt < 1:
                time.sleep(2)

    # 3. Parse HTML using BeautifulSoup (lxml with html.parser fallback)
    if html:
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            return BeautifulSoup(html, "html.parser")
    return None


def safe_text(soup: BeautifulSoup, selector: str, attr: str = None) -> str:
    """Helper: find element by CSS selector, return text or attribute."""
    el = soup.select_one(selector)
    if el is None:
        return ""
    if attr:
        return el.get(attr, "").strip()
    return el.get_text(strip=True)


def extract_asin(url: str) -> str:
    """Extract ASIN from Amazon URL."""
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else ""


def parse_product_details(soup: BeautifulSoup, url: str) -> dict:
    """
    Parse all relevant product details from an Amazon India product page.
    Returns a dict with all scraped fields.
    """
    data = {}

    # ── Basic identifiers ──────────────────────────────────────────────
    data["asin"] = extract_asin(url)
    data["url"] = url

    # ── Product Title ──────────────────────────────────────────────────
    data["title"] = safe_text(soup, "#productTitle")

    # ── Brand ──────────────────────────────────────────────────────────
    data["brand"] = safe_text(soup, "#bylineInfo") or safe_text(soup, "a#bylineInfo")

    # ── Price ──────────────────────────────────────────────────────────
    # Current price (may appear in different locations)
    price = (
        safe_text(soup, "span.a-price > span.a-offscreen")
        or safe_text(soup, "#priceblock_ourprice")
        or safe_text(soup, "#priceblock_dealprice")
        or safe_text(soup, ".a-price .a-price-whole")
    )
    data["price"] = price

    # MRP / List price (before discount)
    mrp = safe_text(soup, "span.a-price.a-text-price > span.a-offscreen")
    data["mrp"] = mrp

    # Discount percentage
    discount = safe_text(soup, "span.savingsPercentage") or safe_text(soup, "#savingsPercentage")
    data["discount_percent"] = discount

    # ── Rating & Reviews ───────────────────────────────────────────────
    data["rating"] = safe_text(soup, "#acrPopover", attr="title") or safe_text(
        soup, "span.a-icon-alt"
    )
    data["num_ratings"] = safe_text(soup, "#acrCustomerReviewText")
    data["num_reviews"] = safe_text(soup, "#askATFLink span")

    # Star breakdown
    for star in [5, 4, 3, 2, 1]:
        selector = f"#histogramTable .a-histogram-row:nth-child({6 - star}) .a-size-base"
        data[f"star_{star}"] = safe_text(soup, selector)

    # ── Availability / Stock ───────────────────────────────────────────
    data["availability"] = safe_text(soup, "#availability span") or safe_text(
        soup, "#outOfStock .a-color-price"
    )

    # ── Seller / Fulfilled By ──────────────────────────────────────────
    data["sold_by"] = safe_text(soup, "#sellerProfileTriggerId") or safe_text(
        soup, "#merchant-info a"
    )
    data["fulfilled_by"] = safe_text(soup, "#fulfillerInfoFeature_feature_div .a-size-small")
    merchant_info = safe_text(soup, "#merchant-info")
    data["merchant_info"] = merchant_info

    # ── Coupon / Deal ──────────────────────────────────────────────────
    data["coupon"] = safe_text(soup, "#promotions_feature_div")
    data["deal_badge"] = safe_text(soup, "#dealBadgeSupportingText")

    # ── Product Images (first image URL) ──────────────────────────────
    img_tag = soup.select_one("#imgTagWrapperId img") or soup.select_one("#landingImage")
    if img_tag:
        data["main_image_url"] = img_tag.get("src") or img_tag.get("data-old-hires", "")
    else:
        data["main_image_url"] = ""

    # ── About This Item (bullet points) ───────────────────────────────
    bullets = soup.select("#feature-bullets li span.a-list-item")
    data["about_item"] = " | ".join(b.get_text(strip=True) for b in bullets[:6])

    # ── Technical Specifications / Product Details table ──────────────
    specs = {}
    # Method 1: prodDetails table
    for row in soup.select("#prodDetails tr"):
        th = row.select_one("th")
        td = row.select_one("td")
        if th and td:
            key = th.get_text(strip=True)
            val = td.get_text(strip=True)
            specs[key] = val

    # Method 2: detailBullets
    for li in soup.select("#detailBulletsWrapper_feature_div li"):
        text = li.get_text(" ", strip=True)
        if ":" in text:
            k, v = text.split(":", 1)
            specs[k.strip()] = v.strip()

    # Extract common spec fields
    data["weight"] = specs.get("Item Weight", specs.get("Weight", ""))
    data["flavour"] = specs.get("Flavour", specs.get("Flavor", ""))
    data["servings"] = specs.get("Number of Servings", specs.get("Servings", ""))
    data["protein_per_serving"] = specs.get("Protein", "")
    data["item_form"] = specs.get("Item Form", "")
    data["age_range"] = specs.get("Age Range Description", specs.get("Age Range", ""))
    data["diet_type"] = specs.get("Diet Type", "")
    data["allergen_info"] = specs.get("Allergen Information", "")
    data["country_of_origin"] = specs.get("Country of Origin", "")
    data["manufacturer"] = specs.get("Manufacturer", "")
    data["date_first_available"] = specs.get("Date First Available", "")
    data["best_seller_rank"] = specs.get("Best Sellers Rank", "")
    data["asin_spec"] = specs.get("ASIN", "")

    # Full specs as JSON string for completeness
    data["all_specs_json"] = json.dumps(specs, ensure_ascii=False)

    # ── Delivery Info ──────────────────────────────────────────────────
    data["delivery_info"] = safe_text(soup, "#mir-layout-DELIVERY_BLOCK")

    # ── Q&A Count ─────────────────────────────────────────────────────
    data["qa_count"] = safe_text(soup, "#askATFLink")

    # ── Category / Breadcrumb ──────────────────────────────────────────
    crumbs = [a.get_text(strip=True) for a in soup.select("#wayfinding-breadcrumbs_feature_div a")]
    data["category_breadcrumb"] = " > ".join(crumbs)

    # ── Scrape Metadata ───────────────────────────────────────────────
    data["scraped_at"] = datetime.now().isoformat()

    return data


def verify_brand(details: dict, brand_key: str) -> bool:
    """Validate that the scraped product matches the target brand."""
    title_lower = details.get("title", "").lower()
    brand_lower = details.get("brand", "").lower()
    
    config = BRANDS_CONFIG.get(brand_key)
    if not config:
        return False
        
    for term in config["verify_terms"]:
        if term == "on":
            # Match "ON" as a separate word to avoid generic substring matches
            if re.search(r'\bon\b', title_lower) or re.search(r'\bon\b', brand_lower):
                return True
        elif term in title_lower or term in brand_lower:
            return True
            
    return False


# ─────────────────────────────────────────────
# STEP 3: CSV Writer
# ─────────────────────────────────────────────

CSV_FIELDS = [
    "asin", "title", "brand", "price", "mrp", "discount_percent",
    "rating", "num_ratings", "num_reviews",
    "star_5", "star_4", "star_3", "star_2", "star_1",
    "availability", "sold_by", "fulfilled_by", "merchant_info",
    "coupon", "deal_badge",
    "weight", "flavour", "servings", "protein_per_serving",
    "item_form", "age_range", "diet_type", "allergen_info",
    "country_of_origin", "manufacturer", "date_first_available",
    "best_seller_rank", "category_breadcrumb",
    "delivery_info", "qa_count",
    "about_item", "main_image_url",
    "all_specs_json", "url", "scraped_at",
]


def save_to_csv(products: list[dict], filepath: str):
    """Write product list to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            writer.writerow(p)
    print(f"\n✅ Saved {len(products)} products to '{filepath}'")


# ─────────────────────────────────────────────
# STEP 4: Main Orchestrator
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-Brand Amazon Product Scraper using TinyFish API")
    parser.add_argument(
        "--brand", 
        choices=list(BRANDS_CONFIG.keys()) + ["all"], 
        default="all", 
        help="Select a specific brand to scrape or 'all' to scrape all brands sequentially (default: all)"
    )
    # Add direct flags as convenience options (e.g. --nakpro, --as-it-is, etc.)
    for brand_key in BRANDS_CONFIG.keys():
        parser.add_argument(f"--{brand_key}", action="store_true", help=f"Scrape {brand_key} brand directly")

    args = parser.parse_args()

    # Resolve which brand to process based on direct flags or the --brand argument
    selected_brand = args.brand
    for brand_key in BRANDS_CONFIG.keys():
        # argparse converts hyphens in flag names to underscores for variable names
        if getattr(args, brand_key.replace("-", "_"), False):
            selected_brand = brand_key
            break

    print("=" * 60)
    print("  Amazon Multi-Brand Scraper — TinyFish Search & Fetch API")
    print("=" * 60)

    if TINYFISH_API_KEY == "your_api_key_here":
        print("\n⚠️  Set your API key:  export TINYFISH_API_KEY='sk-...'")
        return

    # Determine which brands to process
    if selected_brand == "all":
        brands_to_process = list(BRANDS_CONFIG.keys())
    else:
        brands_to_process = [selected_brand]

    for brand_key in brands_to_process:
        brand_config = BRANDS_CONFIG[brand_key]
        search_name = brand_config["search_name"]
        csv_filename = brand_config["csv_filename"]

        print("\n" + "=" * 60)
        print(f"  Starting scraping process for brand: {search_name}")
        print("=" * 60)

        # ── Phase 1: Collect Amazon product URLs via Search API ───────────
        print(f"\n📡 Phase 1: Searching for {search_name} products on Amazon.in...")
        all_urls = []
        for template in QUERY_TEMPLATES:
            query = template.format(brand=search_name)
            print(f"  🔍 Query: {query}")
            for page in range(3):  # Fetch up to 3 pages per query dynamically (saves time/credits)
                results = search_tinyfish(query, page=page)
                if not results:
                    break
                urls = extract_amazon_urls(results)
                new_urls = [u for u in urls if u not in all_urls]
                all_urls.extend(new_urls)
                print(f"      Page {page}: {len(results)} results → {len(new_urls)} new Amazon URLs")
                time.sleep(0.5)

        print(f"\n  📦 Total unique Amazon product URLs found for {search_name}: {len(all_urls)}")

        if not all_urls:
            print(f"\n❌ No Amazon URLs found for {search_name}. Skipping to next brand.")
            continue

        # ── Phase 2: Scrape each Amazon product page ─────────────────────
        print(f"\n🕷️  Phase 2: Scraping product details for {search_name} from Amazon.in...")
        products = []
        seen_asins = set()

        for i, url in enumerate(all_urls, 1):
            asin = extract_asin(url)
            if asin in seen_asins:
                print(f"  [{i}/{len(all_urls)}] ⏭️  Duplicate ASIN {asin}, skipping")
                continue

            print(f"  [{i}/{len(all_urls)}] Fetching: {url}")
            soup = fetch_amazon_page(url)

            if soup is None:
                print(f"    ⚠️  Could not fetch page")
                continue

            details = parse_product_details(soup, url)

            # Sanity check: verify brand name matches
            if not verify_brand(details, brand_key):
                print(f"    ⚠️  Skipping — not a {search_name} product: {details.get('title', 'N/A')[:60]}")
                continue

            seen_asins.add(asin)
            products.append(details)
            print(f"    ✅ {details.get('title', 'N/A')[:55]}... | ₹{details.get('price', 'N/A')} | ⭐{details.get('rating', 'N/A')}")

            time.sleep(DELAY_BETWEEN_REQUESTS)

        # ── Phase 3: Save to CSV ──────────────────────────────────────────
        print(f"\n💾 Phase 3: Saving {len(products)} products to CSV...")
        if products:
            save_to_csv(products, csv_filename)
        else:
            print(f"⚠️  No {search_name} products were scraped.")

        # ── Summary ───────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print(f"  DONE! Scraped {len(products)} {search_name} products.")
        print(f"  Output file : {csv_filename}")
        print("=" * 60)


if __name__ == "__main__":
    main()