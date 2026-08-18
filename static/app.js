const API = {
  dashboard: '/api/app/dashboard',
  ai: lang => `/api/app/ai?lang=${lang}`,
  search: q => `/api/app/search?q=${encodeURIComponent(q)}`,
  keyword: k => `/api/app/keyword/${encodeURIComponent(k)}`,
  changes: '/api/app/changes',
  rankingsToday: '/api/catalog/rankings/today',
  products: '/api/catalog/products',
  periodRankings: p => `/api/periods/rankings?period=${p}`,
};

const I18N = {
  ko: { dashboard:'📊 메인', ai:'🤖 AI 트렌드분석', keywordsTab:'🗂️ 키워드별',
    search:'상품명·브랜드 검색',
    rising:'🔥 올리브영 순위 급등',
    trends:'🌿 트렌드 키워드', trendsSub:'키워드를 누르면 매칭 상품이 보여요',
    daiso:'💎 다이소 뷰티 베스트', daisoSub:'리뷰·평점 기반 자체 랭킹',
    rankings:'🏆 전체 상품 랭킹', rankingsSub:'종합·올리브영·다이소',
    all:'종합', olive:'올리브영', daiso:'다이소',
    daily:'일간', weekly:'주간', monthly:'월간', periodLabel:'분석 기간',
    aiTitle:'AI 트렌드 분석', aiSub:'상단에서 기간을 선택하세요',
    aiSummary:'📌 요약', aiEvidence:'🔗 근거', aiPopular:'🛒 인기 상품',
    kwTitle:'🗂️ 키워드별 전체 상품', kwSub:'키워드를 누르면 해당 전체 상품이 보여요',
    other:'기타',
    vsDaily:'어제 대비 랭킹 변동', vsWeekly:'7일 전 대비 랭킹 변동', vsMonthly:'30일 전 대비 랭킹 변동',
    insufficient:'📉 데이터 부족',
    insufficientDesc:'해당 기간 분석을 위한 히스토리 데이터가 아직 충분히 쌓이지 않았어요.' },
  en: { dashboard:'📊 Dashboard', ai:'🤖 AI Trends', keywordsTab:'🗂️ By Keyword',
    search:'Search products, brands',
    rising:'🔥 Olive Young Rising',
    trends:'🌿 Trend Keywords', trendsSub:'Tap a keyword to see matched products',
    daiso:'💎 Daiso Best', daisoSub:'Own ranking by reviews & ratings',
    rankings:'🏆 Top Rankings', rankingsSub:'All · Olive Young · Daiso',
    all:'All', olive:'Olive Young', daiso:'Daiso',
    daily:'Daily', weekly:'Weekly', monthly:'Monthly', periodLabel:'Period',
    aiTitle:'AI Trend Analysis', aiSub:'Select a period above',
    aiSummary:'📌 Summary', aiEvidence:'🔗 Evidence', aiPopular:'🛒 Popular',
    kwTitle:'🗂️ All Products by Keyword', kwSub:'Tap a keyword to view all products',
    other:'Others',
    vsDaily:'Rank change vs yesterday', vsWeekly:'Rank change vs 7 days ago', vsMonthly:'Rank change vs 30 days ago',
    insufficient:'📉 Not enough data',
    insufficientDesc:'Not enough history data for this period yet.' },
  ar: { dashboard:'📊 الرئيسية', ai:'🤖 تحليل AI', keywordsTab:'🗂️ حسب الكلمة',
    search:'ابحث عن منتج أو علامة',
    rising:'🔥 الأكثر صعوداً',
    trends:'🌿 كلمات الاتجاه', trendsSub:'اضغط لعرض المنتجات المطابقة',
    daiso:'💎 أفضل دايسو', daisoSub:'ترتيب خاص حسب التقييمات',
    rankings:'🏆 أفضل الترتيب', rankingsSub:'الكل · أوليف يونغ · دايسو',
    all:'الكل', olive:'أوليف يونغ', daiso:'دايسو',
    daily:'يومي', weekly:'أسبوعي', monthly:'شهري', periodLabel:'الفترة',
    aiTitle:'تحليل الاتجاهات بالذكاء الاصطناعي', aiSub:'اختر الفترة من الأعلى',
    aiSummary:'📌 ملخص', aiEvidence:'🔗 أدلة', aiPopular:'🛒 منتجات شائعة',
    kwTitle:'🗂️ كل المنتجات حسب الكلمة', kwSub:'اضغط لعرض كل المنتجات',
    other:'أخرى',
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
const kwText = p => (F.name(p) + ' ' + F.brand(p) + ' ' + (p.category || '')).toLowerCase();

let currentLang = 'ko', currentPeriod = 'daily', rankFilter = 'all';
let fuse = null, productPool = [], aiData = null, trendItems = [];
let oliveList = [], daisoList = [];

document.addEventListener('DOMContentLoaded', async () => {
  setupTabs(); setupLang(); setupPeriod(); setupFilter(); setupSearch(); renderKeywordChips();
  await Promise.all([loadAI(), loadProductsPool()]);
  await loadDashboard();
});

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(btn.dataset.tab + '-tab').classList.add('active');
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
function setupFilter() {
  document.querySelectorAll('.filter-btn').forEach(btn => btn.addEventListener('click', () => {
    rankFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b === btn));
    renderRankings();
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
      toggleSec('sec-rising', true);
    } else {
      renderRising(data.rising || []);
    }
  } else {
    const [changes, ranks] = await Promise.all([safeJson(API.changes), safeJson(API.rankingsToday)]);
    oliveList = firstList(getList(ranks,'items','rankings')).map(p => ({ ...p, source: F.source(p) || 'oliveyoung' }));
    daisoList = oliveList.filter(p => F.source(p).includes('daiso'));
    renderRising(firstList(getList(changes,'items','changes','rising')));
  }

  renderGrid(document.getElementById('daiso-best'), daisoList.slice(0, 10), p => rankBadgeHtml(p));
  toggleSec('sec-daiso', daisoList.length);
  renderRankings();
  toggleSec('sec-rankings', oliveList.length || daisoList.length);
  renderTrendKeywordsForPeriod();
}
function toggleSec(id, has) { const el = document.getElementById(id); if (el) el.style.display = has ? '' : 'none'; }

async function loadProductsPool() {
  const data = await safeJson(API.products);
  productPool = Array.isArray(data) ? data : firstList(getList(data,'items','products','results'));
  if (window.Fuse && productPool.length) fuse = new Fuse(productPool, { keys: ['product_name','brand'], threshold: 0.35 });
  if (!daisoList.length) {
    daisoList = productPool.filter(p => F.source(p).includes('daiso')).slice(0, 50);
    renderGrid(document.getElementById('daiso-best'), daisoList.slice(0, 10), p => rankBadgeHtml(p));
    toggleSec('sec-daiso', daisoList.length);
  }
  if (!oliveList.length) oliveList = productPool.filter(p => F.source(p).includes('olive'));
}

function parseKeywordsFromSummary(summary) {
  const m = String(summary || '').match(/(?:주요\s*키워드|key\s*keywords?|الكلمات\s*الرئيسية)\s*[:：]\s*([^|]+)/i);
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
      toggleSec('sec-trends', true);
      return;
    }
  }
  drawTrendChips(items);
}
function drawTrendChips(items) {
  document.getElementById('trend-keywords').innerHTML = items.map(k =>
    `<div class="keyword-chip" onclick='onKeywordClick(${JSON.stringify(k.keyword || k.name || k).replace(/'/g,"&#39;")})'>#${esc(k.keyword || k.name || k)}</div>`
  ).join('');
  toggleSec('sec-trends', items.length);
}

function badgeHtml(p) {
  const s = F.source(p);
  return s.includes('daiso') ? '<span class="badge badge-daiso">🔵 다이소</span>'
       : s.includes('olive') ? '<span class="badge badge-olive">🫒 올리브영</span>' : '';
}
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
  toggleSec('sec-rising', items.length);
}
function renderRankings() {
  let items;
  if (rankFilter === 'olive') items = oliveList;
  else if (rankFilter === 'daiso') items = daisoList;
  else items = (oliveList.length || daisoList.length) ? [...oliveList, ...daisoList] : [];
  renderGrid(document.getElementById('all-rankings'), items.slice(0, 30), p => rankBadgeHtml(p));
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
