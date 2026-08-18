const API = {
  dashboard: '/api/app/dashboard',
  ai: lang => `/api/app/ai?lang=${lang}`,
  search: q => `/api/app/search?q=${encodeURIComponent(q)}`,
  keyword: k => `/api/app/keyword/${encodeURIComponent(k)}`,
  changes: '/api/app/changes',
  rankingsToday: '/api/catalog/rankings/today',
  products: '/api/catalog/products?limit=20000',
  fullProducts: '/api/periods/products',
  periodRankings: p => `/api/periods/rankings?period=${p}`,
};

const I18N = {
  ko: { dashboard:'📊 대시보드', ai:'🤖 AI 트렌드', keywordsTab:'🗂️ 키워드별', allProducts:'🛍️ 전체상품',
    search:'상품명·브랜드 검색',
    rising:'🔥 올리브영 순위 급등',
    daisoSpot:'💎 다이소 주목 상품', daisoSpotSub:'평점·리뷰·신상 기반', seeAll:'전체 보기 ➜',
    trends:'🌿 트렌드 키워드', trendsSub:'키워드를 누르면 매칭 상품이 보여요',
    rankings:'🏆 전체 랭킹', rankingsSub:'올리브영·다이소 통합 TOP 30',
    oliveRankings:'🫒 올리브영 랭킹', oliveRankSub:'판매 랭킹 TOP 30',
    daisoRankings:'🔵 다이소 랭킹', daisoRankSub:'리뷰·평점 기반 자체 랭킹 TOP 30',
    daily:'일간', weekly:'주간', monthly:'월간',
    aiTitle:'AI 트렌드 분석', aiSub:'서구권 소셜·검색 트렌드 기반',
    aiSummary:'📌 요약', aiEvidence:'🔗 근거', aiPopular:'🛒 인기 키워드',
    kwTitle:'🗂️ 키워드별 전체 상품', kwSub:'키워드를 누르면 해당 전체 상품이 보여요',
    allProductsSub:'대카테고리별 · 인기순 정렬', other:'기타',
    vsDaily:'어제 대비 랭킹 변동', vsWeekly:'7일 전 대비 랭킹 변동', vsMonthly:'30일 전 대비 랭킹 변동',
    insufficient:'📉 데이터 부족',
    insufficientDesc:'해당 기간 분석을 위한 히스토리 데이터가 아직 충분히 쌓이지 않았어요.' },
  en: { dashboard:'📊 Dashboard', ai:'🤖 AI Trends', keywordsTab:'🗂️ By Keyword', allProducts:'🛍️ All Products',
    search:'Search products, brands',
    rising:'🔥 Olive Young Rising',
    daisoSpot:'💎 Daiso Spotlight', daisoSpotSub:'By ratings · reviews · new arrivals', seeAll:'See all ➜',
    trends:'🌿 Trend Keywords', trendsSub:'Tap a keyword to see matched products',
    rankings:'🏆 Overall Rankings', rankingsSub:'Olive Young · Daiso TOP 30',
    oliveRankings:'🫒 Olive Young Rankings', oliveRankSub:'Sales ranking TOP 30',
    daisoRankings:'🔵 Daiso Rankings', daisoRankSub:'Own ranking by reviews & ratings TOP 30',
    daily:'Daily', weekly:'Weekly', monthly:'Monthly',
    aiTitle:'AI Trend Analysis', aiSub:'Based on Western social & search trends',
    aiSummary:'📌 Summary', aiEvidence:'🔗 Evidence', aiPopular:'🛒 Popular keywords',
    kwTitle:'🗂️ All Products by Keyword', kwSub:'Tap a keyword to view all products',
    allProductsSub:'By category · sorted by popularity', other:'Others',
    vsDaily:'Rank change vs yesterday', vsWeekly:'Rank change vs 7 days ago', vsMonthly:'Rank change vs 30 days ago',
    insufficient:'📉 Not enough data',
    insufficientDesc:'Not enough history data for this period yet.' },
  ar: { dashboard:'📊 الرئيسية', ai:'🤖 تحليل AI', keywordsTab:'🗂️ حسب الكلمة', allProducts:'🛍️ كل المنتجات',
    search:'ابحث عن منتج أو علامة',
    rising:'🔥 الأكثر صعوداً',
    daisoSpot:'💎 منتجات دايسو المميزة', daisoSpotSub:'حسب التقييمات والمراجعات والجديد', seeAll:'عرض الكل ➜',
    trends:'🌿 كلمات الاتجاه', trendsSub:'اضغط لعرض المنتجات المطابقة',
    rankings:'🏆 الترتيب العام', rankingsSub:'أوليف يونغ · دايسو TOP 30',
    oliveRankings:'🫒 ترتيب أوليف يونغ', oliveRankSub:'ترتيب المبيعات TOP 30',
    daisoRankings:'🔵 ترتيب دايسو', daisoRankSub:'ترتيب خاص حسب التقييمات TOP 30',
    daily:'يومي', weekly:'أسبوعي', monthly:'شهري',
    aiTitle:'تحليل الاتجاهات بالذكاء الاصطناعي', aiSub:'بناءً على اتجاهات الغرب',
    aiSummary:'📌 ملخص', aiEvidence:'🔗 أدلة', aiPopular:'🛒 كلمات شائعة',
    kwTitle:'🗂️ كل المنتجات حسب الكلمة', kwSub:'اضغط لعرض كل المنتجات',
    allProductsSub:'حسب الفئة · مرتبة بالشعبية', other:'أخرى',
    vsDaily:'تغيّر الترتيب عن الأمس', vsWeekly:'تغيّر الترتيب عن ٧ أيام', vsMonthly:'تغيّر الترتيب عن ٣٠ يوماً',
    insufficient:'📉 بيانات غير كافية',
    insufficientDesc:'لا توجد بيانات تاريخية كافية لهذه الفترة بعد.' }
};

