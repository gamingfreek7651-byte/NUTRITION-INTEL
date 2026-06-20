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
import random
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ─────────────────────────────────────────────
# LOAD .env
# ─────────────────────────────────────────────
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
TINYFISH_API_KEY    = os.getenv("TINYFISH_API_KEY", "your_api_key_here")
TINYFISH_SEARCH_URL = "https://api.search.tinyfish.ai"
TINYFISH_FETCH_URL  = "https://api.fetch.tinyfish.ai"

HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ── Concurrency: number of product pages fetched in parallel ──────────
# Raise to 10 if your TinyFish plan allows higher QPS; lower to 3 if throttled.
MAX_WORKERS = 6

# ── Delays ────────────────────────────────────────────────────────────
SEARCH_DELAY   = 0.3   # seconds between search calls (was 0.5)
FETCH_TIMEOUT  = 20    # seconds per TinyFish Fetch call (was 30)
DIRECT_TIMEOUT = 12    # seconds for fallback direct HTTP

# ── How many search pages to fetch per query (1 page ≈ 10 results) ───
# Reducing from 3 → 2 saves ~33% API calls. Bump back if you need more coverage.
SEARCH_PAGES_PER_QUERY = 2

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
        "verify_terms": ["optimum nutrition", "optimum", "on "],
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
    },
}

