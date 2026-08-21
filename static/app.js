const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const state = { lang:'ko', kind:'overall', page:0, q:'', category:'', products:[], currentPeriod:'daily', hasMore:false, initialLoad:80, loadMoreStep:50 };
let SUGGESTIONS = [];

const T = {
ko:{navTrend:'트렌드',navProducts:'상품',eyebrow:'K-BEAUTY MARKET SIGNALS',trendTitle:'오늘의 K-Beauty 트렌드',trendSub:'검색·소셜·지역 신호를 기반으로 시장의 흐름을 봅니다.',rising:'🔥 상승 트렌드',trendMatrix:'📈 트렌드 점수',themeRollup:'🧩 테마별 트렌드',daily:'일간',weekly:'주간',monthly:'월간',weeklyChanges:'🔄 이번 주 핵심 변화',weeklyTop:'🏆 주간 TOP 트렌드',monthlyChanges:'🔄 이번 달 핵심 변화',monthlyTop:'🏆 월간 TOP 트렌드',newEntries:'🆕 신규 진입',risingRank:'📈 상승',fallingRank:'📉 하락',changeTitle:'▲▼ 랭킹 변동',changeSub:'어제 대비 랭킹 변화',productTitle:'상품 랭킹 & 전체 카탈로그',productSub:'올리브영·다이소·자체 종합점수로 상품의 시장 위치를 비교합니다.',overall:'종합랭킹',olive:'올리브영',daiso:'다이소',change:'▲▼ 변동',scoreDesc:'(올리브영 순위 + 트렌드 + 리뷰 종합 점수 기준)',catalog:'🛍️ 전체 상품 카탈로그',catalogSub:'카테고리·성분·키워드로 전체 상품을 탐색합니다.',searchPh:'상품명·브랜드·성분 검색 (예: 레티놀 세럼)',allCategories:'전체 카테고리',loadMore:'더 보기 (50)',rank:'랭크',source:'채널',details:'상품 상세',ingredients:'성분',product_type:'제품 유형',keywords:'키워드',skin_type:'피부 타입',concerns:'고민',texture:'제형',key_ingredients:'주요 성분',claims:'클레임',noData:'데이터 없음',scoreNone:'데이터 부족',mallOlive:'올영',mallDaiso:'다이소',new:'신규',platforms:'플랫폼',days:'지속일'},
en:{navTrend:'Trends',navProducts:'Products',eyebrow:'K-BEAUTY MARKET SIGNALS',trendTitle:"Today's K-Beauty Trends",trendSub:'Read market flow from search, social and regional signals.',rising:'🔥 Rising Trends',trendMatrix:'📈 Trend Score',themeRollup:'🧩 Theme Rollup',daily:'Daily',weekly:'Weekly',monthly:'Monthly',weeklyChanges:'🔄 Key Changes This Week',weeklyTop:'🏆 Weekly TOP Trends',monthlyChanges:'🔄 Key Changes This Month',monthlyTop:'🏆 Monthly TOP Trends',newEntries:'🆕 New Entries',risingRank:'📈 Rising',fallingRank:'📉 Falling',changeTitle:'▲▼ Rank Changes',changeSub:'vs yesterday',productTitle:'Product Rankings & Full Catalog',productSub:'Compare market position using Olive Young, Daiso and a unified score.',overall:'Overall',olive:'Olive Young',daiso:'Daiso',change:'▲▼ Changes',scoreDesc:'(Composite: rank + trend + reviews)',catalog:'🛍️ Full Product Catalog',catalogSub:'Explore products by category, ingredients and keywords.',searchPh:'Search (e.g., retinol serum)',allCategories:'All categories',loadMore:'Load more (50)',rank:'Rank',source:'Channel',details:'Product Details',ingredients:'Ingredients',product_type:'Product Type',keywords:'Keywords',skin_type:'Skin Type',concerns:'Concerns',texture:'Texture',key_ingredients:'Key Ingredients',claims:'Claims',noData:'No data',scoreNone:'Not enough data',mallOlive:'OY',mallDaiso:'Daiso',new:'New',platforms:'Platforms',days:'Days'},
ar:{navTrend:'الاتجاهات',navProducts:'المنتجات',eyebrow:'K-BEAUTY MARKET SIGNALS',trendTitle:'اتجاهات K-Beauty اليوم',trendSub:'اقرأ حركة السوق من إشارات البحث والتواصل والمناطق.',rising:'🔥 الاتجاهات الصاعدة',trendMatrix:'📈 درجات الاتجاه',themeRollup:'🧩 ملخص الثيمات',daily:'يومي',weekly:'أسبوعي',monthly:'شهري',weeklyChanges:'🔄 أهم تغييرات الأسبوع',weeklyTop:'🏆 أفضل اتجاهات الأسبوع',monthlyChanges:'🔄 أهم تغييرات الشهر',monthlyTop:'🏆 أفضل اتجاهات الشهر',newEntries:'🆕 جديد',risingRank:'📈 صاعد',fallingRank:'📉 هابط',changeTitle:'▲▼ تغييرات الترتيب',changeSub:'مقارنة بالأمس',productTitle:'ترتيب المنتجات والكتالوج',productSub:'قارن موقع المنتج باستخدام Olive Young وDaiso والدرجة الموحدة.',overall:'الترتيب العام',olive:'Olive Young',daiso:'Daiso',change:'▲▼ تغييرات',scoreDesc:'(درجة مركبة)',catalog:'🛍️ كتالوج المنتجات',catalogSub:'استكشف المنتجات حسب الفئة والمكونات.',searchPh:'ابحث (مثال: سيروم الريتينول)',allCategories:'كل الفئات',loadMore:'عرض المزيد (50)',rank:'الترتيب',source:'القناة',details:'تفاصيل المنتج',ingredients:'المكونات',product_type:'نوع المنتج',keywords:'كلمات مفتاحية',skin_type:'نوع البشرة',concerns:'المشاكل',texture:'القوام',key_ingredients:'المكونات الرئيسية',claims:'الادعاءات',noData:'لا توجد بيانات',scoreNone:'بيانات غير كافية',mallOlive:'OY',mallDaiso:'Daiso',new:'جديد',platforms:'منصات',days:'أيام'}
};