const isArr = a => Array.isArray(a) && a.length > 0;
const firstList = (...a) => { for (const x of a) if (isArr(x)) return x; return []; };
const getList = (o, ...ks) => { if (!o || typeof o !== 'object') return []; for (const k of ks) if (isArr(o[k])) return o[k]; return []; };
const esc = s => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const F = {
  name: p => p.product_name || p.name || '',
  brand: p => p.brand || '',
  url: p => p.product_url || p.url || '#',
  source: p => {
    let s = String(p.source || '').toLowerCase();
    if (s) return s;
    const id = String(p.product_id || '').toUpperCase();
    const url = String(p.product_url || p.url || '').toLowerCase();
    if (id.startsWith('OY') || url.includes('oliveyoung')) return 'oliveyoung';
    if (id.startsWith('DS') || url.includes('daiso')) return 'daiso';
    return '';
  },
  price: p => {
    let v = p.sale_price ?? p.price ?? null;
    if (v == null) return null;
    v = Number(String(v).replace(/[^0-9]/g, ''));
    if (!v || v === 999) return null;
    return v;
  },
  rank: p => (p.rank ?? p.rank_num ?? null),
};
const kwText = p => (F.name(p) + ' ' + F.brand(p) + ' ' + (p.category || '') + ' ' + (p.parent_category || '')).toLowerCase();

let currentLang = 'ko', currentPeriod = 'daily';
let fuse = null, productPool = [], aiData = null, trendItems = [];
let oliveList = [], daisoList = [], oliveRankList = [], daisoRankList = [];

document.addEventListener('DOMContentLoaded', async () => {
  setupTabs(); setupLang(); setupPeriod(); setupSearch(); renderKeywordChips();
  await Promise.all([loadAI(), loadProductsPool()]);
  await loadDashboard();
});

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(btn.dataset.tab + '-tab').classList.add('active');
    const hide = (btn.dataset.tab === 'keywords' || btn.dataset.tab === 'allproducts');
    document.querySelector('.global-period').style.display = hide ? 'none' : 'flex';
  }));
}
function setupLang() {
  document.querySelectorAll('.lang-btn').forEach(btn => btn.addEventListener('click', async () => {
    currentLang = btn.dataset.lang;
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b === btn));
    applyLang(); renderKeywordChips();
    await loadAI(); showPeriod(); renderTrendKeywordsForPeriod();
  }));
}
function applyLang() {
  const t = I18N[currentLang] || I18N.ko;
  document.querySelectorAll('[data-i18n]').forEach(el => { if (t[el.dataset.i18n]) el.textContent = t[el.dataset.i18n]; });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { if (t[el.dataset.i18nPh]) el.placeholder = t[el.dataset.i18nPh]; });
  document.documentElement.lang = currentLang;
  document.documentElement.dir = currentLang === 'ar' ? 'rtl' : 'ltr';
}
function setupPeriod() {
  document.querySelectorAll('.period-btn').forEach(btn => btn.addEventListener('click', () => {
    currentPeriod = btn.dataset.period;
    document.querySelectorAll('.period-btn').forEach(b => b.classList.toggle('active', b === btn));
    showPeriod(); loadDashboard();
  }));
}

