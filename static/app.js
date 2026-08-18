const API = {
  dashboard: '/api/app/dashboard',
  ai: lang => `/api/app/ai?lang=${lang}`,
  search: q => `/api/app/search?q=${encodeURIComponent(q)}`,
  keyword: k => `/api/app/keyword/${encodeURIComponent(k)}`,
  changes: '/api/app/changes',
  rankingsToday: '/api/catalog/rankings/today',
  products: '/api/catalog/products',
};

const I18N = {
  ko: { dashboard:'📊 대시보드', ai:'🤖 AI 트렌드', ingredients:'🌿 성분별',
    search:'상품명·브랜드·성분 검색 (예: PDRN, 세라마이드)',
    rising:'🔥 올리브영 순위 급등', risingSub:'어제 대비 랭킹 변동',
    trends:'🌿 트렌드 키워드', trendsSub:'키워드를 누르면 매칭 상품이 보여요',
    daiso:'💎 다이소 뷰티 베스트', daisoSub:'가성비 인기 상품',
    rankings:'🏆 전체 상품 킹', rankingsSub:'종합·올리브영·다이소',
    all:'종합', olive:'올리브영', daiso:'다이소',
    aiTitle:'AI 트렌드 분석', aiSub:'기간을 선택하세요',
    daily:'일간', weekly:'주간', monthly:'월간',
    aiSummary:'📌 요약', aiEvidence:'🔗 근거', aiPopular:'🛒 인기 상품',
    ingTitle:'🌿 성분별 상품 보기', ingSub:'성분을 선택하세요' },
  en: { dashboard:'📊 Dashboard', ai:'🤖 AI Trends', ingredients:'🌿 Ingredients',
    search:'Search products, brands, ingredients',
    rising:'🔥 Olive Young Rising', risingSub:'Rank change vs yesterday',
    trends:'🌿 Trend Keywords', trendsSub:'Tap a keyword to see matched products',
    daiso:'💎 Daiso Best', daisoSub:'Popular budget picks',
    rankings:'🏆 Top Rankings', rankingsSub:'All · Olive Young · Daiso',
    all:'All', olive:'Olive Young', daiso:'Daiso',
    aiTitle:'AI Trend Analysis', aiSub:'Select a period',
    daily:'Daily', weekly:'Weekly', monthly:'Monthly',
    aiSummary:'📌 Summary', aiEvidence:'🔗 Evidence', aiPopular:'🛒 Popular products',
    ingTitle:'🌿 Browse by Ingredient', ingSub:'Select an ingredient' },
  ar: { dashboard:'📊 الرئيسية', ai:'🤖 تحليل AI', ingredients:'🌿 المكوّنات',
    search:'ابحث عن منتج أو علامة أو مكوّن',
    rising:'🔥 الأكثر صعوداً', risingSub:'تغيّر الترتيب عن الأمس',
    trends:'🌿 كلمات الاتجاه', trendsSub:'اضغط لعرض المنتجات المطابقة',
    daiso:'💎 أفضل دايسو', daisoSub:'منتجات اقتصادية شائعة',
    rankings:'🏆 أفضل الترتيب', rankingsSub:'الكل · أوليف يونغ · دايسو',
    all:'الكل', olive:'أوليف يونغ', daiso:'دايسو',
    aiTitle:'تحليل الاتجاهات بالذكاء الاصطناعي', aiSub:'اختر الفترة',
    daily:'يومي', weekly:'أسبوعي', monthly:'شهري',
    aiSummary:'📌 ملخص', aiEvidence:'🔗 أدلة', aiPopular:'🛒 منتجات شائعة',
    ingTitle:'🌿 تصفح حسب المكوّن', ingSub:'اختر مكوّناً' }
};

