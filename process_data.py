import csv
import json
import os
import re
import math

def parse_price(val):
    if not val:
        return None
    # Strip currency symbol and commas
    val_clean = re.sub(r"[^\d.]", "", str(val))
    try:
        return float(val_clean)
    except ValueError:
        return None

def parse_int(val):
    if not val:
        return 0
    val_clean = re.sub(r"[^\d]", "", str(val))
    try:
        return int(val_clean)
    except ValueError:
        return 0

def parse_rating(val):
    if not val:
        return 0.0
    # Match decimal number like "4.3"
    match = re.search(r"(\d+\.?\d*)", str(val))
    try:
        return float(match.group(1)) if match else 0.0
    except ValueError:
        return 0.0

def parse_weight_from_size(size_str, title_str=""):
    if not size_str:
        size_str = ""
    size_str = str(size_str).lower()
    title_str = str(title_str).lower()
    combined = size_str + " " + title_str

    # Try finding kilograms (kg / kilograms)
    kg_match = re.search(r"(\d+\.?\d*)\s*(kilograms|kg)", combined)
    if kg_match:
        return float(kg_match.group(1))
        
    # Try finding grams (g / grams)
    g_match = re.search(r"(\d+\.?\d*)\s*(grams|g)", combined)
    if g_match:
        return float(g_match.group(1)) / 1000.0
        
    # Try finding lbs (lbs / lb)
    lbs_match = re.search(r"(\d+\.?\d*)\s*(lbs|lb)", combined)
    if lbs_match:
        return float(lbs_match.group(1)) * 0.453592
        
    return 1.0 # default weight in kg

def parse_servings(servings_str):
    if not servings_str:
        return 0
    servings_str = str(servings_str).lower()
    match = re.search(r"(\d+)", servings_str)
    if match:
        return int(match.group(1))
    return 0

def clean_category(val):
    if not val:
        return "Other"
    
    parts = val.split(">")
    cat = parts[-1].strip()
    
    # Hindi mapping
    hindi_map = {
        "प्री-वर्कआउट": "Pre-Workout",
        "मटर प्रोटीन": "Pea Protein",
        "व्हे प्रोटीन": "Whey Protein",
        "क्रिएटिन": "Creatine",
        "एमिनो एसिड": "Amino Acids"
    }
    if cat in hindi_map:
        return hindi_map[cat]
        
    return cat

