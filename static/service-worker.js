const CACHE_NAME = "kbeauty-dashboard-v1";

const APP_SHELL = [
    "/",
    "/static/index.html",
    "/static/app.js",
    "/static/style.css",
    "/static/manifest.json"
];

// 캐시하지 않을 경로 (API 요청은 항상 최신 데이터 필요)
const NO_CACHE_PATTERNS = [
    /^\/api\//  // 모든 API 요청
];

function shouldCache(url) {
    return !NO_CACHE_PATTERNS.some(pattern => pattern.test(url));
}

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
            .then(() => {
                console.log("[ServiceWorker] App shell cached");
            })
    );

    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => {
                        console.log("[ServiceWorker] Deleting old cache:", key);
                        return caches.delete(key);
                    })
            )
        ).then(() => {
            console.log("[ServiceWorker] Activated");
        })
    );

    self.clients.claim();
});

self.addEventListener("fetch", event => {
    if (event.request.method !== "GET") return;

    const url = new URL(event.request.url);
    
    // API 요청은 캐시하지 않고 네트워크에서만 가져옴
    if (!shouldCache(url.pathname)) {
        event.respondWith(fetch(event.request));
        return;
    }

    // 정적 파일은 Network First 전략
    event.respondWith(
        fetch(event.request)
            .then(response => {
                // 성공한 응답만 캐시
                if (response.ok) {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, copy);
                    });
                }
                return response;
            })
            .catch(error => {
                console.log("[ServiceWorker] Fetch failed, using cache:", event.request.url);
                return caches.match(event.request);
            })
    );
});

// 백그라운드 동기화 (선택사항 - 오프라인에서 데이터 변경 시 서버와 동기화)
self.addEventListener("sync", event => {
    if (event.tag === "sync-trends") {
        event.waitUntil(syncTrends());
    }
});

async function syncTrends() {
    console.log("[ServiceWorker] Syncing trends data...");
    // 여기에 오프라인에서 변경된 데이터를 서버로 전송하는 로직 추가 가능
}
