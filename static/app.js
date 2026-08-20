const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const state = {
    lang: 'ko',
    kind: 'overall',
    page: 0,
    q: '',
    category: '',
    products: [],
    currentPeriod: 'daily'
};

const T = {
    ko: {
        navTrend: '트렌드 인텔리전스',
        navProducts: '상품 인텔리전스',
        eyebrow: 'K-BEAUTY MARKET SIGNALS',
        trendTitle: '오늘의 K-Beauty 트렌드',
        trendSub: '검색·소셜·지역 신호를 기반으로 시장의 흐름을 봅니다.',
        signals: 'Raw Signals',
        topTrendLabel: 'Top Trend',
        googleSignals: 'Google Signals',
        rising: '🔥 Rising Trends',
        google: '🔎 Google Search Signals',
        trendMatrix: '📈 Trend Score Matrix',
        themeRollup: '🧩 테마별 트렌드',
        daily: '일간',
        weekly: '주간',
        monthly: '월간',
        productTitle: '상품 랭킹 & 전체 카탈로그',
        productSub: '올리브영·다이소·자체 종합점수로 상품의 시장 위치를 비교합니다.',
        overall: '종합랭킹',
        olive: '올리브영',
        daiso: '다이소',
        scoreDesc: '자체 0–100 통합점수',
        catalog: '🛍️ Full Product Catalog',
        catalogSub: '카테고리·성분·키워드로 전체 상품을 탐색합니다.',
        searchPh: '상품명·브랜드·성분 검색',
        allCategories: '전체 카테고리',
        loadMore: '더 보기',
        score: '점수',
        rank: '랭크',
        source: '채널',
        details: '상품 상세',
        ingredients: 'Ingredients',
        product_type: 'Product Type',
        keywords: 'Keywords',
        skin_type: 'Skin Type',
        concerns: 'Concerns',
        texture: 'Texture',
        key_ingredients: 'Key Ingredients',
        claims: 'Claims',
        noData: '데이터 없음',
        newEntries: '신규 진입',
        risingTrends: '급상승',
        coolingTrends: '냉각/이탈'
    },
    en: {
        navTrend: 'Trend Intelligence',
        navProducts: 'Product Intelligence',
        eyebrow: 'K-BEAUTY MARKET SIGNALS',
        trendTitle: "Today's K-Beauty Trends",
        trendSub: 'Read market flow from search, social and regional signals.',
        signals: 'Raw Signals',
        topTrendLabel: 'Top Trend',
        googleSignals: 'Google Signals',
        rising: '🔥 Rising Trends',
        google: '🔎 Google Search Signals',
        trendMatrix: '📈 Trend Score Matrix',
        themeRollup: '🧩 Theme Rollup',
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly',
        productTitle: 'Product Rankings & Full Catalog',
        productSub: 'Compare market position using Olive Young, Daiso and a unified score.',
        overall: 'Overall Ranking',
        olive: 'Olive Young',
        daiso: 'Daiso',
        scoreDesc: 'Unified 0–100 score',
        catalog: '🛍️ Full Product Catalog',
        catalogSub: 'Explore products by category, ingredients and keywords.',
        searchPh: 'Search product, brand or ingredient',
        allCategories: 'All categories',
        loadMore: 'Load more',
        score: 'Score',
        rank: 'Rank',
        source: 'Channel',
        details: 'Product Details',
        ingredients: 'Ingredients',
        product_type: 'Product Type',
        keywords: 'Keywords',
        skin_type: 'Skin Type',
        concerns: 'Concerns',
        texture: 'Texture',
        key_ingredients: 'Key Ingredients',
        claims: 'Claims',
        noData: 'No data',
        newEntries: 'New Entries',
        risingTrends: 'Rising',
        coolingTrends: 'Cooling'
    },
    ar: {
        navTrend: 'ذكاء الاتجاهات',
        navProducts: 'ذكاء المنتجات',
        eyebrow: 'إشارات سوق K-BEAUTY',
        trendTitle: 'اتجاهات K-Beauty اليوم',
        trendSub: 'اقرأ حركة السوق من إشارات البحث والتواصل والمناطق.',
        signals: 'الإشارات الخام',
        topTrendLabel: 'أبرز اتجاه',
        googleSignals: 'إشارات Google',
        rising: '🔥 الاتجاهات الصاعدة',
        google: '🔎 إشارات بحث Google',
        trendMatrix: '📈 مصفوفة درجات الاتجاه',
        themeRollup: '🧩 ملخص الثيمات',
        daily: 'يومي',
        weekly: 'أسبوعي',
        monthly: 'شهري',
        productTitle: 'ترتيب المنتجات والكتالوج الكامل',
        productSub: 'قارن موقع المنتج باستخدام Olive Young وDaiso والدرجة الموحدة.',
        overall: 'الترتيب العام',
        olive: 'Olive Young',
        daiso: 'Daiso',
        scoreDesc: 'درجة موحدة من 0 إلى 100',
        catalog: '🛍️ كتالوج المنتجات',
        catalogSub: 'استكشف المنتجات حسب الفئة والمكونات والكلمات المفتاحية.',
        searchPh: 'ابحث عن منتج أو علامة أو مكوّن',
        allCategories: 'كل الفئات',
        loadMore: 'عرض المزيد',
        score: 'الدرجة',
        rank: 'الترتيب',
        source: 'القناة',
        details: 'تفاصيل المنتج',
        ingredients: 'Ingredients',
        product_type: 'Product Type',
        keywords: 'Keywords',
        skin_type: 'Skin Type',
        concerns: 'Concerns',
        texture: 'Texture',
        key_ingredients: 'Key Ingredients',
        claims: 'Claims',
        noData: 'لا توجد بيانات',
        newEntries: 'إدخالات جديدة',
        risingTrends: 'صاعد',
        coolingTrends: 'يبرد'
    }
};