def main():
    csv_file = r"C:\WorkSpace\scrapper\Final file.csv"
    print(f"Processing data from: {csv_file}")
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} does not exist!")
        return

    brand_map = {
        "nutrabay": "Nutrabay",
        "optimum nutrition": "Optimum Nutrition",
        "nakpro": "Nakpro",
        "muscleblaze nutrition": "MuscleBlaze",
        "muscleblaze": "MuscleBlaze",
        "as-it-is nutrition": "AS-IT-IS",
        "as-it-is": "AS-IT-IS"
    }

    raw_products = []
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            asin = row.get("ASIN", "").strip()
            title = row.get("Title", "").strip()
            if not asin or not title:
                continue
            
            # Brand clean
            brand_raw = row.get("Brand", "").strip()
            brand = brand_map.get(brand_raw.lower(), brand_raw)
            
            price = parse_price(row.get("Price"))
            mrp = parse_price(row.get("MRP"))
            
            # Discount
            discount = 0.0
            disc_str = row.get("Discount%", "")
            if disc_str:
                disc_clean = re.sub(r"[^\d.]", "", str(disc_str))
                try:
                    discount = float(disc_clean)
                except ValueError:
                    pass
            if not discount and mrp and price and mrp > price:
                discount = round(((mrp - price) / mrp) * 100, 1)
            
            rating = parse_rating(row.get("Ratings"))
            reviews_count = parse_int(row.get("Reviews"))
            ratings_count = reviews_count # Map ratings_count to reviews_count for consistency
            
            category = clean_category(row.get("Category"))
            
            availability_raw = row.get("Availability", "").strip()
            if availability_raw.lower() in ["in stock", "instock", "available"]:
                availability = "In Stock"
            else:
                availability = "Out Of Stock"
                
            url = row.get("URL", "").strip()
            size = row.get("Size", "").strip() or "Not specified"
            servings = parse_servings(row.get("Servings"))
            flavour = row.get("Flavour", "").strip() or "Unflavoured"
            
            weight = parse_weight_from_size(size, title)
            
            raw_products.append({
                "asin": asin,
                "title": title,
                "brand": brand,
                "price": price or (mrp or 1000.0),
                "mrp": mrp or price or 1000.0,
                "discount": discount,
                "rating": rating or 4.0,
                "ratings_count": ratings_count,
                "reviews_count": reviews_count,
                "category": category,
                "availability": availability,
                "url": url or f"https://www.amazon.in/dp/{asin}",
                "size": size,
                "servings": servings,
                "flavour": flavour,
                "weight": round(weight, 2),
                # Fallback image URL
                "image": "https://images.unsplash.com/photo-1579758629938-03607ccdbaba?w=400"
            })
            count += 1
            
        print(f"Parsed {count} products from {csv_file}")

    if not raw_products:
        print("No products parsed! Exiting.")
        return

    # Normalize stats for business scoring
    max_reviews = max(p["reviews_count"] for p in raw_products) or 1
    
    # Calculate derived business scores for each product
    for p in raw_products:
        # 1. Demand Score (log scale of reviews)
        raw_demand = p["reviews_count"]
        demand_score = min(100.0, max(0.0, (math.log10(raw_demand + 1) / math.log10(max_reviews + 1)) * 100))
        p["demand_score"] = round(demand_score, 1)
        
        # 2. Product Popularity Score (Rating * Demand Log)
        popularity_score = (p["rating"] / 5.0) * demand_score
        p["popularity_score"] = round(min(100.0, max(0.0, popularity_score)), 1)
        
        # 3. Value Score (Weighted based on Rating, Discount, and Price)
        val_score = (p["rating"] * 10.0) + (p["discount"] * 0.6) + (1.0 - min(1.0, p["price"] / 6000.0)) * 20.0
        p["value_score"] = round(min(100.0, max(0.0, val_score)), 1)
        
        # 4. Competitive Score (Index of popularity, rating, demand)
        comp_score = (p["popularity_score"] * 0.5) + (p["demand_score"] * 0.2) + (p["rating"] * 20.0 * 0.3)
        p["competitive_score"] = round(min(100.0, max(0.0, comp_score)), 1)
        
        # 5. Sentiment metrics
        pos_pct = min(100.0, max(0.0, (p["rating"] - 1.0) / 4.0 * 100.0 + 5.0))
        p["sentiment_positive"] = round(pos_pct, 1)
        p["sentiment_negative"] = round(100.0 - pos_pct, 1)

    # Opportunity Classification Engine
    classified_products = []
    category_counts = {}
    for p in raw_products:
        category_counts[p["category"]] = category_counts.get(p["category"], 0) + 1
        
    for p in raw_products:
        op = "Market Follower"
        
        # Market Leaders: High demand + high trust
        if p["popularity_score"] >= 75 and p["rating"] >= 4.2:
            op = "Market Leader"
        # Hidden Gems: High rating + low visibility
        elif p["rating"] >= 4.3 and p["ratings_count"] < 80:
            op = "Hidden Gem"
        # Underperformers: High visibility but poor ratings
        elif p["ratings_count"] >= 150 and p["rating"] < 3.8:
            op = "Underperformer"
        # Premium Winners: High price + strong customer acceptance
        elif p["price"] >= 2800 and p["rating"] >= 4.2 and p["ratings_count"] >= 100:
            op = "Premium Winner"
        # Rising Stars: High popularity score growth potential, mid price
        elif p["popularity_score"] >= 50 and p["popularity_score"] < 75 and p["rating"] >= 4.1:
            op = "Rising Star"
            
        p["opportunity_class"] = op
        classified_products.append(p)

    # Calculate Brand-Level Aggregations
    brands = list(set(p["brand"] for p in classified_products))
    brand_stats = {}
    for b in brands:
        b_prods = [p for p in classified_products if p["brand"] == b]
        if not b_prods:
            continue
        avg_rating = sum(p["rating"] for p in b_prods) / len(b_prods)
        total_ratings = sum(p["ratings_count"] for p in b_prods)
        total_reviews = sum(p["reviews_count"] for p in b_prods)
        avg_price = sum(p["price"] for p in b_prods) / len(b_prods)
        avg_mrp = sum(p["mrp"] for p in b_prods) / len(b_prods)
        avg_discount = sum(p["discount"] for p in b_prods) / len(b_prods)
        avg_popularity = sum(p["popularity_score"] for p in b_prods) / len(b_prods)
        avg_value = sum(p["value_score"] for p in b_prods) / len(b_prods)
        
        brand_stats[b] = {
            "product_count": len(b_prods),
            "avg_rating": round(avg_rating, 2),
            "total_ratings": total_ratings,
            "total_reviews": total_reviews,
            "avg_price": round(avg_price, 2),
            "avg_mrp": round(avg_mrp, 2),
            "avg_discount": round(avg_discount, 2),
            "avg_popularity": round(avg_popularity, 2),
            "avg_value": round(avg_value, 2),
            "sentiment_positive": round(sum(p["sentiment_positive"] for p in b_prods) / len(b_prods), 1)
        }
        
    # Calculate Category-Level Aggregations
    categories = list(set(p["category"] for p in classified_products))
    category_stats = {}
    for c in categories:
        c_prods = [p for p in classified_products if p["category"] == c]
        avg_rating = sum(p["rating"] for p in c_prods) / len(c_prods)
        avg_price = sum(p["price"] for p in c_prods) / len(c_prods)
        total_reviews = sum(p["reviews_count"] for p in c_prods)
        
        category_stats[c] = {
            "product_count": len(c_prods),
            "avg_rating": round(avg_rating, 2),
            "avg_price": round(avg_price, 2),
            "total_reviews": total_reviews
        }

    # Opportunity: White Space Detection
    white_spaces = []
    for c, stats in category_stats.items():
        if stats["product_count"] < 12 and stats["avg_rating"] >= 4.0:
            white_spaces.append({
                "category": c,
                "product_count": stats["product_count"],
                "avg_price": stats["avg_price"],
                "avg_rating": stats["avg_rating"],
                "reviews": stats["total_reviews"],
                "score": round((stats["avg_rating"] * 10) + (stats["avg_price"] / 100) + (100 - stats["product_count"] * 5), 1)
            })
    white_spaces = sorted(white_spaces, key=lambda x: x["score"], reverse=True)

    # Consolidated JSON database output
    output_data = {
        "metadata": {
            "scraped_date": "2026-06-21",
            "total_products": len(classified_products),
            "total_ratings": sum(p["ratings_count"] for p in classified_products),
            "total_reviews": sum(p["reviews_count"] for p in classified_products),
            "global_avg_rating": round(sum(p["rating"] for p in classified_products) / len(classified_products), 2),
            "global_avg_price": round(sum(p["price"] for p in classified_products) / len(classified_products), 2)
        },
        "brand_stats": brand_stats,
        "category_stats": category_stats,
        "white_spaces": white_spaces,
        "products": classified_products
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully processed {len(classified_products)} products and saved to data.json!")

if __name__ == "__main__":
    main()