async function safeJson(url) { try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch (e) { return null; } }

async function loadAI() {
  const data = await safeJson(API.ai(currentLang));
  if (data) { aiData = data; showPeriod(); document.getElementById('ai-popular').textContent = data.popular || ''; }
}
function showPeriod() {
  const t = I18N[currentLang] || I18N.ko;
  const d = (aiData || {})[currentPeriod];
  if (!d || !d.summary) {
    document.getElementById('ai-summary').textContent = `${t.insufficient} - ${t.insufficientDesc}`;
    document.getElementById('ai-evidence').innerHTML = '';
    return;
  }
  document.getElementById('ai-summary').textContent = d.summary;
  document.getElementById('ai-evidence').innerHTML = firstList(d.evidence).map(e => `<li>${esc(typeof e === 'string' ? e : JSON.stringify(e))}</li>`).join('');
}

async function loadDashboard() {
  const t = I18N[currentLang] || I18N.ko;
  document.getElementById('rising-sub').textContent = t['vs' + currentPeriod.charAt(0).toUpperCase() + currentPeriod.slice(1)] || '';

  const data = await safeJson(API.periodRankings(currentPeriod));
  if (data && (isArr(data.rankings) || isArr(data.daiso) || data.insufficient !== undefined)) {
    oliveList = (data.rankings || []).map(p => ({ ...p, source: 'oliveyoung' }));
    daisoList = (data.daiso || []).map(p => ({ ...p, source: 'daiso' }));
    if (data.insufficient) {
      document.getElementById('olive-rising').innerHTML = `<p class="insufficient">📉 ${esc(t.insufficient)} - ${esc(t.insufficientDesc)}</p>`;
    } else {
      renderRising(data.rising || []);
    }
  } else {
    const [changes, ranks] = await Promise.all([safeJson(API.changes), safeJson(API.rankingsToday)]);
    oliveList = firstList(getList(ranks,'items','rankings')).map(p => ({ ...p, source: F.source(p) || 'oliveyoung' }));
    daisoList = oliveList.filter(p => F.source(p).includes('daiso'));
    renderRising(firstList(getList(changes,'items','changes','rising')));
  }

  renderDaisoSpot();
  renderBottomRankings();
  renderTrendKeywordsForPeriod();
}

async function loadProductsPool() {
  let data = await safeJson(API.fullProducts);
  if (!data || !isArr(data.items)) data = await safeJson(API.products);
  productPool = (data && isArr(data.items)) ? data.items : (Array.isArray(data) ? data : []);
  if (window.Fuse && productPool.length) fuse = new Fuse(productPool, { keys: ['product_name','brand'], threshold: 0.35 });
  renderAllProducts();
}

/* ✅ 우측: 다이소 주목 상품 (신상 > 평점 > 리뷰순) */
function renderDaisoSpot() {
  const spot = productPool.filter(p => F.source(p).includes('daiso'))
    .sort((a,b) => ((b.is_new?1:0)-(a.is_new?1:0)) || ((b.rating||0)-(a.rating||0)) || ((b.review_count||0)-(a.review_count||0)))
    .slice(0, 10);
  renderGrid(document.getElementById('daiso-spot'), spot, p => {
    if (p.is_new) return '<div class="rank-no daiso">🆕 신상</div>';
    if (p.rating) return `<div class="rank-no daiso">⭐ ${p.rating}</div>`;
    return '';
  });
}
/* ✅ "전체 보기" → 하단 다이소 랭킹으로 스크롤 */
function showDaisoRankings() {
  document.getElementById('sec-daiso-rankings').scrollIntoView({ behavior: 'smooth' });
}