const THEME_T = {
ko:{barrier_soothing:'장벽·진정',sun_protection:'자외선 차단',acne_pore:'여드름·모공',brightening_pigment:'미백·색소',antiaging_regeneration:'안티에이징·재생',hydration:'수분·보습',other:'기타'},
en:{barrier_soothing:'Barrier·Soothing',sun_protection:'Sun Protection',acne_pore:'Acne·Pore',brightening_pigment:'Brightening',antiaging_regeneration:'Anti-aging',hydration:'Hydration',other:'Other'},
ar:{barrier_soothing:'حاجز·تهدئة',sun_protection:'حماية الشمس',acne_pore:'حب الشباب',brightening_pigment:'تفتيح',antiaging_regeneration:'مكافحة الشيخوخة',hydration:'ترطيب',other:'أخرى'}
};

function tr(k){ return T[state.lang][k] || T.en[k] || k; }
function themeT(k){ return (THEME_T[state.lang]||{})[k] || THEME_T.en[k] || k; }
// 언어 토글에 맞춰 상품명을 한글/영문으로 전환. 영문 번역이 없으면 한글로 폴백.
function pname(p){ return (state.lang !== 'ko' && p.product_name_en) ? p.product_name_en : p.product_name; }
// 브랜드/카테고리도 동일하게 전환 (term_translations 캐시 기반, 없으면 한글 폴백)
function bname(p){ return (state.lang !== 'ko' && p.brand_en) ? p.brand_en : p.brand; }
function cname(p){ return (state.lang !== 'ko' && p.category_en) ? p.category_en : p.category; }
function esc(x){ return String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function arr(v){ if(!v) return []; if(Array.isArray(v)) return v; try{ const x=JSON.parse(v); if(Array.isArray(x)) return x; }catch{} return String(v).split(/[,|;\n]+/).map(x=>x.trim()).filter(Boolean); }
async function api(u){ const r = await fetch(u); if(!r.ok) throw Error(r.status); return r.json(); }
const fmt = x => Number(x||0).toFixed(1);

function applyLang(){
  document.documentElement.lang = state.lang;
  document.body.classList.toggle('rtl', state.lang==='ar');
  $$('[data-t]').forEach(e => e.textContent = tr(e.dataset.t));
  $$('[data-ph]').forEach(e => e.placeholder = tr(e.dataset.ph));
  renderAll();
}

$$('.langs button').forEach(b => b.onclick = () => { state.lang = b.dataset.lang; applyLang(); });
$$('.nav').forEach(b => b.onclick = () => {
  const p = b.dataset.page;
  $$('.nav').forEach(x => x.classList.toggle('active', x===b));
  $$('.page').forEach(x => x.classList.remove('active'));
  $('#'+p+'Page').classList.add('active');
  if (p==='products' && !state.products.length) loadProducts();
});
$$('.periodTab').forEach(b => b.onclick = () => {
  state.currentPeriod = b.dataset.period;
  $$('.periodTab').forEach(x => x.classList.toggle('active', x===b));
  $$('.periodContent').forEach(x => x.classList.remove('active'));
  $('#'+state.currentPeriod+'Content').classList.add('active');
  loadPeriodData();
});
$$('.toggleHead').forEach(head => head.addEventListener('click', () => head.closest('.panel').classList.toggle('collapsed')));

function renderTrends(a){
  $('#trendList').innerHTML = (a && a.length) ? a.map((x,i) => {
    const chips = [];
    if (!x.has_history) chips.push(`<span class="metaChip chipNew">✨ ${tr('new')}</span>`);
    if (x.theme && x.theme !== 'other') chips.push(`<span class="metaChip">${esc(themeT(x.theme))}</span>`);
    chips.push(`<span class="metaChip">${tr('platforms')}: ${Math.max(1, Math.round((x.cross_platform_score||0)/33.3))}</span>`);
    return `<div class="trendRow"><div class="rankNo">${i+1}</div><div class="rankBody"><div class="rankNameLine"><span class="trendName">${esc(x.keyword)}</span> ${chips.join(' ')}</div><div class="bar"><i style="width:${Math.min(100, Number(x.trend_score)||0)}%"></i></div></div><div class="grow">${fmt(x.trend_score)}</div></div>`;
  }).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderMatrix(a){
  $('#trendMatrix').innerHTML = (a && a.length) ? a.map(x => `<div class="trendRow"><div class="rankBody"><b>${esc(x.keyword)}</b></div><b>${fmt(x.trend_score)}</b></div>`).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderThemes(themes){
  $('#themeGrid').innerHTML = (themes && themes.length) ? themes.map((t,i) => {
    const rc = i===0?'gold':i===1?'silver':i===2?'bronze':'normal';
    const rl = state.lang==='ko' ? `${i+1}위` : state.lang==='ar' ? `المركز ${i+1}` : `#${i+1}`;
    return `<div class="themeCard" style="border-color:${t.color}44"><div class="themeHeader"><span class="themeRank ${rc}">${rl}</span><span class="themeIcon">${t.icon}</span><span class="themeName">${esc(themeT(t.theme))}</span></div><div class="meta">${t.keyword_count} keywords</div><div class="themeKeywords">${(t.top_keywords||[]).slice(0,5).map(k=>`<span class="chip">${esc(k.keyword)}</span>`).join('')}</div></div>`;
  }).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderPeriodList(a, sel, total){
  $(sel).innerHTML = (a && a.length) ? a.map((x,i) => `<div class="trendRow"><div class="rankNo">${i+1}</div><div class="rankBody"><div class="trendName">${esc(x.keyword)}</div><div class="trendMeta"><span class="metaChip">${esc(themeT(x.theme))}</span><span class="metaChip">${tr('days')}: ${x.active_days}/${total}</span></div></div><div class="grow">${fmt(x.total_score)}</div></div>`).join('') : `<p class="muted">${tr('noData')}</p>`;
}

function renderDelta(delta, sel){
  const box = $(sel); if(!box) return;
  const li = (list,f) => (list && list.length) ? list.slice(0,10).map(f).join('') : `<li>${tr('noData')}</li>`;
  box.innerHTML = `
  <div class="deltaCard"><h3 class="new">${tr('newEntries')}</h3><ul class="deltaList">${li(delta.new, x=>`<li>${esc(x.keyword)} <b>${fmt(x.score)}</b></li>`)}</ul></div>
  <div class="deltaCard"><h3 class="rising">${tr('risingRank')}</h3><ul class="deltaList">${li(delta.rising, x=>`<li>${esc(x.keyword)} <b>${fmt(x.prev_score)} → ${fmt(x.curr_score)}</b></li>`)}</ul></div>
  <div class="deltaCard"><h3 class="falling">${tr('fallingRank')}</h3><ul class="deltaList">${li(delta.cooling, x=>`<li>${esc(x.keyword)} <b>${fmt(x.prev_score)}${x.curr_score? ' → '+fmt(x.curr_score):''}</b></li>`)}</ul></div>`;
}

function rankCard(p, i){
  let badge = '';
  if (state.kind === 'overall'){
    if (p.olive_rank) badge += `<span class="metaChip">${tr('mallOlive')} #${p.olive_rank}</span>`;
    if (p.daiso_score) badge += `<span class="metaChip">${tr('mallDaiso')} ${fmt(p.daiso_score)}</span>`;
  } else if (state.kind === 'olive'){
    if (p.olive_rank) badge = `<span class="metaChip">${tr('mallOlive')} #${p.olive_rank}</span>`;
  } else if (state.kind === 'daiso'){
    if (p.daiso_score) badge = `<span class="metaChip">${tr('mallDaiso')} ${fmt(p.daiso_score)}</span>`;
  }
  const nameHtml = p.product_url
    ? `<a href="${esc(p.product_url)}" target="_blank" rel="noopener noreferrer" class="prodNameLink">${esc(pname(p))}</a>`
    : `<span class="prodName">${esc(pname(p))}</span>`;
  return `<div class="rankRow"><div class="rankNo">${i}</div><div class="rankBody"><div class="rankNameLine">${nameHtml} ${badge}</div><div class="meta">${esc(bname(p)||'')} · ${esc(cname(p)||'')}</div></div></div>`;
}

function renderProducts(){
  $('#products').innerHTML = state.products.map(p => `
  <div class="productCard" data-url="${esc(p.product_url||'')}">
    <div class="source">${esc(p.source||'')}</div>
    <a href="${esc(p.product_url||'#')}" target="_blank" rel="noopener noreferrer" class="prodNameLink">${esc(pname(p))}</a>
    <div class="meta">${esc(bname(p)||'')} · ${esc(cname(p)||'')}</div>
    <div class="chips">${arr(p.keywords).slice(0,4).map(x=>`<span class="chip">${esc(x)}</span>`).join('')}</div>
  </div>`).join('');
  $('#loadMore').style.display = state.hasMore ? 'block' : 'none';
}

async function loadProducts(reset=true){
  if (reset){ state.page = 0; state.products = []; }
  const q = encodeURIComponent(state.q), cat = encodeURIComponent(state.category);
  const limit = reset ? state.initialLoad : state.loadMoreStep;
  const offset = reset ? 0 : state.products.length;
  const d = await api(`/api/products?q=${q}&category=${cat}&limit=${limit}&offset=${offset}`);
  state.products = reset ? d.items : state.products.concat(d.items);
  state.hasMore = d.has_more;
  $('#productDate').textContent = d.latest_date || $('#productDate').textContent;
  renderProducts();
}

async function loadRanking(){
  try{
    const d = await api('/api/rankings?kind=' + state.kind + '&limit=50');
    $('#productDate').textContent = d.latest_date || '';
    $('#rankTitle').textContent = tr(state.kind);
    $('#rankingList').innerHTML = d.items.map((p,i) => rankCard(p, i+1)).join('') || `<p class="muted">${tr('noData')}</p>`;
  }catch(e){ $('#rankingList').innerHTML = `<p class="muted">${tr('noData')}</p>`; }
}

async function loadChangeData(){
  try{
    const d = await api('/api/rankings/change');
    const renderList = (items, type, elId) => {
      const el = $(elId);
      if (!items || !items.length){ el.innerHTML = `<li>${tr('noData')}</li>`; return; }
      el.innerHTML = items.slice(0,15).map(item => {
        const mall = item.source === 'oliveyoung' ? tr('mallOlive') : tr('mallDaiso');
        let badge = '';
        if (type==='new') badge = `<span class="changeBadge new">🆕</span>`;
        else if (type==='rise') badge = `<span class="changeBadge rise">▲ +${item.diff}</span>`;
        else badge = `<span class="changeBadge fall">▼ ${item.diff}</span>`;
        const link = item.product_url ? `<a href="${esc(item.product_url)}" target="_blank" rel="noopener noreferrer" class="prodNameLink">${esc(pname(item))}</a>` : esc(pname(item));
        return `<li>${link} <span class="mallBadge">${mall}</span> ${badge}</li>`;
      }).join('');
    };
    renderList(d.new,'new','#changeNew');
    renderList(d.rising,'rise','#changeRise');
    renderList(d.falling,'fall','#changeFall');
  }catch(e){ console.error(e); }
}

async function loadCategories(){
  const d = await api('/api/categories');
  $('#category').innerHTML = `<option value="">${tr('allCategories')}</option>` + d.items.map(x=>`<option value="${esc(x.category)}">${esc(x.category)} (${x.count})</option>`).join('');
}

async function loadSuggestions(){
  try{ const d = await api('/api/suggestions'); SUGGESTIONS = d.items || []; }catch(e){ SUGGESTIONS = []; }
}
function renderSuggestions(){
  const q = state.q.trim().toLowerCase();
  const list = SUGGESTIONS.filter(k => !q || k.toLowerCase().includes(q)).slice(0,18);
  const box = $('#suggestBox');
  if (!list.length){ box.classList.remove('show'); return; }
  box.innerHTML = list.map(k=>`<span class="chip" data-k="${esc(k)}">${esc(k)}</span>`).join('');
  box.classList.add('show');
  $$('#suggestBox .chip').forEach(ch => ch.onclick = () => { $('#search').value = ch.dataset.k; state.q = ch.dataset.k; box.classList.remove('show'); loadProducts(); });
}

let timer;
$('#search').addEventListener('input', e => { state.q = e.target.value; renderSuggestions(); clearTimeout(timer); timer = setTimeout(() => loadProducts(), 350); });
$('#search').addEventListener('focus', renderSuggestions);
document.addEventListener('click', e => { if (!e.target.closest('.searchWrap')) $('#suggestBox').classList.remove('show'); });
$('#category').addEventListener('change', e => { state.category = e.target.value; loadProducts(); });
$('#loadMore').onclick = () => loadProducts(false);

$$('.rankTab').forEach(b => b.onclick = () => {
  state.kind = b.dataset.kind;
  $$('.rankTab').forEach(x => x.classList.toggle('active', x===b));
  if (state.kind === 'change'){ $('#rankPanel').style.display='none'; $('#changePanel').style.display='block'; loadChangeData(); }
  else { $('#rankPanel').style.display='block'; $('#changePanel').style.display='none'; loadRanking(); }
});

async function loadDailyData(){
  try{
    const d = await api('/api/trends/daily');
    $('#catalogDate').textContent = d.date || '';
    renderTrends(d.trends || []);
    renderMatrix(d.trends || []);
    const t = await api('/api/trends/themes');
    renderThemes(t.themes || []);
  }catch(e){ console.error(e); }
}
async function loadWeeklyData(){ try{ const d = await api('/api/trends/weekly'); renderPeriodList(d.trends||[], '#weeklyList', 5); renderDelta(d.delta||{}, '#weeklyDelta'); }catch(e){ console.error(e); } }
async function loadMonthlyData(){ try{ const d = await api('/api/trends/monthly'); renderPeriodList(d.trends||[], '#monthlyList', 30); renderDelta(d.delta||{}, '#monthlyDelta'); }catch(e){ console.error(e); } }
function loadPeriodData(){
  if (state.currentPeriod==='daily') loadDailyData();
  else if (state.currentPeriod==='weekly') loadWeeklyData();
  else loadMonthlyData();
}

function renderAll(){
  if ($('#trendPage').classList.contains('active')) loadPeriodData();
  if ($('#productsPage').classList.contains('active')){
    if (state.kind==='change') loadChangeData(); else loadRanking();
    renderProducts();
  }
}

$('#close').onclick = () => $('#modal').classList.remove('show');
$('#modal').onclick = e => { if (e.target.id==='modal') $('#modal').classList.remove('show'); };

applyLang();
loadDailyData();
loadRanking();
loadCategories();
loadSuggestions();
