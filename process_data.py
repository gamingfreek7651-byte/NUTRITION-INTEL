import csv
import glob
import json
import os
import re
import math

def parse_price(val):
    if not val:
        return None
    val_clean = re.sub(r"[^\d.]", "", val)
    try:
        return float(val_clean)
    except ValueError:
        return None

def parse_int(val):
    if not val:
        return 0
    val_clean = re.sub(r"[^\d]", "", val)
    try:
        return int(val_clean)
    except ValueError:
        return 0

def parse_rating(val):
    if not val:
        return 0.0
    # Match decimal number like "4.3"
    match = re.search(r"(\d+\.?\d*)", val)
    try:
        return float(match.group(1)) if match else 0.0
    except ValueError:
        return 0.0

def parse_weight(row):
    # Try weight field first, then parse from title
    weight_str = row.get("weight", "") or ""
    title_str = row.get("title", "") or ""
    
    combined = (weight_str + " " + title_str).lower()
    
    # Check for kg, lbs, g
    # e.g., "1kg", "1 kg", "2.27 kg", "907g", "5 lbs", "2 lb"
    match_kg = re.search(r"(\d+\.?\d*)\s*kg", combined)
    if match_kg:
        return float(match_kg.group(1))
        
    match_g = re.search(r"(\d+\.?\d*)\s*g(rams)?", combined)
    if match_g:
        return float(match_g.group(1)) / 1000.0
        
    match_lbs = re.search(r"(\d+\.?\d*)\s*lb(s)?", combined)
    if match_lbs:
        return float(match_lbs.group(1)) * 0.453592
        
    return 1.0 # default weight in kg

def parse_protein(row):
    title = row.get("title", "") or ""
    specs = row.get("all_specs_json", "") or ""
    combined = (title + " " + specs).lower()
    
    # Look for "24g", "24 g", "24.5g protein"
    match = re.search(r"(\d+\.?\d*)\s*g\s*protein", combined)
    if match:
        return float(match.group(1))
    
    # Try just "24g" or specs
    match_g = re.search(r"(\d+\.?\d*)\s*g", row.get("protein_per_serving", "") or "")
    if match_g:
        return float(match_g.group(1))
        
    return 24.0 # default protein grams for supplements if not parsed

def clean_category(val):
    if not val:
        return "Other"
    
    # Extract last part of breadcrumb
    parts = val.split(">")
    cat = parts[-1].strip()
    
    # Direct translation of Hindi terms
    hindi_map = {
        "प्री-वर्कआउट": "Pre-Workout",
        "मटर प्रोटीन": "Pea Protein",
        "व्हे प्रोटीन": "Whey Protein",
        "क्रिएटिन": "Creatine",
        "एमिनो एसिड": "Amino Acids"
    }
    if cat in hindi_map:
        return hindi_map[cat]
        
    # Standard mapping to clean categories
    cat_lower = cat.lower()
    if "whey" in cat_lower:
        return "Whey Protein"
    elif "isolate" in cat_lower:
        return "Isolate Protein"
    elif "creatine" in cat_lower:
        return "Creatine"
    elif "mass" in cat_lower or "gainer" in cat_lower:
        return "Mass Gainer"
    elif "pre-workout" in cat_lower or "pre workout" in cat_lower:
        return "Pre-Workout"
    elif "pea" in cat_lower or "plant" in cat_lower:
        return "Plant Protein"
    elif "casein" in cat_lower:
        return "Casein Protein"
    elif "bcaa" in cat_lower:
        return "BCAA"
    elif "glutamine" in cat_lower:
        return "Glutamine"
    elif "multivitamin" in cat_lower or "mineral" in cat_lower:
        return "Multivitamins"
    elif "shilajit" in cat_lower:
        return "Shilajit"
    elif "peanut" in cat_lower:
        return "Peanut Butter"
    elif "fish oil" in cat_lower or "omega" in cat_lower:
        return "Omega & Fish Oil"
    
    return cat.strip()