/* ✅ 하단 랭킹 3종 (각 30위) */
function renderBottomRankings() {
  oliveRankList = productPool.filter(p => F.source(p).includes('olive') && p.rank)
    .sort((a,b) => a.rank - b.rank).slice(0, 30);
  daisoRankList = productPool.filter(p => F.source(p).includes('daiso'))
    .sort((a,b) => (b.daiso_score||0) - (a.daiso_score||0)).slice(0, 30);
  const all = [...oliveRankList, ...daisoRankList]
    .sort((a,b) => (b.pop||0) - (a.pop||0)).slice(0, 30);
  renderGrid(document.getElementById('all-rankings'), all, p => rankBadgeHtml(p));
  renderGrid(document.getElementById('olive-rankings'), oliveRankList, p => rankBadgeHtml(p));
  renderGrid(document.getElementById('daiso-rankings'), daisoRankList, p => rankBadgeHtml(p));
}

function parseKeywordsFromSummary(summary) {
  const m = String(summary || '').match(/(?:주요\s*키워드|key\s*keywords?|الكلمات\s*الرئيسية|서구권\s*주요\s*트렌드)\s*[:：]\s*([^|.]+)/i);
  if (!m) return [];
  return m[1].split(/[,،]/).map(s => s.trim()).filter(Boolean).map(k => ({ keyword: k }));
}
function renderTrendKeywordsForPeriod() {
  const t = I18N[currentLang] || I18N.ko;
  let items = [];
  if (currentPeriod === 'daily') {
    items = trendItems;
    if (!items.length && aiData) items = parseKeywordsFromSummary((aiData.daily || {}).summary);
    if (!items.length) {
      safeJson(API.dashboard).then(d => {
        trendItems = firstList(getList(d,'top_trends','trends','keywords','trend_keywords'));
        drawTrendChips(trendItems);
      });
      return;
    }
  } else {
    items = parseKeywordsFromSummary((aiData?.[currentPeriod] || {}).summary);
    if (!items.length) {
      document.getElementById('trend-keywords').innerHTML = `<p class="insufficient">📉 ${esc(t.insufficient)} - ${esc(t.insufficientDesc)}</p>`;
      return;
    }
  }
  drawTrendChips(items);
}
function drawTrendChips(items) {
  document.getElementById('trend-keywords').innerHTML = items.map(k =>
    `<div class="keyword-chip" onclick='onKeywordClick(${JSON.stringify(k.keyword || k.name || k).replace(/'/g,"&#39;")})'>#${esc(k.keyword || k.name || k)}</div>`
  ).join('');
}

function badgeHtml(p) {
  const s = F.source(p);
  return s.includes('daiso') ? '<span class="badge badge-daiso">🔵 다이소</span>'
       : s.includes('olive') ? '<span class="badge badge-olive">🫒 올리브영</span>' : '';
}
function rankBadgeHtml(p) {
  const s = F.source(p);
  if (s.includes('olive')) {
    const r = F.rank(p) || (oliveRankList.indexOf(p) >= 0 ? oliveRankList.indexOf(p) + 1 : null);
    if (r && r > 0) return `<div class="rank-no olive">🫒 올리브영 ${r}위</div>`;
    return '';
  }
  if (s.includes('daiso')) {
    const i = daisoRankList.indexOf(p);
    if (i >= 0) return `<div class="rank-no daiso">🔵 다이소 ${i + 1}위</div>`;
    return '';
  }
  return '';
}
function cardHtml(p, topHtml = '') {
  const price = F.price(p);
  return `<div class="product-card" onclick="window.open('${esc(F.url(p))}','_blank')">
    ${topHtml || badgeHtml(p)}
    <div class="brand">${esc(F.brand(p))}</div>
    <div class="name">${esc(F.name(p))}</div>
    <div class="price">${price != null ? Number(price).toLocaleString() + '원' : '<span style="color:#999;font-size:12px;">가격 확인</span>'}</div>
  </div>`;
}
function renderGrid(el, items, topFn) {
  el.innerHTML = items.map(p => cardHtml(p, topFn ? topFn(p) : '')).join('') || '<p class="loading">데이터 없음</p>';
}
function renderRising(items) {
  document.getElementById('olive-rising').innerHTML = items.map(p => {
    const ch = p.change ?? ((p.previous_rank ?? 0) - (F.rank(p) ?? 0));
    const html = (ch > 0 ? `<div class="rank-change-up">🚀 +${ch}계단</div>` : ch < 0 ? `<div class="rank-change-down">📉 ${ch}계단</div>` : '');
    return cardHtml(p, rankBadgeHtml(p) + html);
  }).join('') || '<p class="loading">데이터 없음</p>';
}