# Leaner query set — remove low-yield generic templates to cut API calls
QUERY_TEMPLATES = [
    "{brand} protein site:amazon.in",
    "{brand} whey protein amazon.in",
    "{brand} protein powder amazon india",
    "{brand} supplement site:amazon.in",
    "{brand} creatine site:amazon.in",
    "{brand} multivitamin site:amazon.in",
    "{brand} pre workout site:amazon.in",
    "{brand} BCAA site:amazon.in",
    "{brand} mass gainer site:amazon.in",
    "{brand} omega amazon.in",
    "{brand} fish oil site:amazon.in",
    "{brand} peanut butter site:amazon.in",
    "{brand} glutamine site:amazon.in",
    "{brand} L-Carnitine site:amazon.in",
    "{brand} ashwagandha site:amazon.in",
    "{brand} wellness site:amazon.in",
    "{brand} collagen amazon india",
    "{brand} gainer site:amazon.in",
    "{brand} CLA site:amazon.in",
    "{brand} shilajit site:amazon.in",
    "{brand} apple cider vinegar site:amazon.in",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def check_connection_error(e: Exception, context: str):
    err_str = str(e)
    if any(kw in err_str for kw in ("getaddrinfo failed", "Name or service not known", "failed to resolve")):
        print(f"  ❌ [{context}] DNS/network error — check your internet connection.")
    else:
        print(f"  ⚠️  [{context}] {e}")


def extract_asin(url: str) -> str:
    """Extract ASIN from any Amazon URL format."""
    # Handles /dp/ASIN, /gp/product/ASIN, /exec/obidos/ASIN, etc.
    match = re.search(r"(?:/dp/|/gp/product/|/exec/obidos/(?:ASIN/)?|/o/ASIN/)([A-Z0-9]{10})", url, re.IGNORECASE)
    return match.group(1).upper() if match else ""


# ─────────────────────────────────────────────
# STEP 1: TinyFish Search  (batched & deduplicated)
# ─────────────────────────────────────────────

def search_tinyfish(query: str, page: int = 0) -> list[dict]:
    headers = {"X-API-Key": TINYFISH_API_KEY}
    params  = {"query": query, "page": page, "location": "IN", "language": "en"}
    for attempt in range(3):
        try:
            resp = requests.get(TINYFISH_SEARCH_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            check_connection_error(e, f"Search q='{query}' p={page} attempt {attempt+1}/3")
            if attempt < 2:
                time.sleep((attempt + 1) * 2)
    return []


def extract_amazon_urls(results: list[dict]) -> list[str]:
    """
    Extract valid Amazon.in product URLs.
    Accepts both /dp/ and /gp/product/ paths, and is case-insensitive.
    """
    seen, urls = set(), []
    for r in results:
        url = r.get("url", "")
        if "amazon.in" not in url:
            continue
        # Accept /dp/ or /gp/product/ pages
        if not re.search(r"/dp/|/gp/product/", url, re.IGNORECASE):
            continue
        asin = extract_asin(url)
        if not asin or asin in seen:
            continue
        seen.add(asin)
        # Normalise to canonical /dp/ URL, strip query params
        clean = f"https://www.amazon.in/dp/{asin}"
        urls.append(clean)
    return urls


def collect_all_urls(search_name: str) -> list[str]:
    """Run all queries and return a deduplicated list of Amazon product URLs."""
    all_asins: set[str] = set()
    all_urls:  list[str] = []

    for template in QUERY_TEMPLATES:
        query = template.format(brand=search_name)
        print(f"  🔍 {query}")
        for page in range(SEARCH_PAGES_PER_QUERY):
            results = search_tinyfish(query, page=page)
            if not results:
                break
            urls = extract_amazon_urls(results)
            new = []
            for u in urls:
                asin = extract_asin(u)
                if asin and asin not in all_asins:
                    all_asins.add(asin)
                    all_urls.append(u)
                    new.append(u)
            print(f"      page {page}: {len(results)} results → {len(new)} new URLs (total {len(all_urls)})")
            time.sleep(SEARCH_DELAY)

    return all_urls


# ─────────────────────────────────────────────
# STEP 2: Amazon Page Fetcher  (parallel)
# ─────────────────────────────────────────────

def fetch_amazon_page(url: str) -> "BeautifulSoup | None":
    """
    Fetch page via TinyFish Fetch API (JS rendering), falling back to direct HTTP.
    Uses productTitle content validation to ensure the response isn't a robot check or stripped page.
    """
    html = None
    headers = {"X-API-Key": TINYFISH_API_KEY}
    payload = {"urls": [url], "format": "html"}

    # TinyFish Fetch — max 2 attempts
    for attempt in range(2):
        try:
            resp = requests.post(TINYFISH_FETCH_URL, headers=headers, json=payload, timeout=FETCH_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results and isinstance(results, list):
                    html = results[0].get("text") or results[0].get("html")
                if not html:
                    html = data.get("html") or data.get("content")
                
                # Check if this is a valid product page containing the title
                if html and "productTitle" in html:
                    break
                else:
                    html = None
            elif resp.status_code in (400, 401, 403, 404):
                break  # don't retry client errors
            else:
                print(f"    [TF Fetch HTTP {resp.status_code}] attempt {attempt+1}/2 — {url}")
        except Exception as e:
            check_connection_error(e, f"TF Fetch attempt {attempt+1}/2")
        if not html and attempt == 0:
            time.sleep(2)

    # Direct HTTP fallback — 2 attempts with agent rotation
    if not html:
        for attempt in range(2):
            try:
                headers_direct = HEADERS_HTTP.copy()
                headers_direct["User-Agent"] = random.choice(USER_AGENTS)
                resp = requests.get(url, headers=headers_direct, timeout=DIRECT_TIMEOUT)
                if resp.status_code == 200:
                    html_temp = resp.text
                    if html_temp and "productTitle" in html_temp:
                        html = html_temp
                        break
                elif resp.status_code in (403, 503):
                    pass  # blocked, try next attempt
            except Exception as e:
                check_connection_error(e, f"Direct HTTP attempt {attempt+1}/2")
            if not html and attempt == 0:
                time.sleep(2)

    if html:
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            return BeautifulSoup(html, "html.parser")
    return None


# ─────────────────────────────────────────────
# STEP 3: Product Detail Parser
# ─────────────────────────────────────────────

def safe_text(soup: BeautifulSoup, selector: str, attr: str = None) -> str:
    el = soup.select_one(selector)
    if el is None:
        return ""
    if attr:
        return el.get(attr, "").strip()
    return el.get_text(strip=True)


def parse_product_details(soup: BeautifulSoup, url: str) -> dict:
    data = {}
    data["asin"] = extract_asin(url)
    data["url"]  = url

    # ── Title ─────────────────────────────────────────────────────────
    data["title"] = safe_text(soup, "#productTitle")

    # ── Brand ─────────────────────────────────────────────────────────
    # Try multiple selectors — Amazon restructures its DOM frequently
    data["brand"] = (
        safe_text(soup, "#bylineInfo")
        or safe_text(soup, "a#bylineInfo")
        or safe_text(soup, ".po-brand .po-break-word")
        or safe_text(soup, "tr.po-brand td.a-span9 span")
    )

    # ── Price ─────────────────────────────────────────────────────────
    price = (
        safe_text(soup, "span.a-price > span.a-offscreen")
        or safe_text(soup, "#priceblock_ourprice")
        or safe_text(soup, "#priceblock_dealprice")
        or safe_text(soup, ".priceToPay span.a-offscreen")
        or safe_text(soup, "#corePrice_desktop .a-offscreen")
        or safe_text(soup, "#apex_offerDisplay_desktop .a-offscreen")
    )
    data["price"] = price

    mrp = (
        safe_text(soup, "span.a-price.a-text-price > span.a-offscreen")
        or safe_text(soup, "#listPrice")
        or safe_text(soup, ".basisPrice span.a-offscreen")
    )
    data["mrp"] = mrp

    data["discount_percent"] = (
        safe_text(soup, "span.savingsPercentage")
        or safe_text(soup, "#savingsPercentage")
        or safe_text(soup, ".savingsPercentage")
    )

    # ── Ratings ───────────────────────────────────────────────────────
    data["rating"]      = safe_text(soup, "#acrPopover", attr="title") or safe_text(soup, "span.a-icon-alt")
    data["num_ratings"] = safe_text(soup, "#acrCustomerReviewText")
    data["num_reviews"] = safe_text(soup, "#askATFLink span")

    for star in [5, 4, 3, 2, 1]:
        selector = f"#histogramTable .a-histogram-row:nth-child({6 - star}) .a-size-base"
        data[f"star_{star}"] = safe_text(soup, selector)

    # ── Availability ──────────────────────────────────────────────────
    data["availability"] = (
        safe_text(soup, "#availability span")
        or safe_text(soup, "#outOfStock .a-color-price")
        or safe_text(soup, "#availability")
    )

    # ── Seller ────────────────────────────────────────────────────────
    data["sold_by"]       = safe_text(soup, "#sellerProfileTriggerId") or safe_text(soup, "#merchant-info a")
    data["fulfilled_by"]  = safe_text(soup, "#fulfillerInfoFeature_feature_div .a-size-small")
    data["merchant_info"] = safe_text(soup, "#merchant-info")

    # ── Coupon / Deal ─────────────────────────────────────────────────
    data["coupon"]     = safe_text(soup, "#promotions_feature_div")
    data["deal_badge"] = safe_text(soup, "#dealBadgeSupportingText")

    # ── Main Image ────────────────────────────────────────────────────
    img_tag = soup.select_one("#imgTagWrapperId img") or soup.select_one("#landingImage")
    if img_tag:
        data["main_image_url"] = (
            img_tag.get("data-old-hires")  # high-res version
            or img_tag.get("src", "")
        )
    else:
        data["main_image_url"] = ""

    # ── About This Item bullets ────────────────────────────────────────
    bullets = soup.select("#feature-bullets li span.a-list-item")
    if not bullets:
        bullets = soup.select("#featurebullets_feature_div li span.a-list-item")
    data["about_item"] = " | ".join(b.get_text(strip=True) for b in bullets[:6])

    # ── Specs / Product Details ────────────────────────────────────────
    specs: dict[str, str] = {}

    # Method 1: prodDetails tables (two-column th/td)
    for row in soup.select("#prodDetails tr"):
        th = row.select_one("th")
        td = row.select_one("td")
        if th and td:
            specs[th.get_text(strip=True)] = td.get_text(strip=True)

    # Method 2: detailBullets list
    for li in soup.select("#detailBulletsWrapper_feature_div li"):
        text = li.get_text(" ", strip=True)
        if ":" in text:
            k, v = text.split(":", 1)
            key = re.sub(r"[\u200e\u200f\xa0]", "", k).strip()
            val = re.sub(r"[\u200e\u200f\xa0]", "", v).strip()
            if key:
                specs[key] = val

    # Method 3: productOverview table (newer Amazon layout)
    for row in soup.select("#productOverview_feature_div tr"):
        tds = row.select("td")
        if len(tds) >= 2:
            key = tds[0].get_text(strip=True)
            val = tds[1].get_text(strip=True)
            if key and key not in specs:
                specs[key] = val

    data["weight"]             = specs.get("Item Weight", specs.get("Weight", ""))
    data["flavour"]            = specs.get("Flavour", specs.get("Flavor", specs.get("Flavour Name", "")))
    data["servings"]           = specs.get("Number of Servings", specs.get("Servings", ""))
    data["protein_per_serving"]= specs.get("Protein", specs.get("Protein Per Serving", ""))
    data["item_form"]          = specs.get("Item Form", "")
    data["age_range"]          = specs.get("Age Range Description", specs.get("Age Range", ""))
    data["diet_type"]          = specs.get("Diet Type", "")
    data["allergen_info"]      = specs.get("Allergen Information", "")
    data["country_of_origin"]  = specs.get("Country of Origin", "")
    data["manufacturer"]       = specs.get("Manufacturer", "")
    data["date_first_available"]= specs.get("Date First Available", "")
    data["best_seller_rank"]   = specs.get("Best Sellers Rank", "")
    data["asin_spec"]          = specs.get("ASIN", "")
    data["all_specs_json"]     = json.dumps(specs, ensure_ascii=False)

    # ── Delivery / Q&A / Breadcrumb ───────────────────────────────────
    data["delivery_info"] = safe_text(soup, "#mir-layout-DELIVERY_BLOCK")
    data["qa_count"]      = safe_text(soup, "#askATFLink")
    crumbs = [a.get_text(strip=True) for a in soup.select("#wayfinding-breadcrumbs_feature_div a")]
    data["category_breadcrumb"] = " > ".join(crumbs)

    data["scraped_at"] = datetime.now().isoformat()
    return data


def verify_brand(details: dict, brand_key: str) -> bool:
    """
    Verify that the scraped product belongs to the target brand.
    Uses a slightly looser match: checks title, brand field, and manufacturer.
    """
    config = BRANDS_CONFIG.get(brand_key)
    if not config:
        return False

    haystack = " ".join([
        details.get("title", ""),
        details.get("brand", ""),
        details.get("manufacturer", ""),
    ]).lower()

    for term in config["verify_terms"]:
        term_lower = term.lower()
        if term_lower == "on ":
            # Word-boundary match to avoid false positives (e.g. "action")
            if re.search(r'\bon\b', haystack):
                return True
        elif term_lower in haystack:
            return True

    return False


# ─────────────────────────────────────────────
# STEP 4: CSV Writer
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
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            writer.writerow(p)
    print(f"\n✅ Saved {len(products)} products → '{filepath}'")


# ─────────────────────────────────────────────
# STEP 5: Parallel Product Scraper
# ─────────────────────────────────────────────

def scrape_url(args_tuple):
    """Worker function for ThreadPoolExecutor."""
    idx, total, url, brand_key = args_tuple
    
    # Introduce random delay to space out concurrent requests to Amazon
    time.sleep(random.uniform(0.5, 3.0))
    
    asin = extract_asin(url)
    soup = fetch_amazon_page(url)
    if soup is None:
        return None, asin, idx, total, url, "fetch_failed"

    details = parse_product_details(soup, url)
    if not verify_brand(details, brand_key):
        return None, asin, idx, total, url, f"brand_mismatch:{details.get('title','')[:50]}"

    return details, asin, idx, total, url, "ok"


def scrape_products_parallel(urls: list[str], brand_key: str) -> list[dict]:
    """Scrape all URLs in parallel using a thread pool."""
    products:    list[dict] = []
    seen_asins:  set[str]   = set()
    print_lock = Lock()
    total = len(urls)

    tasks = [
        (i + 1, total, url, brand_key)
        for i, url in enumerate(urls)
    ]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_url, t): t for t in tasks}
        for future in as_completed(futures):
            details, asin, idx, total, url, status = future.result()
            with print_lock:
                if status == "fetch_failed":
                    print(f"  [{idx}/{total}] ⚠️  Failed to fetch — {url}")
                elif status.startswith("brand_mismatch"):
                    title_snippet = status.split(":", 1)[1]
                    print(f"  [{idx}/{total}] ⏭️  Not a match — {title_snippet}")
                elif asin in seen_asins:
                    print(f"  [{idx}/{total}] ⏭️  Duplicate ASIN {asin}")
                else:
                    seen_asins.add(asin)
                    products.append(details)
                    print(
                        f"  [{idx}/{total}] ✅ {details.get('title','N/A')[:55]}"
                        f"… | ₹{details.get('price','N/A')} | ⭐{details.get('rating','N/A')}"
                    )

    return products


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────

def main():
    global MAX_WORKERS, SEARCH_PAGES_PER_QUERY
    parser = argparse.ArgumentParser(description="Multi-Brand Amazon Product Scraper — TinyFish API")
    parser.add_argument(
        "--brand",
        choices=list(BRANDS_CONFIG.keys()) + ["all"],
        default="all",
        help="Brand to scrape, or 'all' (default: all)",
    )
    for brand_key in BRANDS_CONFIG.keys():
        parser.add_argument(f"--{brand_key}", action="store_true", help=f"Scrape {brand_key}")
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Parallel fetch workers (default: {MAX_WORKERS})",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=SEARCH_PAGES_PER_QUERY,
        help=f"Search pages per query (default: {SEARCH_PAGES_PER_QUERY})",
    )
    args = parser.parse_args()

    # Override globals from CLI
    MAX_WORKERS            = args.workers
    SEARCH_PAGES_PER_QUERY = args.pages

    selected_brand = args.brand
    for brand_key in BRANDS_CONFIG.keys():
        if getattr(args, brand_key.replace("-", "_"), False):
            selected_brand = brand_key
            break

    print("=" * 60)
    print("  Amazon Multi-Brand Scraper — TinyFish API (Optimised)")
    print(f"  Workers: {MAX_WORKERS}  |  Search pages/query: {SEARCH_PAGES_PER_QUERY}")
    print("=" * 60)

    if TINYFISH_API_KEY == "your_api_key_here":
        print("\n⚠️  Set your API key:  export TINYFISH_API_KEY='sk-...'")
        return

    brands_to_process = list(BRANDS_CONFIG.keys()) if selected_brand == "all" else [selected_brand]

    for brand_key in brands_to_process:
        brand_config = BRANDS_CONFIG[brand_key]
        search_name  = brand_config["search_name"]
        csv_filename = brand_config["csv_filename"]

        print(f"\n{'=' * 60}")
        print(f"  Brand: {search_name}")
        print(f"{'=' * 60}")

        # ── Phase 1: Collect URLs ─────────────────────────────────────
        print(f"\n📡 Phase 1: Searching Amazon.in for {search_name}…")
        t0 = time.time()
        all_urls = collect_all_urls(search_name)
        elapsed  = time.time() - t0
        print(f"\n  📦 {len(all_urls)} unique product URLs found in {elapsed:.1f}s")

        if not all_urls:
            print(f"❌ No URLs found for {search_name}. Skipping.")
            continue

        # ── Phase 2: Parallel scraping ────────────────────────────────
        print(f"\n🕷️  Phase 2: Scraping {len(all_urls)} pages (parallel, {MAX_WORKERS} workers)…")
        t0 = time.time()
        products = scrape_products_parallel(all_urls, brand_key)
        elapsed  = time.time() - t0
        print(f"\n  ⏱️  Scraping done in {elapsed:.1f}s")

        # ── Phase 3: Save ─────────────────────────────────────────────
        print(f"\n💾 Phase 3: Saving…")
        if products:
            save_to_csv(products, csv_filename)
        else:
            print(f"⚠️  No valid {search_name} products scraped.")

        print(f"\n{'=' * 60}")
        print(f"  DONE — {len(products)} {search_name} products → {csv_filename}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()