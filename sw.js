
self.addEventListener('install', (e) => {
    console.log('[MerkezSoft] Service Worker Kuruldu');
});

self.addEventListener('fetch', (e) => {
    // Şimdilik sadece ağ üzerinden çalışıyor
});