const INGREDIENTS = [
  { label:'PDRN', keys:['pdrn','디엔에이','연어'] },
  { label:'레티놀', keys:['레티놀','retinol'] },
  { label:'세라마이드', keys:['세라마이드','ceramide'] },
  { label:'병풀/시카', keys:['병풀','시카','센텔라','cica','centella'] },
  { label:'나이아신아마이드', keys:['나이아신아마이드','niacinamide'] },
  { label:'히알루론산', keys:['히알루론','hyaluron'] },
  { label:'비타민C', keys:['비타씨','비타민 c','vitamin c','아스코빅'] },
  { label:'기타', keys:[] },
];

const isArr = a => Array.isArray(a) && a.length > 0;
const firstList = (...a) => { for (const x of a) if (isArr(x)) return x; return []; };
const getList = (o, ...ks) => { if (!o || typeof o !== 'object') return []; for (const k of ks) if (isArr(o[k])) return o[k]; return []; };
const esc = s => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const F = {
  name: p => p.product_name || p.name || '',
  brand: p => p.brand || '',
  url: p => p.product_url || p.url || '#',
  source: p => String(p.source || '').toLowerCase(),
  price: p => (p.sale_price ?? p.price ?? null),
  rank: p => (p.rank ?? p.rank_num ?? null),
};

let currentLang = 'ko', currentPeriod = 'daily', rankFilter = 'all';
let fuse = null, productPool = [], aiData = null, trendItems = [];
let allRankings = [], oliveList = [], daisoList = [];

document.addEventListener('DOMContentLoaded', () => {
  setupTabs(); setupLang(); setupPeriod(); setupFilter(); setupSearch(); renderIngredientChips();
  loadDashboard(); loadProductsPool(); loadAI();
});

/* ========== 설정류 ========== */
function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(btn.dataset.tab + '-tab').classList.add('active');
  }));
}
function setupLang() {
  document.querySelectorAll('.lang-btn').forEach(btn => btn.addEventListener('click', () => {
    currentLang = btn.dataset.lang;
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b === btn));
    applyLang(); loadAI();
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
    showPeriod();
  }));
}
function setupFilter() {
  document.querySelectorAll('.filter-btn').forEach(btn => btn.addEventListener('click', () => {
    rankFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b === btn));
    renderRankings();
  }));
}

/* ========== 데이터 ========== */
async function safeJson(url) { try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch (e) { return null; } }

async function loadDashboard() {
  const [dash, changes, ranks] = await Promise.all([
    safeJson(API.dashboard), safeJson(API.changes), safeJson(API.rankingsToday)
  ]);

  const rising = firstList(getList(changes,'items','changes','rising'), getList(dash,'rising_products','rising','changes'));
  renderRising(rising);

  trendItems = firstList(getList(dash,'top_trends','trends','keywords','trend_keywords'));
  renderTrendKeywords(trendItems);

  allRankings = firstList(getList(ranks,'items','rankings'), getList(dash,'top_rankings','rankings'));
  oliveList = allRankings.filter(p => F.source(p).includes('olive'));
  daisoList = allRankings.filter(p => F.source(p).includes('daiso'));
  if (!daisoList.length) daisoList = getList(dash,'daiso_picks','daiso');

  renderGrid(document.getElementById('daiso-best'), daisoList.slice(0, 10), p => rankBadgeHtml(p));
  toggleSec('sec-daiso', daisoList.length);

  renderRankings();
  toggleSec('sec-rankings', allRankings.length || daisoList.length);
}
function toggleSec(id, has) { const el = document.getElementById(id); if (el) el.style.display = has ? '' : 'none'; }

async function loadProductsPool() {
  const data = await safeJson(API.products);
  productPool = Array.isArray(data) ? data : firstList(getList(data,'items','products','results'));
  if (window.Fuse && productPool.length) fuse = new Fuse(productPool, { keys: ['product_name','brand'], threshold: 0.35 });
}

async function loadAI() {
  document.getElementById('ai-summary').textContent = '...';
  const data = await safeJson(API.ai(currentLang));
  if (data) { aiData = data; showPeriod(); document.getElementById('ai-popular').textContent = data.popular || ''; }
}
function showPeriod() {
  if (!aiData) return;
  const d = aiData[currentPeriod] || {};
  document.getElementById('ai-summary').textContent = d.summary || '-';
  document.getElementById('ai-evidence').innerHTML = firstList(d.evidence).map(e => `<li>${esc(typeof e === 'string' ? e : JSON.stringify(e))}</li>`).join('');
}

