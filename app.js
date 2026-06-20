// APPLICATION STATE
let allData = null;
let filteredProducts = [];
let chartInstances = {};

const state = {
    currentTab: 'overview',
    filters: {
        brands: new Set(),
        categories: new Set(),
        rating: 0.0,
        priceMin: null,
        priceMax: null,
        stockOnly: false,
        search: ''
    },
    opportunityTab: 'gems'
};

// INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchDashboardData();
});

// EVENT LISTENERS SETUP
function initEventListeners() {
    // Landing Page launch buttons
    const launchBtns = document.querySelectorAll('.landing-cta-btn, .btn-primary-large');
    launchBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('landingView').style.display = 'none';
            document.getElementById('appConsoleView').style.display = 'flex';
            switchTab('overview');
        });
    });

    // Collapsible Left Navigation
    const sidebar = document.getElementById('sidebar');
    const sidebarBtn = document.getElementById('sidebarCollapseBtn');
    if (sidebarBtn) {
        sidebarBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }

    // Collapsible Right Filter Pane
    const filterPane = document.getElementById('filterPane');
    const filterBtn = document.getElementById('filterPaneToggleBtn');
    if (filterBtn) {
        filterBtn.addEventListener('click', () => {
            filterPane.classList.toggle('closed');
        });
    }

    // Sidebar Tab Clicks
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = item.getAttribute('data-tab');
            if (tabName) {
                switchTab(tabName);
            }
        });
    });

    // Reset Filters Button
    const resetBtn = document.getElementById('filterResetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            resetAllFilters();
        });
    }

    // Global Search input
    const searchInput = document.getElementById('globalSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            state.filters.search = e.target.value.trim().toLowerCase();
            applyFiltersAndRender();
        });
    }

    // Price Filters
    const minPriceInput = document.getElementById('filterPriceMin');
    const maxPriceInput = document.getElementById('filterPriceMax');
    if (minPriceInput) {
        minPriceInput.addEventListener('input', (e) => {
            state.filters.priceMin = e.target.value ? parseFloat(e.target.value) : null;
            applyFiltersAndRender();
        });
    }
    if (maxPriceInput) {
        maxPriceInput.addEventListener('input', (e) => {
            state.filters.priceMax = e.target.value ? parseFloat(e.target.value) : null;
            applyFiltersAndRender();
        });
    }

    // Rating Filter Select
    const ratingSelect = document.getElementById('filterRatingSelect');
    if (ratingSelect) {
        ratingSelect.addEventListener('change', (e) => {
            state.filters.rating = parseFloat(e.target.value);
            applyFiltersAndRender();
        });
    }

    // Availability Filter
    const stockCheckbox = document.getElementById('filterStockIn');
    if (stockCheckbox) {
        stockCheckbox.addEventListener('change', (e) => {
            state.filters.stockOnly = e.target.checked;
            applyFiltersAndRender();
        });
    }

    // Export Button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            exportToCSV();
        });
    }

    // Close Drawer events
    const drawerCloseBtn = document.getElementById('drawerCloseBtn');
    const drawerOverlay = document.getElementById('drawerOverlay');
    if (drawerCloseBtn) drawerCloseBtn.addEventListener('click', closeProductDrawer);
    if (drawerOverlay) drawerOverlay.addEventListener('click', closeProductDrawer);

    // Opportunity Sub-tabs
    const oppTabsHeader = document.getElementById('opportunityTabsHeader');
    if (oppTabsHeader) {
        oppTabsHeader.addEventListener('click', (e) => {
            if (e.target.classList.contains('opp-tab-btn')) {
                document.querySelectorAll('.opp-tab-btn').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                state.opportunityTab = e.target.getAttribute('data-opp');
                renderOpportunityProductsTable();
            }
        });
    }
}

// FETCH DATA FROM JSON FILE
function fetchDashboardData() {
    fetch('data.json')
        .then(response => {
            if (!response.ok) {
                throw new Error("HTTP error " + response.status);
            }
            return response.json();
        })
        .then(data => {
            allData = data;
            
            // Populate data metadata
            if (data.metadata && data.metadata.scraped_date) {
                document.getElementById('refreshDate').textContent = data.metadata.scraped_date;
            }
            
            // Extract unique categories and brands for filter initialization
            initFiltersUI();
            
            // Apply initial filtering and display Overview
            applyFiltersAndRender();
        })
        .catch(error => {
            console.error("Failed to load dashboard dataset:", error);
            // In case dataset load failed, show error message
            alert("Error loading data.json dataset. Please ensure process_data.py has generated data.json and it is served correctly.");
        });
}

// POPULATE DYNAMIC BRAND & CATEGORY FILTER LISTS
function initFiltersUI() {
    if (!allData) return;

    // Brands List
    const brandsList = document.getElementById('filterBrandsList');
    brandsList.innerHTML = '';
    const brandsSet = new Set(allData.products.map(p => p.brand));
    Array.from(brandsSet).sort().forEach(brandName => {
        const label = document.createElement('label');
        label.className = 'checkbox-label';
        
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.value = brandName;
        input.addEventListener('change', (e) => {
            if (e.target.checked) {
                state.filters.brands.add(brandName);
            } else {
                state.filters.brands.delete(brandName);
            }
            applyFiltersAndRender();
        });
        
        const span = document.createElement('span');
        span.textContent = brandName;
        
        label.appendChild(input);
        label.appendChild(span);
        brandsList.appendChild(label);
    });

    // Categories List
    const categoriesList = document.getElementById('filterCategoriesList');
    categoriesList.innerHTML = '';
    const categoriesSet = new Set(allData.products.map(p => p.category));
    Array.from(categoriesSet).sort().forEach(catName => {
        const label = document.createElement('label');
        label.className = 'checkbox-label';
        
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.value = catName;
        input.addEventListener('change', (e) => {
            if (e.target.checked) {
                state.filters.categories.add(catName);
            } else {
                state.filters.categories.delete(catName);
            }
            applyFiltersAndRender();
        });
        
        const span = document.createElement('span');
        span.textContent = catName;
        
        label.appendChild(input);
        label.appendChild(span);
        categoriesList.appendChild(label);
    });
}