function tr(k) { return T[state.lang][k] || T.en[k] || k; }

function esc(x) { return String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function arr(v) { if (!v) return []; if (Array.isArray(v)) return v; try { const x = JSON.parse(v); if (Array.isArray(x)) return x; } catch {} return String(v).split(/[,|;\n]+/).map(x => x.trim()).filter(Boolean); }

async function api(u) { const r = await fetch(u); if (!r.ok) throw Error(r.status); return r.json(); }

function applyLang() {
    document.documentElement.lang = state.lang;
    document.body.classList.toggle('rtl', state.lang === 'ar');
    $$('[data-t]').forEach(e => e.textContent = tr(e.dataset.t));
    $$('[data-ph]').forEach(e => e.placeholder = tr(e.dataset.ph));
}

// ========== Navigation ==========
$$('.langs button').forEach(b => b.onclick = () => { state.lang = b.dataset.lang; applyLang(); renderAll(); });

$$('.nav').forEach(b => b.onclick = () => {
    const p = b.dataset.page;
    $$('.nav').forEach(x => x.classList.toggle('active', x === b));
    $$('.page').forEach(x => x.classList.remove('active'));
    $('#' + p + 'Page').classList.add('active');
    if (p === 'products' && !state.products.length) loadProducts();
});

// ========== Period Tabs (Daily/Weekly/Monthly) ==========
$$('.periodTab').forEach(b => b.onclick = () => {
    state.currentPeriod = b.dataset.period;
    $$('.periodTab').forEach(x => x.classList.toggle('active', x === b));
    $$('.periodContent').forEach(x => x.classList.remove('active'));
    $('#' + state.currentPeriod + 'Content').classList.add('active');
    loadPeriodData();
});

// ========== Render Functions ==========
const fmt = x => Number(x || 0).toFixed(1);

function lifecycleBadge(info) {
    return `<span class="lifecycleBadge" style="background:${info.color}22;color:${info.color};border:1px solid ${info.color}44">
        ${info.icon} ${info.label}
    </span>`;
}

function renderTrends(a) {
    $('#trendList').innerHTML = a.length ? a.map((x, i) => `
        <div class="trendRow">
            <div class="rankNo">${i + 1}</div>
            <div style="flex:1">
                <div class="trendName">${esc(x.keyword)}</div>
                <div class="trendMeta">
                    ${lifecycleBadge(x.lifecycle_info || {label:'Unknown',color:'#6b7280',icon:'❓'})}
                    <span class="metaChip">${esc(x.theme_info?.label || 'Other')}</span>
                    ${x.z_score ? `<span class="metaChip">Z: ${fmt(x.z_score)}</span>` : ''}
                </div>
                <div class="bar"><i style="width:${Math.min(100, Number(x.trend_score) || 0)}%"></i></div>
            </div>
            <div class="grow">${fmt(x.trend_score)}</div>
        </div>
    `).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderGoogle(a) {
    $('#googleList').innerHTML = a.length ? a.map(x => `
        <div class="googleRow">
            <div style="flex:1">
                <b>${esc(x.keyword)}</b>
                <div class="meta">${esc(x.region || 'global')} · ${esc(x.source || 'Google')}</div>
            </div>
            <div class="grow">${Number(x.rising_score || 0).toFixed(1)} ↑</div>
        </div>
    `).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderMatrix(a) {
    $('#trendMatrix').innerHTML = a.map(x => `
        <div class="trendRow">
            <div style="width:150px">
                <b>${esc(x.keyword)}</b>
                <div class="trendMeta">
                    ${lifecycleBadge(x.lifecycle_info || {label:'Unknown',color:'#6b7280',icon:'❓'})}
                </div>
            </div>
            <div style="flex:1">
                <div class="meta">
                    Volume ${fmt(x.volume_score)} · 
                    Velocity ${fmt(x.velocity_score)} · 
                    ${x.z_score ? `Z-score ${fmt(x.z_score)} · ` : ''}
                    Cross-platform ${fmt(x.cross_platform_score)}
                </div>
            </div>
            <b>${fmt(x.trend_score)}</b>
        </div>
    `).join('');
}

function renderThemes(themes) {
    $('#themeGrid').innerHTML = themes.map(t => `
        <div class="themeCard" style="border-color:${t.color}44">
            <div class="themeHeader">
                <span class="themeIcon">${t.icon}</span>
                <span class="themeName">${esc(t.label)}</span>
            </div>
            <div class="themeScore" style="color:${t.color}">${fmt(t.total_score)}</div>
            <div class="meta">${t.keyword_count} keywords</div>
            <div class="themeKeywords">
                ${t.top_keywords.slice(0, 5).map(k => `<span class="chip">${esc(k.keyword)}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function renderDelta(delta, containerId) {
    const container = $(containerId);
    container.innerHTML = `
        <div class="deltaCard">
            <h3 class="new">🆕 ${tr('newEntries')}</h3>
            <ul class="deltaList">
                ${delta.new.length ? delta.new.slice(0, 10).map(x => `<li>${esc(x.keyword)} <b>${fmt(x.score)}</b></li>`).join('') : '<li>None</li>'}
            </ul>
        </div>
        <div class="deltaCard">
            <h3 class="rising">📈 ${tr('risingTrends')}</h3>
            <ul class="deltaList">
                ${delta.rising.length ? delta.rising.slice(0, 10).map(x => `<li>${esc(x.keyword)} <b>${fmt(x.prev_score)} → ${fmt(x.curr_score)}</b></li>`).join('') : '<li>None</li>'}
            </ul>
        </div>
        <div class="deltaCard">
            <h3 class="cooling">📉 ${tr('coolingTrends')}</h3>
            <ul class="deltaList">
                ${delta.cooling.length ? delta.cooling.slice(0, 10).map(x => `<li>${esc(x.keyword)} <b>${fmt(x.prev_score)}${x.curr_score ? ' → ' + fmt(x.curr_score) : ' (gone)'}</b></li>`).join('') : '<li>None</li>'}
            </ul>
        </div>
    `;
}

function renderWeeklyTrends(a) {
    $('#weeklyList').innerHTML = a.length ? a.map((x, i) => `
        <div class="trendRow">
            <div class="rankNo">${i + 1}</div>
            <div style="flex:1">
                <div class="trendName">${esc(x.keyword)}</div>
                <div class="trendMeta">
                    <span class="metaChip">${esc(x.theme_info?.label || 'Other')}</span>
                    <span class="metaChip">지속일: ${x.active_days}/7</span>
                </div>
                <div class="bar"><i style="width:${Math.min(100, Number(x.avg_score) || 0)}%"></i></div>
            </div>
            <div class="grow">${fmt(x.total_score)}</div>
        </div>
    `).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderMonthlyTrends(a) {
    $('#monthlyList').innerHTML = a.length ? a.map((x, i) => `
        <div class="trendRow">
            <div class="rankNo">${i + 1}</div>
            <div style="flex:1">
                <div class="trendName">${esc(x.keyword)}</div>
                <div class="trendMeta">
                    <span class="metaChip">${esc(x.theme_info?.label || 'Other')}</span>
                    <span class="metaChip">지속일: ${x.active_days}/30</span>
                </div>
                <div class="bar"><i style="width:${Math.min(100, Number(x.avg_score) || 0)}%"></i></div>
            </div>
            <div class="grow">${fmt(x.total_score)}</div>
        </div>
    `).join('') : `<p class="muted">${tr('noData')}</p>`;
}

// ========== Data Loading ==========
async function loadDailyData() {
    try {
        const d = await api('/api/trends/daily');
        $('#trendCount').textContent = (d.raw_signal_count || 0).toLocaleString();
        $('#topTrend').textContent = d.trends?.[0]?.keyword || '-';
        $('#googleCount').textContent = (d.google?.length || 0);
        $('#catalogDate').textContent = d.date || '';
        renderTrends(d.trends || []);
        renderGoogle(d.google || []);
        renderMatrix(d.trends || []);
        
        // Load themes
        const themes = await api('/api/trends/themes');
        renderThemes(themes.themes || []);
    } catch (e) {
        console.error('Daily load error:', e);
    }
}

async function loadWeeklyData() {
    try {
        const d = await api('/api/trends/weekly');
        renderWeeklyTrends(d.trends || []);
        renderDelta(d.delta || {}, '#weeklyDelta');
    } catch (e) {
        console.error('Weekly load error:', e);
    }
}

async function loadMonthlyData() {
    try {
        const d = await api('/api/trends/monthly');
        renderMonthlyTrends(d.trends || []);
        renderDelta(d.delta || {}, '#monthlyDelta');
    } catch (e) {
        console.error('Monthly load error:', e);
    }
}

function loadPeriodData() {
    if (state.currentPeriod === 'daily') loadDailyData();
    else if (state.currentPeriod === 'weekly') loadWeeklyData();
    else if (state.currentPeriod === 'monthly') loadMonthlyData();
}

// ========== Ranking (Products) ==========
$$('.rankTab').forEach(b => b.onclick = () => {
    state.kind = b.dataset.kind;
    $$('.rankTab').forEach(x => x.classList.toggle('active', x === b));
    loadRanking();
});

function rankCard(p, i) {
    const score = state.kind === 'overall' ? p.overall_score : state.kind === 'olive' ? p.olive_rank : p.daiso_score;
    return `
        <div class="rankRow">
            <div class="rankNo">${i}</div>
            <div style="flex:1">
                <div class="prodName">${esc(p.product_name)}</div>
                <div class="meta">${esc(p.brand || '')} · ${esc(p.category || '')} · ${esc(p.source || '')}</div>
            </div>
            <div class="grow">${state.kind === 'olive' ? '#' + score : (fmt(score) + ' ' + tr('score'))}</div>
        </div>
    `;
}

async function loadRanking() {
    try {
        const d = await api('/api/rankings?kind=' + state.kind + '&limit=50');
        $('#productDate').textContent = d.latest_date || '';
        $('#rankTitle').textContent = tr(state.kind);
        $('#rankingList').innerHTML = d.items.map((p, i) => rankCard(p, i + 1)).join('');
    } catch (e) {
        $('#rankingList').innerHTML = '<p>' + tr('noData') + '</p>';
    }
}

// ========== Products ==========
async function loadCategories() {
    const d = await api('/api/categories');
    $('#category').innerHTML = '<option value="">' + tr('allCategories') + '</option>' + d.items.map(x => `<option value="${esc(x.category)}">${esc(x.category)} (${x.count})</option>`).join('');
}

async function loadProducts(reset = true) {
    if (reset) { state.page = 0; state.products = []; }
    const q = encodeURIComponent(state.q), cat = encodeURIComponent(state.category);
    const d = await api(`/api/products?q=${q}&category=${cat}&limit=200&offset=${state.page * 200}`);
    state.products = reset ? d.items : state.products.concat(d.items);
    state.hasMore = d.has_more;
    $('#productDate').textContent = d.latest_date || $('#productDate').textContent;
    renderProducts();
}

function renderProducts() {
    const a = state.products.slice(0, 200);
    $('#products').innerHTML = a.map(p => `
        <div class="productCard" data-id="${esc(p.product_id)}">
            <div class="source">${esc(p.source || '')}</div>
            <h3>${esc(p.product_name)}</h3>
            <div class="meta">${esc(p.brand || '')} · ${esc(p.category || '')}</div>
            <div class="score">${fmt(p.overall_score)}</div>
            <div class="meta">${tr('score')} · ${p.olive_rank ? 'OY #' + p.olive_rank : ''}${p.daiso_score ? '· Daiso ' + fmt(p.daiso_score) : ''}</div>
            <div class="chips">${arr(p.keywords).slice(0, 5).map(x => `<span class="chip">${esc(x)}</span>`).join('')}</div>
        </div>
    `).join('');
    $$('.productCard').forEach(x => x.onclick = () => openDetail(x.dataset.id));
    $('#loadMore').style.display = state.hasMore ? 'block' : 'none';
}

let timer;
$('#search').addEventListener('input', e => { clearTimeout(timer); state.q = e.target.value; timer = setTimeout(() => loadProducts(), 350); });
$('#category').addEventListener('change', e => { state.category = e.target.value; loadProducts(); });
$('#loadMore').onclick = () => { state.page++; loadProducts(false); };

async function openDetail(id) {
    const d = await api('/api/products/' + encodeURIComponent(id));
    if (!d.found) return;
    const p = d.product;
    $('#detail').innerHTML = `
        <p class="eyebrow">${tr('details')}</p>
        <h2>${esc(p.product_name)}</h2>
        <p class="muted">${esc(p.brand || '')} · ${esc(p.source || '')} · ${esc(p.category || '')}</p>
        <div class="detailGrid">
            ${['product_type', 'ingredients', 'key_ingredients', 'keywords', 'skin_type', 'concerns', 'texture', 'claims'].map(k => `
                <div class="detailItem">
                    <b>${tr(k)}</b>
                    <div>${arr(p[k]).map(x => `<span class="chip">${esc(x)}</span>`).join(' ') || esc(p[k] || tr('noData'))}</div>
                </div>
            `).join('')}
        </div>
        <div class="detailItem" style="margin-top:14px">
            <b>${tr('score')}</b>
            <div style="font-size:30px;font-weight:900">${fmt(p.overall_score)}</div>
            <div class="meta">Olive Young: ${p.olive_rank ? '#' + p.olive_rank : '-'} · Daiso: ${p.daiso_score ? fmt(p.daiso_score) : '-'}</div>
        </div>
        <div class="detailItem" style="margin-top:14px">
            <b>Rank History</b>
            <div class="chips">${d.rankings.slice(0, 20).map(r => `<span class="chip">${esc(r.ranking_date)} · ${esc(r.source)} · #${r.rank_num}</span>`).join('')}</div>
        </div>
    `;
    $('#modal').classList.add('show');
}

function renderAll() {
    renderRankings();
    renderProducts();
}

$('#close').onclick = () => $('#modal').classList.remove('show');
$('#modal').onclick = e => { if (e.target.id === 'modal') $('#modal').classList.remove('show'); };

// ========== Init ==========
applyLang();
loadDailyData();
loadRanking();
loadCategories();