/* ========== 렌더링 ========== */
function badgeHtml(p) {
  const s = F.source(p);
  return s.includes('daiso') ? '<span class="badge badge-daiso">🔵 다이소</span>'
       : s.includes('olive') ? '<span class="badge badge-olive">🫒 올리브영</span>' : '';
}
/* ✅ 랭킹 배지: 다이소는 자체 랭킹(수집 순서), 올리브영은 실제 랭킹 */
function rankBadgeHtml(p) {
  const s = F.source(p);
  if (s.includes('daiso')) return `<div class="rank-no daiso">🔵 다이소 ${daisoList.indexOf(p) + 1}위</div>`;
  if (s.includes('olive')) return `<div class="rank-no olive">🫒 올리브영 ${F.rank(p) || (oliveList.indexOf(p) + 1)}위</div>`;
  return '';
}
function cardHtml(p, topHtml = '') {
  const price = F.price(p);
  return `<div class="product-card" onclick="window.open('${esc(F.url(p))}','_blank')">
    ${topHtml || badgeHtml(p)}
    <div class="brand">${esc(F.brand(p))}</div>
    <div class="name">${esc(F.name(p))}</div>
    <div class="price">${price != null ? Number(price).toLocaleString() + '원' : ''}</div>
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
  toggleSec('sec-rising', items.length);
}
/* ✅ 점수() 제거, 키워드만 */
function renderTrendKeywords(items) {
  document.getElementById('trend-keywords').innerHTML = items.map((k, i) =>
    `<div class="keyword-chip" onclick="onKeywordClick(${i})">#${esc(k.keyword || k.name || k)}</div>`).join('');
  toggleSec('sec-trends', items.length);
}
/* ✅ 종합/올리브영/다이소 필터 */
function renderRankings() {
  let items;
  if (rankFilter === 'olive') items = oliveList;
  else if (rankFilter === 'daiso') items = daisoList;
  else items = [...oliveList, ...daisoList].length ? [...oliveList, ...daisoList] : allRankings;
  renderGrid(document.getElementById('all-rankings'), items.slice(0, 30), p => rankBadgeHtml(p));
}

async function onKeywordClick(i) {
  const item = trendItems[i] || {};
  const kw = item.keyword || item.name || '';
  let products = firstList(item.products);
  if (!products.length) {
    const d = await safeJson(API.keyword(kw));
    products = firstList(getList(d,'products','items','results'));
  }
  document.getElementById('keyword-match-title').textContent = `🌿 #${kw}`;
  renderGrid(document.getElementById('keyword-match-grid'), products);
  const sec = document.getElementById('keyword-match');
  sec.style.display = 'block'; sec.scrollIntoView({ behavior: 'smooth' });
}
function closeKeywordMatch() { document.getElementById('keyword-match').style.display = 'none'; }

/* ========== 검색 ========== */
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

/* ========== 성분별 ========== */
function renderIngredientChips() {
  document.getElementById('ingredient-chips').innerHTML = INGREDIENTS.map((ing, i) =>
    `<div class="keyword-chip" onclick="onIngredientClick(${i})">${esc(ing.label)}</div>`).join('');
}
function onIngredientClick(i) {
  const ing = INGREDIENTS[i];
  const allKeys = INGREDIENTS.slice(0, -1).flatMap(x => x.keys);
  const match = p => {
    const n = (F.name(p) + ' ' + F.brand(p)).toLowerCase();
    return ing.keys.some(k => n.includes(k.toLowerCase()));
  };
  const items = ing.keys.length ? productPool.filter(match)
    : productPool.filter(p => { const n = (F.name(p) + ' ' + F.brand(p)).toLowerCase(); return !allKeys.some(k => n.includes(k.toLowerCase())); });
  renderGrid(document.getElementById('ingredient-results'), items.slice(0, 30), p => rankBadgeHtml(p));
}