// RESET ALL FILTER SELECTIONS
function resetAllFilters() {
    state.filters.brands.clear();
    state.filters.categories.clear();
    state.filters.rating = 0.0;
    state.filters.priceMin = null;
    state.filters.priceMax = null;
    state.filters.stockOnly = false;
    state.filters.search = '';

    // Clear UI controls
    document.querySelectorAll('#filterBrandsList input').forEach(input => input.checked = false);
    document.querySelectorAll('#filterCategoriesList input').forEach(input => input.checked = false);
    document.getElementById('filterRatingSelect').value = "0";
    document.getElementById('filterPriceMin').value = "";
    document.getElementById('filterPriceMax').value = "";
    document.getElementById('filterStockIn').checked = false;
    document.getElementById('globalSearchInput').value = "";

    applyFiltersAndRender();
}

// TAB NAVIGATION SWITCH
function switchTab(tabName) {
    if (tabName === 'portal') {
        document.getElementById('appConsoleView').style.display = 'none';
        document.getElementById('landingView').style.display = 'block';
        
        // Clear active highlights on side menu
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
        return;
    }

    state.currentTab = tabName;
    
    // Highlight sidebar nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('data-tab') === tabName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Show selected page element
    document.querySelectorAll('.content-page').forEach(page => {
        page.classList.remove('active');
    });
    
    const activePage = document.getElementById('page-' + tabName);
    if (activePage) {
        activePage.classList.add('active');
    }

    renderCurrentTab();
}

// DATA FILTERING ENGINE
function applyFiltersAndRender() {
    if (!allData) return;

    filteredProducts = allData.products.filter(product => {
        // Brand filter
        if (state.filters.brands.size > 0 && !state.filters.brands.has(product.brand)) {
            return false;
        }
        
        // Category filter
        if (state.filters.categories.size > 0 && !state.filters.categories.has(product.category)) {
            return false;
        }
        
        // Rating filter
        if (product.rating < state.filters.rating) {
            return false;
        }
        
        // Price Min filter
        if (state.filters.priceMin !== null && product.price < state.filters.priceMin) {
            return false;
        }
        
        // Price Max filter
        if (state.filters.priceMax !== null && product.price > state.filters.priceMax) {
            return false;
        }
        
        // Availability / Stock Filter
        if (state.filters.stockOnly && product.availability !== "In stock") {
            return false;
        }
        
        // Search Filter
        if (state.filters.search !== '') {
            const matchesSearch = 
                product.title.toLowerCase().includes(state.filters.search) || 
                product.brand.toLowerCase().includes(state.filters.search) || 
                product.category.toLowerCase().includes(state.filters.search) || 
                product.flavour.toLowerCase().includes(state.filters.search);
            if (!matchesSearch) return false;
        }

        return true;
    });

    // Rebuild active filter badges
    renderFilterBadges();
    
    // Update KPI panels with calculated aggregates
    updateKPICards();

    // Render active tab visualizations
    renderCurrentTab();
}

// RENDER FILTER BADGES IN TOP COMMAND BAR
function renderFilterBadges() {
    const container = document.getElementById('activeFiltersContainer');
    container.innerHTML = '';

    // helper function to create badge
    const createBadge = (text, removeCallback) => {
        const badge = document.createElement('div');
        badge.className = 'filter-badge';
        badge.innerHTML = `<span>${text}</span>`;
        
        const close = document.createElement('span');
        close.className = 'filter-badge-remove';
        close.innerHTML = '&times;';
        close.addEventListener('click', removeCallback);
        
        badge.appendChild(close);
        container.appendChild(badge);
    };

    // Brands
    state.filters.brands.forEach(b => {
        createBadge(`Brand: ${b}`, () => {
            state.filters.brands.delete(b);
            // Uncheck UI control
            document.querySelectorAll('#filterBrandsList input').forEach(input => {
                if (input.value === b) input.checked = false;
            });
            applyFiltersAndRender();
        });
    });

    // Categories
    state.filters.categories.forEach(c => {
        createBadge(`Cat: ${c}`, () => {
            state.filters.categories.delete(c);
            document.querySelectorAll('#filterCategoriesList input').forEach(input => {
                if (input.value === c) input.checked = false;
            });
            applyFiltersAndRender();
        });
    });

    // Rating
    if (state.filters.rating > 0) {
        createBadge(`Rating: ${state.filters.rating}+ ⭐`, () => {
            state.filters.rating = 0.0;
            document.getElementById('filterRatingSelect').value = "0";
            applyFiltersAndRender();
        });
    }

    // Prices
    if (state.filters.priceMin !== null) {
        createBadge(`Min Price: ₹${state.filters.priceMin}`, () => {
            state.filters.priceMin = null;
            document.getElementById('filterPriceMin').value = "";
            applyFiltersAndRender();
        });
    }
    if (state.filters.priceMax !== null) {
        createBadge(`Max Price: ₹${state.filters.priceMax}`, () => {
            state.filters.priceMax = null;
            document.getElementById('filterPriceMax').value = "";
            applyFiltersAndRender();
        });
    }

    // Availability
    if (state.filters.stockOnly) {
        createBadge("In Stock Only", () => {
            state.filters.stockOnly = false;
            document.getElementById('filterStockIn').checked = false;
            applyFiltersAndRender();
        });
    }
}

