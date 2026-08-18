// 전역 변수
let fuse = null;
let productPool = [];

document.addEventListener('DOMContentLoaded', async () => {
    setupTabs();
    await initDashboard();
    setupSearch();
});

// 1. 탭 전환 로직 (네비게이션 실종 방지)
function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            // 버튼 활성화
            tabs.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 콘텐츠 전환
            const targetId = `${btn.dataset.tab}-tab`;
            contents.forEach(c => c.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');
        });
    });
}

// 2. 대시보드 초기화
async function initDashboard() {
    try {
        const res = await fetch('/api/app/home');
        const data = await res.json();

        // 검색용 데이터 풀 생성 (기존 데이터 활용)
        productPool = [
            ...(data.rising_products || []),
            ...(data.top_rankings || [])
        ];
        
        // 렌더링
        renderOliveRising(data.rising_products || []);
        renderDaisoBest(data.daiso_picks || data.top_rankings.filter(p => p.source === 'daiso') || []);
        
    } catch (err) {
        console.error('데이터 로드 실패:', err);
    }
}

// 3. 검색 자동완성 (Fuse.js)
function setupSearch() {
    if (!window.Fuse) return;

    // 검색 옵션 설정 (오타 허용, 브랜드/상품명 검색)
    const options = { keys: ['product_name', 'brand'], threshold: 0.3 };
    fuse = new Fuse(productPool, options);

    const input = document.getElementById('searchInput');
    const box = document.getElementById('searchSuggestions');

    input.addEventListener('input', (e) => {
        const val = e.target.value;
        if (!val.trim()) { box.style.display = 'none'; return; }

        const results = fuse.search(val).slice(0, 5); // 상위 5개
        
        if (results.length > 0) {
            box.innerHTML = results.map(r => `
                <div class="suggestion-item" onclick="window.open('${r.item.product_url}', '_blank')">
                    <div>
                        <strong>${r.item.brand}</strong>
                        <div>${r.item.product_name}</div>
                    </div>
                    <span class="badge ${r.item.source === 'oliveyoung' ? 'badge-olive' : 'badge-daiso'}">
                        ${r.item.source === 'oliveyoung' ? '올리브영' : '다이소'}
                    </span>
                </div>
            `).join('');
            box.style.display = 'block';
        } else {
            box.style.display = 'none';
        }
    });
    
    // 외부 클릭 시 닫기
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) box.style.display = 'none';
    });
}

// 4. 올리브영 급상승 랭킹 렌더링
function renderOliveRising(products) {
    const container = document.getElementById('olive-rising');
    container.innerHTML = products.map(p => {
        // 랭킹 변동 계산 (이전 랭킹 - 현재 랭킹 = 양수면 상승)
        const diff = (p.previous_rank || 0) - (p.rank || p.rank_num || 0);
        const changeHtml = diff > 0 
            ? `<div class="rank-change-up">🚀 ${diff}계단 급상승</div>` 
            : `<div class="rank-change-down">📉 ${Math.abs(diff)}계단 하락</div>`;

        return `
            <div class="product-card" onclick="window.open('${p.product_url}', '_blank')">
                <span class="badge badge-olive">🫒 올리브영</span>
                ${changeHtml}
                <div class="brand">${p.brand}</div>
                <div class="name">${p.product_name}</div>
                <div class="price">${p.sale_price ? p.sale_price.toLocaleString() + '원' : '가격 미정'}</div>
            </div>
        `;
    }).join('');
}

// 5. 다이소 베스트 렌더링
function renderDaisoBest(products) {
    const container = document.getElementById('daiso-best');
    container.innerHTML = products.slice(0, 10).map(p => `
        <div class="product-card" onclick="window.open('${p.product_url}', '_blank')">
            <span class="badge badge-daiso">🔵 다이소</span>
            <div class="brand">${p.brand}</div>
            <div class="name">${p.product_name}</div>
            <div class="price" style="color: #1565c0;">가성비 꿀템</div>
        </div>
    `).join('');
}