def main():
    print("Processing scraped CSV files...")
    
    csv_files = {
        "optimum_nutrition": "optimum_nutrition_amazon_products.csv",
        "muscleblaze": "muscleblaze_amazon_products.csv",
        "nutrabay": "nutrabay_amazon_products.csv",
        "nakpro": "nakpro_amazon_products.csv",
        "as-it-is": "as-it-is_amazon_products.csv"
    }
    
    brand_map = {
        "optimum_nutrition": "Optimum Nutrition",
        "muscleblaze": "MuscleBlaze",
        "nutrabay": "Nutrabay",
        "nakpro": "Nakpro",
        "as-it-is": "AS-IT-IS"
    }
    
    raw_products = []
    
    for key, filename in csv_files.items():
        if not os.path.exists(filename):
            print(f"Warning: {filename} does not exist. Skipping.")
            continue
            
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                asin = row.get("asin", "").strip()
                title = row.get("title", "").strip()
                if not asin or not title:
                    continue
                
                price = parse_price(row.get("price"))
                mrp = parse_price(row.get("mrp"))
                rating = parse_rating(row.get("rating"))
                ratings_count = parse_int(row.get("num_ratings"))
                reviews_count = parse_int(row.get("num_reviews"))
                if not reviews_count:
                    # Estimate reviews count if missing
                    reviews_count = int(ratings_count * 0.12)
                
                # Discount calculation
                discount = 0.0
                disc_str = row.get("discount_percent", "")
                if disc_str:
                    disc_clean = re.sub(r"[^\d.]", "", disc_str)
                    try:
                        discount = float(disc_clean)
                    except ValueError:
                        pass
                if not discount and mrp and price and mrp > price:
                    discount = round(((mrp - price) / mrp) * 100, 1)
                
                # Standardize category
                category = clean_category(row.get("category_breadcrumb"))
                
                # BSR Extraction
                bsr = 999999
                bsr_str = row.get("best_seller_rank", "")
                if bsr_str:
                    bsr_match = re.search(r"#(\d{1,3}(?:,\d{3})*)", bsr_str)
                    if bsr_match:
                        bsr = int(bsr_match.group(1).replace(",", ""))
                
                # Specifications
                weight = parse_weight(row)
                flavour = row.get("flavour", "").strip() or "Unflavoured"
                protein = parse_protein(row)
                servings = parse_int(row.get("servings")) or int(weight * 30)
                item_form = row.get("item_form", "").strip() or "Powder"
                diet_type = row.get("diet_type", "").strip() or "Vegetarian"
                
                raw_products.append({
                    "asin": asin,
                    "title": title,
                    "brand": brand_map[key],
                    "price": price or (mrp or 1000.0), # fallback
                    "mrp": mrp or price or 1000.0,
                    "discount": discount,
                    "rating": rating or 4.0, # default if 0
                    "ratings_count": ratings_count,
                    "reviews_count": reviews_count,
                    "category": category,
                    "bsr": bsr,
                    "weight": round(weight, 2),
                    "flavour": flavour,
                    "protein": protein,
                    "servings": servings,
                    "item_form": item_form,
                    "diet_type": diet_type,
                    "image": row.get("main_image_url", "").strip() or "https://images.unsplash.com/photo-1579758629938-03607ccdbaba?w=400",
                    "url": row.get("url", "").strip() or f"https://www.amazon.in/dp/{asin}",
                    "scraped_at": row.get("scraped_at", "").strip() or "2026-06-20T12:00:00"
                })
                count += 1
            print(f"Parsed {count} products from {filename}")

    if not raw_products:
        print("No products parsed! Exiting.")
        return

    # Normalize stats for business scoring
    max_ratings = max(p["ratings_count"] for p in raw_products) or 1
    max_reviews = max(p["reviews_count"] for p in raw_products) or 1
    max_bsr = max(p["bsr"] for p in raw_products) or 1
    
    # Calculate derived business scores for each product
    for p in raw_products:
        # 1. Demand Score (log scale to control outliers)
        raw_demand = p["ratings_count"] + (p["reviews_count"] * 2)
        demand_score = min(100.0, max(0.0, (math.log10(raw_demand + 1) / math.log10(max_ratings + 2*max_reviews + 1)) * 100))
        p["demand_score"] = round(demand_score, 1)
        
        # 2. Product Popularity Score (Rating * Demand Log)
        popularity_score = (p["rating"] / 5.0) * demand_score * 0.7 + (1.0 - min(1.0, p["bsr"] / 50000.0)) * 30.0
        p["popularity_score"] = round(min(100.0, max(0.0, popularity_score)), 1)
        
        # 3. Value Score (Protein per price unit and rating)
        protein_ratio = p["protein"] / p["price"] if p["price"] else 0
        # Scale to max ratio in dataset
        val_score = (protein_ratio * 1000) * 10.0 + (p["rating"] * 8.0)
        p["value_score"] = round(min(100.0, max(0.0, val_score)), 1)
        
        # 4. Competitive Score (Index of popularity, rating, BSR position)
        comp_score = (p["popularity_score"] * 0.4) + (p["demand_score"] * 0.3) + (p["rating"] * 20.0 * 0.3)
        p["competitive_score"] = round(min(100.0, max(0.0, comp_score)), 1)
        
        # 5. Sentiment metrics
        # Positive sentiment estimated from rating (e.g. 5 stars = 100%, 1 star = 0%)
        # Normal distributions based on rating:
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
    brands = list(brand_map.values())
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
    # Categories with moderate/high average ratings, high average price, but low competition (< 10 products total)
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
            "scraped_date": "2026-06-20",
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