// UPDATE TOP KPI CARDS
function updateKPICards() {
    if (filteredProducts.length === 0) {
        document.getElementById('kpi-total-products').textContent = '0';
        document.getElementById('kpi-avg-price').textContent = '₹0';
        document.getElementById('kpi-avg-rating').textContent = '0.0';
        document.getElementById('kpi-total-reviews').textContent = '0';
        document.getElementById('kpi-market-leader').textContent = 'N/A';
        return;
    }

    const totalProducts = filteredProducts.length;
    const totalPrice = filteredProducts.reduce((sum, p) => sum + p.price, 0);
    const avgPrice = totalPrice / totalProducts;
    
    const totalRating = filteredProducts.reduce((sum, p) => sum + p.rating, 0);
    const avgRating = totalRating / totalProducts;
    
    const totalReviews = filteredProducts.reduce((sum, p) => sum + p.reviews_count, 0);
    
    // Find Leader Brand (by Total Reviews)
    const brandReviews = {};
    filteredProducts.forEach(p => {
        brandReviews[p.brand] = (brandReviews[p.brand] || 0) + p.reviews_count;
    });
    
    let leaderBrand = 'N/A';
    let maxReviews = -1;
    for (const b in brandReviews) {
        if (brandReviews[b] > maxReviews) {
            maxReviews = brandReviews[b];
            leaderBrand = b;
        }
    }

    document.getElementById('kpi-total-products').textContent = totalProducts.toLocaleString();
    document.getElementById('kpi-avg-price').textContent = formatCurrency(avgPrice);
    document.getElementById('kpi-avg-rating').textContent = avgRating.toFixed(2) + ' ★';
    document.getElementById('kpi-total-reviews').textContent = totalReviews.toLocaleString();
    document.getElementById('kpi-market-leader').textContent = leaderBrand;
}

// DESTROY CHART HELPER
function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

// MAIN RENDER SWITCH
function renderCurrentTab() {
    if (!allData) return;

    // Defer chart rendering if the console view is hidden to prevent 0px canvas issues
    const consoleView = document.getElementById('appConsoleView');
    if (consoleView && consoleView.style.display === 'none') {
        return;
    }

    // Destroy all current charts to avoid drawing conflicts
    Object.keys(chartInstances).forEach(key => destroyChart(key));

    switch (state.currentTab) {
        case 'overview':
            renderOverviewTab();
            break;
        case 'competitive':
            renderCompetitiveTab();
            break;
        case 'pricing':
            renderPricingTab();
            break;
        case 'performance':
            renderPerformanceTab();
            break;
        case 'sentiment':
            renderSentimentTab();
            break;
        case 'portfolio':
            renderPortfolioTab();
            break;
        case 'opportunity':
            renderOpportunityTab();
            break;
    }
}

