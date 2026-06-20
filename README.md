# Amazon India Nutrition Supplement Competitive Intelligence Platform

An investor-grade, SaaS-style marketplace intelligence platform analyzing Amazon India's nutrition supplement segment. Designed as a high-end corporate analytics tool to help brands, analysts, and product managers monitor competition, optimize pricing, and find growing niches.

### 🌟 Project Preview
![App Interface Preview](APP.png)

---

## 🎥 Demonstration Video
Below is a video walkthrough showcasing the collapsible navigation, filter command bar, cross-filtering, product spec drawers, and the McKinsey-style benchmarking matrix:

<video src="NUTRITION%20INTEL.mp4" width="100%" controls></video>

---

## 🚀 Key Modules & Features

### 1. Business Intelligence Console (7 Specialized Modules)
* **Executive Overview**: Total segment indicators, brand reviews share (Share of Voice), category distribution, and top demand products.
* **Competitive Intelligence**: McKinsey-style benchmarking matrix and bubble-scatter positioning map (bubble size = review volume).
* **Pricing Strategy**: Price tier stacks (Budget, Mid, Premium), discount dependency analysis, and category average prices.
* **Product Performance**: Inventory catalog explorer with advanced sorting, popularity score indicators, and detail drawers.
* **Consumer Sentiment**: Sentiment index ratio, star rating frequencies, and brand trust satisfaction ledgers.
* **Portfolio Analysis**: Assortment matrix, product form distribution, unique flavor diversity, and protein content comparisons.
* **Opportunity Center**: Algorithmic whitespace opportunity scores, executive advisory recommendations, and opportunity sub-tabs.

### 2. Data Engineering Pipeline (`process_data.py`)
Converts raw scraper data from Optimum Nutrition, MuscleBlaze, Nutrabay, Nakpro, and AS-IT-IS into a single optimized `data.json` database.
* **Standardization**: Cleans currency symbols, translates Hindi text tags (e.g. `"व्हे प्रोटीन"` to `"Whey Protein"`), and normalizes weights (lbs/grams to standard Kg).
* **Derived Analytics Formulas**:
  * **Demand Score**: Logarithmic ratings and reviews scale to control skewness.
  * **Popularity Index**: Normalized composition of BSR rank, reviews count, and stars.
  * **Value Score**: Correlates protein density per rupee spent with customer satisfaction.
  * **Competitive Score**: Shows the market presence of competitor listings.
* **Whitespace Detection**: Algorithmic scoring of niches with high consumer demand (>4.0 stars) but low listing saturation (<12 competing products).

---

## ⚙️ Local Run Instructions

### Prerequisites
* Python 3.8 or higher.
* Web Browser (Chrome, Firefox, Safari).

### Setup and Launch
1. Clone the repository:
   ```bash
   git clone https://github.com/gamingfreek7651-byte/NUTRITION-INTEL.git
   cd NUTRITION-INTEL
   ```
2. Run the local development server:
   ```bash
   python app.py
   ```
3. Open your browser and navigate to:
   ```text
   http://localhost:8000
   ```

---

## 🛠️ Technical Stack
* **Backend Pipeline**: Python (Standard `csv`, `re`, `json`, `math` libraries)
* **Frontend client**: Vanilla HTML5, Vanilla CSS3 (Custom properties, grid systems, HSL-based colors), Vanilla JavaScript ES6
* **Visualizations**: Chart.js v4.x (Scatter, Bubble, Doughnut, Bar charts)
* **Hosting Support**: Fully static, portable architecture compatible with GitHub Pages, Vercel, and Netlify.

---

**Built by Yogesh Kumar | Amazon Nutrition Market Intelligence Platform**