/* 전체상품 탭 */
function renderAllProducts() {
  const order = ['스킨케어','마스크팩','클렌징','선케어','메이크업','맨즈케어','향수'];
  const groups = {};
  productPool.forEach(p => {
    const g = p.parent_category || p.category || '기타';
    (groups[g] = groups[g] || []).push(p);
  });
  const keys = [
    ...order.filter(k => groups[k]),
    ...Object.keys(groups).filter(k => !order.includes(k)).sort()
  ];
  const container = document.getElementById('allproducts-container');
  if (!container) return;
  container.innerHTML = keys.map(k => {
    const items = groups[k].sort((a,b) => (b.pop || 0) - (a.pop || 0)).slice(0, 12);
    return `<div class="cat-section">
      <h3 class="cat-title">${esc(k)} <span class="cat-count">${groups[k].length}개</span></h3>
      <div class="product-grid">${items.map(p => cardHtml(p, rankBadgeHtml(p))).join('')}</div>
    </div>`;
  }).join('') || '<p class="loading">데이터 없음</p>';
}

async function onKeywordClick(kw) {
  let products = [];
  const t = trendItems.find(x => (x.keyword || x.name) === kw);
  if (t) products = firstList(t.products);
  if (!products.length) {
    const d = await safeJson(API.keyword(kw));
    products = firstList(getList(d,'products','items','results'));
  }
  if (!products.length && fuse) products = fuse.search(kw).slice(0, 20).map(r => r.item);
  document.getElementById('keyword-match-title').textContent = `🌿 #${kw}`;
  renderGrid(document.getElementById('keyword-match-grid'), products);
  const sec = document.getElementById('keyword-match');
  sec.style.display = 'block'; sec.scrollIntoView({ behavior: 'smooth' });
}
function closeKeywordMatch() { document.getElementById('keyword-match').style.display = 'none'; }

function setupSearch() {
  const input = document.getElementById('searchInput');
  const box = document.getElementById('searchSuggestions');
  input.addEventListener('input', () => {
    const v = input.value.trim();
    if (!v || !fuse) { box.style.display = 'none'; return; }
    const res = fuse.search(v).slice(0, 6);
    if (!res.length) { box.style.display = 'none'; return; }
    box.innerHTML = res.map(r => `<div class="suggestion-item" onclick="doSearch('${esc(F.name(r.item)).replace(/'/g,'')}')">
      <div><div class="s-name">${esc(F.name(r.item))}</div><div class="s-brand">${esc(F.brand(r.item))}</div></div>
      ${badgeHtml(r.item)}</div>`).join('');
    box.style.display = 'block';
  });
  input.addEventListener('keydown', e => { if (e.key === 'Enter') { box.style.display = 'none'; doSearch(input.value.trim()); } });
  document.addEventListener('click', e => { if (!e.target.closest('.search-wrapper')) box.style.display = 'none'; });
}
async function doSearch(q) {
  if (!q) return;
  document.getElementById('searchSuggestions').style.display = 'none';
  const sec = document.getElementById('search-results');
  sec.style.display = 'block';
  document.getElementById('search-results-title').textContent = `🔎 "${q}"`;
  const grid = document.getElementById('search-results-grid');
  grid.innerHTML = '<p class="loading">검색 중...</p>';
  const data = await safeJson(API.search(q));
  let items = firstList(getList(data,'items','products','results'));
  if (!items.length && fuse) items = fuse.search(q).slice(0, 20).map(r => r.item);
  renderGrid(grid, items);
  sec.scrollIntoView({ behavior: 'smooth' });
}
function closeSearchResults() { document.getElementById('search-results').style.display = 'none'; }

function renderKeywordChips() {
  const lang = currentLang;
  const t = I18N[lang] || I18N.ko;
  document.getElementById('keyword-chips').innerHTML =
    KEYWORDS.map((k, i) => `<div class="keyword-chip" onclick="onKeywordTabClick(${i})">${esc(keywordLabel(k, lang))}</div>`).join('') +
    `<div class="keyword-chip other-chip" onclick="onKeywordTabClick(-1)">${esc(t.other)}</div>`;
}
function onKeywordTabClick(i) {
  let items;
  if (i >= 0) items = productPool.filter(p => matchKeywordText(kwText(p), KEYWORDS[i]));
  else items = productPool.filter(p => !KEYWORDS.some(kw => matchKeywordText(kwText(p), kw)));
  renderGrid(document.getElementById('keyword-results'), items.slice(0, 60), p => rankBadgeHtml(p));
}