// ----------------------------------------------------
// 1. EXECUTIVE OVERVIEW PAGE RENDER
// ----------------------------------------------------
function renderOverviewTab() {
    // A. Market Share Donut/Pie (Reviews)
    const brandReviews = {};
    filteredProducts.forEach(p => {
        brandReviews[p.brand] = (brandReviews[p.brand] || 0) + p.reviews_count;
    });

    const brands = Object.keys(brandReviews);
    const reviews = Object.values(brandReviews);
    const colors = getBrandColorPalette(brands);

    const ctxShare = document.getElementById('marketShareChart').getContext('2d');
    chartInstances['marketShareChart'] = new Chart(ctxShare, {
        type: 'bar',
        data: {
            labels: brands,
            datasets: [{
                label: 'Total Reviews',
                data: reviews,
                backgroundColor: colors,
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { borderDash: [2, 2] } }
            }
        }
    });

    // B. Category Distribution Chart (Horizontal Bar)
    const categoryCounts = {};
    filteredProducts.forEach(p => {
        categoryCounts[p.category] = (categoryCounts[p.category] || 0) + 1;
    });

    // Sort categories by count desc
    const sortedCats = Object.entries(categoryCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 7);

    const catLabels = sortedCats.map(x => x[0]);
    const catData = sortedCats.map(x => x[1]);

    const ctxCat = document.getElementById('categoryDistributionChart').getContext('2d');
    chartInstances['categoryDistributionChart'] = new Chart(ctxCat, {
        type: 'bar',
        data: {
            labels: catLabels,
            datasets: [{
                data: catData,
                backgroundColor: '#4B5563', // Slate Gray
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { borderDash: [2, 2] } },
                y: { grid: { display: false } }
            }
        }
    });

    // C. Brand Core Stats Sidebar list
    const brandCounts = {};
    const brandPriceSum = {};
    const brandRatingSum = {};
    filteredProducts.forEach(p => {
        brandCounts[p.brand] = (brandCounts[p.brand] || 0) + 1;
        brandPriceSum[p.brand] = (brandPriceSum[p.brand] || 0) + p.price;
        brandRatingSum[p.brand] = (brandRatingSum[p.brand] || 0) + p.rating;
    });

    const brandListContainer = document.getElementById('brandOverviewStatsList');
    brandListContainer.innerHTML = '';
    
    // Sort brands by count desc
    const sortedBrands = Object.keys(brandCounts).sort((a, b) => brandCounts[b] - brandCounts[a]);
    
    if (sortedBrands.length === 0) {
        brandListContainer.innerHTML = '<div style="color: var(--color-secondary); font-size:13px;">No data to display. Apply filters to refresh.</div>';
    } else {
        const maxProds = brandCounts[sortedBrands[0]];
        sortedBrands.forEach(b => {
            const count = brandCounts[b];
            const avgP = brandPriceSum[b] / count;
            const avgR = brandRatingSum[b] / count;
            const pct = (count / maxProds) * 100;
            
            const item = document.createElement('div');
            item.className = 'stats-item';
            item.innerHTML = `
                <div class="stats-item-header">
                    <span class="stats-item-title">${b}</span>
                    <span class="stats-item-value">${count} Products</span>
                </div>
                <div style="font-size:11px; color: var(--color-secondary); margin-top:2px;">
                    Avg Price: ${formatCurrency(avgP)} | Avg Rating: ${avgR.toFixed(1)} ★
                </div>
                <div class="stats-item-bar">
                    <div class="stats-item-bar-fill" style="width: ${pct}%; background-color: ${getSingleBrandColor(b)}"></div>
                </div>
            `;
            brandListContainer.appendChild(item);
        });
    }

    // D. Overview Top Products Table
    const topProducts = [...filteredProducts]
        .sort((a, b) => b.reviews_count - a.reviews_count)
        .slice(0, 5);

    const tbody = document.querySelector('#overviewTopProductsTable tbody');
    tbody.innerHTML = '';
    
    if (topProducts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--color-secondary);">No products available.</td></tr>';
    } else {
        topProducts.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 500; font-size: 13px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="#" class="product-link" onclick="openProductDrawer('${p.asin}'); return false;">${p.title}</a>
                    </div>
                </td>
                <td>${p.brand}</td>
                <td><span class="stars-container">${renderStars(p.rating)} (${p.rating.toFixed(1)})</span></td>
                <td>${p.reviews_count.toLocaleString()}</td>
                <td>${formatCurrency(p.price)}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// ----------------------------------------------------
// 2. COMPETITIVE INTELLIGENCE PAGE RENDER
// ----------------------------------------------------
function renderCompetitiveTab() {
    // A. Benchmarking Matrix Table (McKinsey style)
    const table = document.getElementById('competitiveBenchmarkingTable');
    table.innerHTML = '';

    // List of active brands in filter (or fallback to all)
    const activeBrands = state.filters.brands.size > 0 
        ? Array.from(state.filters.brands)
        : ["Optimum Nutrition", "MuscleBlaze", "Nutrabay", "Nakpro", "AS-IT-IS"];

    // Compute aggregates per brand dynamically based on filtered set
    const matrix = {
        "Product Count": {},
        "Average Rating": {},
        "Share of Voice (Reviews %)": {},
        "Average Selling Price (ASP)": {},
        "Average Discount": {},
        "Core Category": {}
    };

    const totalReviews = filteredProducts.reduce((sum, p) => sum + p.reviews_count, 0);

    activeBrands.forEach(b => {
        const prods = filteredProducts.filter(p => p.brand === b);
        const count = prods.length;
        
        if (count > 0) {
            const avgRating = prods.reduce((sum, p) => sum + p.rating, 0) / count;
            const bReviews = prods.reduce((sum, p) => sum + p.reviews_count, 0);
            const rShare = totalReviews > 0 ? (bReviews / totalReviews) * 100 : 0;
            const avgPrice = prods.reduce((sum, p) => sum + p.price, 0) / count;
            const avgDiscount = prods.reduce((sum, p) => sum + p.discount, 0) / count;
            
            // Core Category
            const cats = {};
            prods.forEach(p => cats[p.category] = (cats[p.category] || 0) + 1);
            let coreCat = 'N/A';
            let maxCount = -1;
            for (const c in cats) {
                if (cats[c] > maxCount) {
                    maxCount = cats[c];
                    coreCat = c;
                }
            }

            matrix["Product Count"][b] = count.toLocaleString();
            matrix["Average Rating"][b] = avgRating.toFixed(2) + ' ★';
            matrix["Share of Voice (Reviews %)"][b] = rShare.toFixed(1) + '%';
            matrix["Average Selling Price (ASP)"][b] = formatCurrency(avgPrice);
            matrix["Average Discount"][b] = avgDiscount.toFixed(1) + '%';
            matrix["Core Category"][b] = coreCat;
        } else {
            matrix["Product Count"][b] = '0';
            matrix["Average Rating"][b] = 'N/A';
            matrix["Share of Voice (Reviews %)"][b] = '0.0%';
            matrix["Average Selling Price (ASP)"][b] = 'N/A';
            matrix["Average Discount"][b] = 'N/A';
            matrix["Core Category"][b] = 'N/A';
        }
    });

    // Build Table HTML
    let tableHTML = '<thead><tr><th>Benchmarking Dimension</th>';
    activeBrands.forEach(b => {
        tableHTML += `<th>${b}</th>`;
    });
    tableHTML += '</tr></thead><tbody>';

    for (const dimension in matrix) {
        tableHTML += `<tr><td class="feature-header">${dimension}</td>`;
        activeBrands.forEach(b => {
            tableHTML += `<td>${matrix[dimension][b]}</td>`;
        });
        tableHTML += '</tr>';
    }
    tableHTML += '</tbody>';
    table.innerHTML = tableHTML;

    // B. Competitive Positioning Map Scatter Plot (Rating vs Price)
    const scatterData = filteredProducts.map(p => ({
        x: p.price,
        y: p.rating,
        r: Math.min(15, Math.max(4, Math.log10(p.reviews_count + 1) * 3)), // radius scaled log reviews
        brand: p.brand,
        title: p.title
    }));

    const ctxScatter = document.getElementById('competitivePositioningChart').getContext('2d');
    chartInstances['competitivePositioningChart'] = new Chart(ctxScatter, {
        type: 'bubble',
        data: {
            datasets: activeBrands.map(b => ({
                label: b,
                data: scatterData.filter(d => d.brand === b),
                backgroundColor: getSingleBrandColor(b) + 'CC', // add transparency
                borderColor: getSingleBrandColor(b),
                borderWidth: 1
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const raw = context.raw;
                            return [
                                `Product: ${raw.title.substring(0, 50)}...`,
                                `Price: ${formatCurrency(raw.x)}`,
                                `Rating: ${raw.y.toFixed(1)} ★`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Selling Price (₹)' },
                    grid: { borderDash: [2, 2] }
                },
                y: {
                    title: { display: true, text: 'Rating' },
                    min: 1.0,
                    max: 5.1,
                    grid: { borderDash: [2, 2] }
                }
            }
        }
    });

    // C. Review share (pie concentration)
    const totalReviewsAll = activeBrands.map(b => {
        return filteredProducts.filter(p => p.brand === b).reduce((sum, p) => sum + p.reviews_count, 0);
    });

    const ctxConcentration = document.getElementById('marketConcentrationChart').getContext('2d');
    chartInstances['marketConcentrationChart'] = new Chart(ctxConcentration, {
        type: 'pie',
        data: {
            labels: activeBrands,
            datasets: [{
                data: totalReviewsAll,
                backgroundColor: getBrandColorPalette(activeBrands),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8 } }
            }
        }
    });

    // Concentration Analysis text
    const summaryText = document.getElementById('concentrationSummaryText');
    const sortedShares = activeBrands.map((b, i) => ({ brand: b, reviews: totalReviewsAll[i] }))
        .sort((a, b) => b.reviews - a.reviews);
    
    if (sortedShares.length > 0 && totalReviews > 0) {
        const topB = sortedShares[0];
        const topShare = (topB.reviews / totalReviews) * 100;
        summaryText.innerHTML = `
            <strong>Analysis:</strong> 
            The market shows high concentration. <strong>${topB.brand}</strong> commands a dominant 
            <strong>${topShare.toFixed(1)}%</strong> share of customer review volume (Share of Voice).
        `;
    } else {
        summaryText.textContent = '';
    }
}

// ----------------------------------------------------
// 3. PRICING STRATEGY PAGE RENDER
// ----------------------------------------------------
function renderPricingTab() {
    const activeBrands = state.filters.brands.size > 0 
        ? Array.from(state.filters.brands)
        : ["Optimum Nutrition", "MuscleBlaze", "Nutrabay", "Nakpro", "AS-IT-IS"];

    // A. Price Tiers Chart (Budget vs Mid vs Premium)
    const tiersData = {
        "Budget (< ₹1500)": [],
        "Mid (₹1500-₹3000)": [],
        "Premium (> ₹3000)": []
    };

    activeBrands.forEach(b => {
        const bProds = filteredProducts.filter(p => p.brand === b);
        const budget = bProds.filter(p => p.price < 1500).length;
        const mid = bProds.filter(p => p.price >= 1500 && p.price <= 3000).length;
        const premium = bProds.filter(p => p.price > 3000).length;
        
        tiersData["Budget (< ₹1500)"].push(budget);
        tiersData["Mid (₹1500-₹3000)"].push(mid);
        tiersData["Premium (> ₹3000)"].push(premium);
    });

    const ctxTiers = document.getElementById('priceTiersChart').getContext('2d');
    chartInstances['priceTiersChart'] = new Chart(ctxTiers, {
        type: 'bar',
        data: {
            labels: activeBrands,
            datasets: [
                {
                    label: 'Budget (< ₹1500)',
                    data: tiersData["Budget (< ₹1500)"],
                    backgroundColor: '#9CA3AF' // Slate Gray light
                },
                {
                    label: 'Mid (₹1500-₹3000)',
                    data: tiersData["Mid (₹1500-₹3000)"],
                    backgroundColor: '#4B5563' // Slate Gray normal
                },
                {
                    label: 'Premium (> ₹3000)',
                    data: tiersData["Premium (> ₹3000)"],
                    backgroundColor: '#1F2937' // Dark Charcoal
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, grid: { borderDash: [2, 2] } }
            }
        }
    });

    // B. Discount Dependency Scatter (Discount % vs Rating)
    const discountData = filteredProducts.map(p => ({
        x: p.discount,
        y: p.rating,
        r: 6,
        brand: p.brand
    }));

    const ctxDiscount = document.getElementById('discountDependencyChart').getContext('2d');
    chartInstances['discountDependencyChart'] = new Chart(ctxDiscount, {
        type: 'scatter',
        data: {
            datasets: activeBrands.map(b => ({
                label: b,
                data: discountData.filter(d => d.brand === b),
                backgroundColor: getSingleBrandColor(b) + 'DD',
                borderColor: getSingleBrandColor(b),
                borderWidth: 1
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Average Discount (%)' },
                    grid: { borderDash: [2, 2] }
                },
                y: {
                    title: { display: true, text: 'Product Rating' },
                    min: 1.0,
                    max: 5.1,
                    grid: { borderDash: [2, 2] }
                }
            }
        }
    });

    // C. Pricing Benchmark Table
    const tbody = document.querySelector('#pricingBenchmarkTable tbody');
    tbody.innerHTML = '';
    
    const categoriesSet = new Set(filteredProducts.map(p => p.category));
    const sortedCats = Array.from(categoriesSet).sort();
    
    if (sortedCats.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--color-secondary);">No category data available.</td></tr>';
    } else {
        sortedCats.forEach(cat => {
            const tr = document.createElement('tr');
            let trHTML = `<td style="font-weight:600;">${cat}</td>`;
            
            const columnBrands = ["Optimum Nutrition", "MuscleBlaze", "Nutrabay", "Nakpro", "AS-IT-IS"];
            columnBrands.forEach(b => {
                const cProds = filteredProducts.filter(p => p.brand === b && p.category === cat);
                if (cProds.length > 0) {
                    const avgPrice = cProds.reduce((sum, p) => sum + p.price, 0) / cProds.length;
                    trHTML += `<td>${formatCurrency(avgPrice)} <span style="font-size:10px; color:var(--color-secondary);">(${cProds.length})</span></td>`;
                } else {
                    trHTML += `<td style="color:var(--color-secondary);">-</td>`;
                }
            });
            tr.innerHTML = trHTML;
            tbody.appendChild(tr);
        });
    }
}

// ----------------------------------------------------
// 4. PRODUCT PERFORMANCE PAGE RENDER
// ----------------------------------------------------
function renderPerformanceTab() {
    const tbody = document.querySelector('#productPerformanceCatalogTable tbody');
    tbody.innerHTML = '';

    // Sort by popularity desc
    const sortedProducts = [...filteredProducts]
        .sort((a, b) => b.popularity_score - a.popularity_score)
        .slice(0, 50); // Show top 50

    if (sortedProducts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color: var(--color-secondary);">No products match the selected criteria.</td></tr>';
    } else {
        sortedProducts.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <img src="${p.image}" class="table-prod-img" alt="product" style="width: 32px; height: 32px; object-fit: contain; border: 1px solid var(--color-border); border-radius:4px; padding: 2px;">
                </td>
                <td>
                    <div style="font-weight: 500; font-size: 13px; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="#" class="product-link" onclick="openProductDrawer('${p.asin}'); return false;" title="${p.title}">${p.title}</a>
                    </div>
                    <div style="font-size: 10px; color: var(--color-secondary); margin-top:2px;">
                        ASIN: ${p.asin} | ${p.category} | ${p.flavour} | ${p.weight} kg
                    </div>
                </td>
                <td style="font-weight: 500;">${p.brand}</td>
                <td style="font-weight: 600;">${formatCurrency(p.price)}</td>
                <td><span class="stars-container">${renderStars(p.rating)} (${p.rating.toFixed(1)})</span></td>
                <td>${p.reviews_count.toLocaleString()}</td>
                <td style="font-family: monospace;">#${p.bsr !== 999999 ? p.bsr.toLocaleString() : 'N/A'}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 600; min-width:24px;">${p.popularity_score}</span>
                        <div class="stats-item-bar" style="width: 50px; margin-top: 0;">
                            <div class="stats-item-bar-fill" style="width: ${p.popularity_score}%; background-color: var(--color-accent);"></div>
                        </div>
                    </div>
                </td>
                <td style="text-align: center;">
                    <button class="btn-detail" onclick="openProductDrawer('${p.asin}')">Details</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// ----------------------------------------------------
// 5. CONSUMER SENTIMENT PAGE RENDER
// ----------------------------------------------------
function renderSentimentTab() {
    const activeBrands = state.filters.brands.size > 0 
        ? Array.from(state.filters.brands)
        : ["Optimum Nutrition", "MuscleBlaze", "Nutrabay", "Nakpro", "AS-IT-IS"];

    // A. Trust / Sentiment Index Chart
    const positiveSentiment = [];
    const negativeSentiment = [];
    activeBrands.forEach(b => {
        const bProds = filteredProducts.filter(p => p.brand === b);
        if (bProds.length > 0) {
            const avgPos = bProds.reduce((sum, p) => sum + p.sentiment_positive, 0) / bProds.length;
            positiveSentiment.push(avgPos);
            negativeSentiment.push(100.0 - avgPos);
        } else {
            positiveSentiment.push(0);
            negativeSentiment.push(0);
        }
    });

    const ctxTrust = document.getElementById('brandTrustScoreChart').getContext('2d');
    chartInstances['brandTrustScoreChart'] = new Chart(ctxTrust, {
        type: 'bar',
        data: {
            labels: activeBrands,
            datasets: [
                {
                    label: 'Positive Sentiment %',
                    data: positiveSentiment,
                    backgroundColor: 'var(--color-positive)'
                },
                {
                    label: 'Negative Sentiment %',
                    data: negativeSentiment,
                    backgroundColor: 'var(--color-negative)'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, max: 100, grid: { borderDash: [2, 2] } }
            }
        }
    });

    // B. Overall Rating Distribution Chart
    const ratingTiers = {
        "5 ★": 0,
        "4 ★": 0,
        "3 ★": 0,
        "2 ★": 0,
        "1 ★": 0
    };

    filteredProducts.forEach(p => {
        if (p.rating >= 4.5) ratingTiers["5 ★"]++;
        else if (p.rating >= 3.8) ratingTiers["4 ★"]++;
        else if (p.rating >= 2.8) ratingTiers["3 ★"]++;
        else if (p.rating >= 1.8) ratingTiers["2 ★"]++;
        else if (p.rating > 0) ratingTiers["1 ★"]++;
    });

    const ctxRatingDist = document.getElementById('ratingDistributionChart').getContext('2d');
    chartInstances['ratingDistributionChart'] = new Chart(ctxRatingDist, {
        type: 'bar',
        data: {
            labels: Object.keys(ratingTiers),
            datasets: [{
                data: Object.values(ratingTiers),
                backgroundColor: '#FF9900', // Amazon Orange
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { borderDash: [2, 2] } }
            }
        }
    });

    // C. Satisfaction Ledger Table
    const tbody = document.querySelector('#satisfactionLedgerTable tbody');
    tbody.innerHTML = '';

    activeBrands.forEach(b => {
        const bProds = filteredProducts.filter(p => p.brand === b);
        const count = bProds.length;
        if (count > 0) {
            const avgRating = bProds.reduce((sum, p) => sum + p.rating, 0) / count;
            const totRatings = bProds.reduce((sum, p) => sum + p.ratings_count, 0);
            const avgPos = bProds.reduce((sum, p) => sum + p.sentiment_positive, 0) / count;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600;">${b}</td>
                <td><span class="stars-container">${renderStars(avgRating)} (${avgRating.toFixed(2)})</span></td>
                <td>${totRatings.toLocaleString()}</td>
                <td style="color: var(--color-positive); font-weight: 600;">${avgPos.toFixed(1)}%</td>
                <td style="color: var(--color-negative); font-weight: 600;">${(100.0 - avgPos).toFixed(1)}%</td>
            `;
            tbody.appendChild(tr);
        }
    });
}

// ----------------------------------------------------
// 6. PORTFOLIO ANALYSIS PAGE RENDER
// ----------------------------------------------------
function renderPortfolioTab() {
    const activeBrands = state.filters.brands.size > 0 
        ? Array.from(state.filters.brands)
        : ["Optimum Nutrition", "MuscleBlaze", "Nutrabay", "Nakpro", "AS-IT-IS"];

    // A. Assortment Matrix Table (penetration count grid)
    const assortment = document.getElementById('assortmentMatrixTable');
    assortment.innerHTML = '';
    
    const categoriesSet = new Set(filteredProducts.map(p => p.category));
    const categories = Array.from(categoriesSet).sort();

    // Table Header
    let tableHTML = '<thead><tr><th>Supplement Categories</th>';
    activeBrands.forEach(b => {
        tableHTML += `<th>${b}</th>`;
    });
    tableHTML += '</tr></thead><tbody>';

    categories.forEach(cat => {
        tableHTML += `<tr><td class="feature-header">${cat}</td>`;
        activeBrands.forEach(b => {
            const count = filteredProducts.filter(p => p.brand === b && p.category === cat).length;
            tableHTML += `<td>${count} Products</td>`;
        });
        tableHTML += '</tr>';
    });
    tableHTML += '</tbody>';
    assortment.innerHTML = tableHTML;

    // B. Form Factor Donut Chart
    const formCounts = {};
    filteredProducts.forEach(p => {
        formCounts[p.item_form] = (formCounts[p.item_form] || 0) + 1;
    });

    const ctxForm = document.getElementById('formFactorChart').getContext('2d');
    chartInstances['formFactorChart'] = new Chart(ctxForm, {
        type: 'doughnut',
        data: {
            labels: Object.keys(formCounts),
            datasets: [{
                data: Object.values(formCounts),
                backgroundColor: ['#1E1E1E', '#4B5563', '#9CA3AF', '#D1D5DB', '#F3F4F6'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8 } }
            }
        }
    });

    // C. Flavor counts (horizontal bar)
    const flavorCounts = {};
    activeBrands.forEach(b => {
        const bProds = filteredProducts.filter(p => p.brand === b);
        const flavors = new Set(bProds.map(p => p.flavour.toLowerCase()));
        flavorCounts[b] = flavors.size;
    });

    const ctxFlavors = document.getElementById('flavorCountChart').getContext('2d');
    chartInstances['flavorCountChart'] = new Chart(ctxFlavors, {
        type: 'bar',
        data: {
            labels: activeBrands,
            datasets: [{
                data: activeBrands.map(b => flavorCounts[b]),
                backgroundColor: '#FF9900', // Amazon Orange
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { borderDash: [2, 2] } },
                y: { grid: { display: false } }
            }
        }
    });

    // D. Portfolio compare table
    const tbody = document.querySelector('#portfolioCompareTable tbody');
    tbody.innerHTML = '';

    activeBrands.forEach(b => {
        const bProds = filteredProducts.filter(p => p.brand === b);
        const count = bProds.length;
        if (count > 0) {
            const avgWeight = bProds.reduce((sum, p) => sum + p.weight, 0) / count;
            const avgServings = bProds.reduce((sum, p) => sum + p.servings, 0) / count;
            const avgProtein = bProds.reduce((sum, p) => sum + p.protein, 0) / count;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600;">${b}</td>
                <td>${avgWeight.toFixed(2)} kg</td>
                <td>${Math.round(avgServings)}</td>
                <td>${avgProtein.toFixed(1)}g</td>
            `;
            tbody.appendChild(tr);
        }
    });
}

// ----------------------------------------------------
// 7. OPPORTUNITY CENTER PAGE RENDER
// ----------------------------------------------------
function renderOpportunityTab() {
    // A. Whitespace Opportunities Table
    const tbodyWS = document.querySelector('#whitespaceOpportunitiesTable tbody');
    tbodyWS.innerHTML = '';
    
    if (allData && allData.white_spaces && allData.white_spaces.length > 0) {
        allData.white_spaces.slice(0, 5).forEach(ws => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600;">${ws.category}</td>
                <td>${ws.product_count} Products</td>
                <td style="font-weight:500;">${formatCurrency(ws.avg_price)}</td>
                <td><span class="stars-container">${renderStars(ws.avg_rating)} (${ws.avg_rating.toFixed(2)})</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight:700; color: var(--color-accent);">${ws.score}</span>
                        <div class="stats-item-bar" style="width: 60px; margin-top:0;">
                            <div class="stats-item-bar-fill" style="width: ${Math.min(100, ws.score)}%; background-color: var(--color-accent);"></div>
                        </div>
                    </div>
                </td>
            `;
            tbodyWS.appendChild(tr);
        });
    } else {
        tbodyWS.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--color-secondary);">No whitespace opportunities found.</td></tr>';
    }

    // B. Strategic advisory list
    const advisoryList = document.getElementById('executiveRecommendationsList');
    advisoryList.innerHTML = `
        <div class="rec-item">
            <span class="rec-icon">💡</span>
            <div class="rec-text">
                <div class="rec-text-title">Premium Niche Expansion</div>
                Portfolio mapping suggests expanding premium isolate products. AS-IT-IS and Nakpro have low competition in premium bands.
            </div>
        </div>
        <div class="rec-item">
            <span class="rec-icon">⚠️</span>
            <div class="rec-text">
                <div class="rec-text-title">Product Reformulation Required</div>
                Identified <strong>${filteredProducts.filter(p => p.opportunity_class === "Underperformer").length}</strong> underperforming products with high visibility but low ratings. Focus on flavor refinement.
            </div>
        </div>
        <div class="rec-item">
            <span class="rec-icon">🎯</span>
            <div class="rec-text">
                <div class="rec-text-title">Marketing Optimization</div>
                Promote "Hidden Gems" (high ratings but low reviews) using sponsor ads on core keywords to drive visibility.
            </div>
        </div>
    `;

    // C. Products Table according to opportunity tabs
    renderOpportunityProductsTable();
}

function renderOpportunityProductsTable() {
    const tbody = document.querySelector('#opportunityProductsTable tbody');
    tbody.innerHTML = '';

    const oppMapping = {
        "gems": "Hidden Gem",
        "stars": "Rising Star",
        "underperformers": "Underperformer",
        "premium": "Premium Winner"
    };

    const targetClass = oppMapping[state.opportunityTab] || "Hidden Gem";
    const oppProducts = filteredProducts.filter(p => p.opportunity_class === targetClass)
        .sort((a, b) => b.popularity_score - a.popularity_score)
        .slice(0, 15);

    if (oppProducts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--color-secondary);">No products classified as ${targetClass} under current filters.</td></tr>`;
    } else {
        oppProducts.forEach(p => {
            const scoreVal = p.competitive_score;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 500; font-size: 13px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="#" class="product-link" onclick="openProductDrawer('${p.asin}'); return false;">${p.title}</a>
                    </div>
                </td>
                <td style="font-weight:500;">${p.brand}</td>
                <td>${p.category}</td>
                <td style="font-weight:600;">${formatCurrency(p.price)}</td>
                <td><span class="stars-container">${renderStars(p.rating)} (${p.rating.toFixed(1)})</span></td>
                <td>${p.reviews_count.toLocaleString()}</td>
                <td>
                    <span style="font-weight:600;">Score: ${scoreVal}</span>
                </td>
                <td style="text-align: center;">
                    <button class="btn-detail" onclick="openProductDrawer('${p.asin}')">Details</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// ----------------------------------------------------
// PRODUCT DETAIL DRAWER (POPUP)
// ----------------------------------------------------
function openProductDrawer(asin) {
    const product = allData.products.find(p => p.asin === asin);
    if (!product) return;

    const drawer = document.getElementById('detailDrawer');
    const overlay = document.getElementById('drawerOverlay');
    const content = document.getElementById('drawerContent');

    content.innerHTML = `
        <div class="drawer-content-header">
            <img src="${product.image}" class="drawer-img" alt="product">
            <div>
                <div class="drawer-brand">${product.brand}</div>
                <h2 class="drawer-title">${product.title}</h2>
                <div style="margin-top: 8px;">
                    <span class="stars-container">${renderStars(product.rating)}</span>
                    <span style="font-size: 12px; color: var(--color-secondary); margin-left: 6px;">(${product.rating.toFixed(1)} ★ | ${product.ratings_count.toLocaleString()} Ratings)</span>
                </div>
            </div>
        </div>

        <div class="drawer-body-grid">
            <div class="drawer-info-block">
                <div class="drawer-info-lbl">Market Price</div>
                <div class="drawer-info-val">${formatCurrency(product.price)}</div>
            </div>
            <div class="drawer-info-block">
                <div class="drawer-info-lbl">List MRP</div>
                <div class="drawer-info-val" style="text-decoration: line-through; font-size:14px; font-weight:500; color:var(--color-secondary);">${formatCurrency(product.mrp)}</div>
            </div>
            <div class="drawer-info-block">
                <div class="drawer-info-lbl">Discount Value</div>
                <div class="drawer-info-val" style="color: var(--color-negative);">${product.discount}% OFF</div>
            </div>
            <div class="drawer-info-block">
                <div class="drawer-info-lbl">Best Seller Rank</div>
                <div class="drawer-info-val">#${product.bsr !== 999999 ? product.bsr.toLocaleString() : 'N/A'}</div>
            </div>
            <div class="drawer-info-block">
                <div class="drawer-info-lbl">Popularity Score</div>
                <div class="drawer-info-val" style="color: var(--color-accent);">${product.popularity_score} / 100</div>
            </div>
            <div class="drawer-info-block">
                <div class="drawer-info-lbl">Derived Value Score</div>
                <div class="drawer-info-val">${product.value_score} / 100</div>
            </div>
        </div>

        <div class="drawer-info-block" style="margin-bottom: 24px;">
            <div class="drawer-info-lbl">Opportunity Tag</div>
            <div class="drawer-info-val" style="font-size: 14px; color: var(--color-positive); font-weight:600;">${product.opportunity_class}</div>
        </div>

        <div style="margin-bottom: 24px;">
            <h3 style="font-size: 13px; font-weight:600; text-transform:uppercase; color:var(--color-secondary); margin-bottom:8px;">Product Specifications</h3>
            <table class="drawer-specs-table">
                <tr>
                    <td>Category</td>
                    <td>${product.category}</td>
                </tr>
                <tr>
                    <td>Flavour</td>
                    <td>${product.flavour}</td>
                </tr>
                <tr>
                    <td>Weight</td>
                    <td>${product.weight} Kg</td>
                </tr>
                <tr>
                    <td>Protein Content</td>
                    <td>${product.protein}g</td>
                </tr>
                <tr>
                    <td>Servings Count</td>
                    <td>${product.servings} Servings</td>
                </tr>
                <tr>
                    <td>Item Form</td>
                    <td>${product.item_form}</td>
                </tr>
                <tr>
                    <td>Diet Category</td>
                    <td>${product.diet_type}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin-top:30px;">
            <a href="${product.url}" target="_blank" class="action-btn" style="background-color: var(--color-accent); border: none; color: #111827; display: inline-flex; justify-content:center; width: 100%; font-weight: 600;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                View Live on Amazon.in
            </a>
        </div>
    `;

    drawer.classList.add('open');
    overlay.classList.add('active');
}

function closeProductDrawer() {
    document.getElementById('detailDrawer').classList.remove('open');
    document.getElementById('drawerOverlay').classList.remove('active');
}

// ----------------------------------------------------
// EXPORT CURRENT FILTERED PRODUCTS TO CSV
// ----------------------------------------------------
function exportToCSV() {
    if (filteredProducts.length === 0) {
        alert("No filtered products to export!");
        return;
    }

    const headers = [
        "ASIN", "Title", "Brand", "Price", "MRP", "Discount %", 
        "Rating", "Ratings Count", "Reviews Count", "Category", 
        "BSR Rank", "Weight", "Flavour", "Protein (g)", "Servings", 
        "Opportunity Class", "Amazon URL"
    ];

    let csvContent = "data:text/csv;charset=utf-8,\ufeff";
    csvContent += headers.map(h => `"${h.replace(/"/g, '""')}"`).join(",") + "\n";

    filteredProducts.forEach(p => {
        const row = [
            p.asin,
            p.title,
            p.brand,
            p.price,
            p.mrp,
            p.discount,
            p.rating,
            p.ratings_count,
            p.reviews_count,
            p.category,
            p.bsr,
            p.weight,
            p.flavour,
            p.protein,
            p.servings,
            p.opportunity_class,
            p.url
        ];
        csvContent += row.map(v => {
            const strVal = v !== undefined && v !== null ? String(v) : '';
            return `"${strVal.replace(/"/g, '""')}"`;
        }).join(",") + "\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `competitive_intel_export_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ----------------------------------------------------
// HELPER STYLE & FORMATTING FUNCTIONS
// ----------------------------------------------------
function getBrandColorPalette(brandList) {
    return brandList.map(b => getSingleBrandColor(b));
}

function getSingleBrandColor(brandName) {
    const map = {
        "Optimum Nutrition": "#1F2937", // Dark Charcoal-Gray
        "MuscleBlaze": "#FF9900",       // Amazon Orange
        "Nutrabay": "#3B82F6",          // Royal Blue
        "Nakpro": "#10B981",            // Emerald Green
        "AS-IT-IS": "#8B5CF6"           // Purple
    };
    return map[brandName] || "#6B7280"; // fallback Gray
}

function formatCurrency(val) {
    if (val === undefined || val === null || isNaN(val)) return '₹0.00';
    return '₹' + val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderStars(rating) {
    let starsHTML = '';
    const rounded = Math.round(rating * 2) / 2; // round to nearest 0.5
    for (let i = 1; i <= 5; i++) {
        if (i <= rounded) {
            starsHTML += '★';
        } else if (i - 0.5 === rounded) {
            starsHTML += '½'; // Show half star
        } else {
            starsHTML += '☆';
        }
    }
    return starsHTML;
}
