/**
 * Travel Map & Google Places Search Integration
 * - Parabolic dashed arc routes for flights & ferries (放物線ルート)
 * - Automatic driving duration calculation and timeline display for cars
 * - Destination-based auto-centering and localized search biasing
 */
let mapInstance = null;
let mapMarkers = [];
let routePolylines = [];
let routeBadges = [];
let directionsService = null;
let autocompleteInstance = null;

// CSRF Token Helper
function getCsrfToken() {
  const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
  if (cookieMatch) return decodeURIComponent(cookieMatch[1]);
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// 座標間の自動車移動時間の概算フォールバック計算
function calculateDrivingMinutes(p1, p2) {
  const R = 6371; // 地球半径 (km)
  const dLat = (p2.lat - p1.lat) * Math.PI / 180;
  const dLng = (p2.lng - p1.lng) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distKm = R * c;
  const roadKm = distKm * 1.35; // 道路の曲がり係数
  const minutes = Math.round((roadKm / 40.0) * 60); // 平均時速40km
  return Math.max(5, minutes);
}

function formatMinutes(totalMinutes) {
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;
  if (hours > 0 && mins > 0) {
    return `${hours}時間${mins}分`;
  } else if (hours > 0) {
    return `${hours}時間`;
  } else {
    return `${mins}分`;
  }
}

// 飛行機・フェリー用の優美な放物線（二次ベジェ曲線）の座標列と頂点を生成
function generateCurvedArc(p1, p2, numPoints = 40, curvature = 0.20) {
  const points = [];
  const dx = p2.lng - p1.lng;
  const dy = p2.lat - p1.lat;
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) return { points: [p1, p2], midPoint: p1 };

  // 法線ベクトル
  let nx = -dy / dist;
  let ny = dx / dist;

  // 常に北側（上方向）に凸となるよう制御
  if (ny < 0) {
    nx = -nx;
    ny = -ny;
  }

  const offset = dist * curvature;
  const midLat = (p1.lat + p2.lat) / 2;
  const midLng = (p1.lng + p2.lng) / 2;
  const controlPoint = {
    lat: midLat + ny * offset,
    lng: midLng + nx * offset,
  };

  // ベジェ曲線補間
  for (let i = 0; i <= numPoints; i++) {
    const t = i / numPoints;
    const invT = 1 - t;
    const lat = invT * invT * p1.lat + 2 * invT * t * controlPoint.lat + t * t * p2.lat;
    const lng = invT * invT * p1.lng + 2 * invT * t * controlPoint.lng + t * t * p2.lng;
    points.push({ lat, lng });
  }

  const apex = {
    lat: 0.25 * p1.lat + 0.5 * controlPoint.lat + 0.25 * p2.lat,
    lng: 0.25 * p1.lng + 0.5 * controlPoint.lng + 0.25 * p2.lng,
  };

  return { points, midPoint: apex };
}

// 日本全国の主要観光地・都道府県・都市のプリセット座標辞書（瞬時センタリング用）
const PRESET_DESTINATIONS = {
  '北海道': { lat: 43.4, lng: 142.8, zoom: 7 },
  '札幌': { lat: 43.0618, lng: 141.3545, zoom: 12 },
  '小樽': { lat: 43.1907, lng: 140.9947, zoom: 12 },
  '函館': { lat: 41.7687, lng: 140.7288, zoom: 12 },
  '富良野': { lat: 43.3421, lng: 142.3832, zoom: 11 },
  '美瑛': { lat: 43.5912, lng: 142.4636, zoom: 11 },
  '旭川': { lat: 43.7706, lng: 142.3650, zoom: 11 },
  '登別': { lat: 42.4131, lng: 141.1066, zoom: 12 },
  '知床': { lat: 44.0583, lng: 145.1294, zoom: 10 },
  '釧路': { lat: 42.9849, lng: 144.3818, zoom: 11 },
  '十勝': { lat: 42.9239, lng: 143.1961, zoom: 10 },
  '帯広': { lat: 42.9239, lng: 143.1961, zoom: 12 },
  '洞爺湖': { lat: 42.5800, lng: 140.8500, zoom: 12 },
  'ニセコ': { lat: 42.8617, lng: 140.6983, zoom: 12 },
  '青森': { lat: 40.8244, lng: 140.7400, zoom: 10 },
  '弘前': { lat: 40.6031, lng: 140.4642, zoom: 12 },
  '八戸': { lat: 40.5123, lng: 141.4884, zoom: 12 },
  '十和田': { lat: 40.6145, lng: 141.2173, zoom: 11 },
  '岩手': { lat: 39.7036, lng: 141.1527, zoom: 9 },
  '盛岡': { lat: 39.7036, lng: 141.1527, zoom: 12 },
  '平泉': { lat: 38.9867, lng: 141.1144, zoom: 13 },
  '宮城': { lat: 38.2682, lng: 140.8694, zoom: 10 },
  '仙台': { lat: 38.2682, lng: 140.8694, zoom: 12 },
  '松島': { lat: 38.3713, lng: 141.0664, zoom: 12 },
  '秋田': { lat: 39.7186, lng: 140.1024, zoom: 10 },
  '田沢湖': { lat: 39.7214, lng: 140.6625, zoom: 12 },
  '角館': { lat: 39.5933, lng: 140.5614, zoom: 13 },
  '山形': { lat: 38.2554, lng: 140.3396, zoom: 10 },
  '蔵王': { lat: 38.1367, lng: 140.4461, zoom: 12 },
  '銀山温泉': { lat: 38.5703, lng: 140.5303, zoom: 14 },
  '福島': { lat: 37.7608, lng: 140.4748, zoom: 10 },
  '会津': { lat: 37.4948, lng: 139.9297, zoom: 12 },
  '東京': { lat: 35.6812, lng: 139.7671, zoom: 12 },
  '神奈川': { lat: 35.4475, lng: 139.6423, zoom: 11 },
  '横浜': { lat: 35.4437, lng: 139.6380, zoom: 12 },
  '箱根': { lat: 35.2323, lng: 139.0416, zoom: 12 },
  '鎌倉': { lat: 35.3190, lng: 139.5467, zoom: 13 },
  '千葉': { lat: 35.6073, lng: 140.1063, zoom: 11 },
  '埼玉': { lat: 35.8617, lng: 139.6455, zoom: 11 },
  '日光': { lat: 36.7548, lng: 139.5986, zoom: 12 },
  '那須': { lat: 37.0189, lng: 140.0169, zoom: 11 },
  '草津': { lat: 36.6206, lng: 138.5963, zoom: 13 },
  '伊香保': { lat: 36.4983, lng: 138.9175, zoom: 13 },
  '新潟': { lat: 37.9022, lng: 139.0232, zoom: 10 },
  '富山': { lat: 36.6953, lng: 137.2113, zoom: 11 },
  '石川': { lat: 36.5613, lng: 136.6562, zoom: 10 },
  '金沢': { lat: 36.5613, lng: 136.6562, zoom: 12 },
  '福井': { lat: 36.0652, lng: 136.2216, zoom: 11 },
  '山梨': { lat: 35.6639, lng: 138.5684, zoom: 11 },
  '富士': { lat: 35.3606, lng: 138.7274, zoom: 11 },
  '長野': { lat: 36.6513, lng: 138.1810, zoom: 10 },
  '軽井沢': { lat: 36.3488, lng: 138.6355, zoom: 12 },
  '松本': { lat: 36.2380, lng: 137.9720, zoom: 12 },
  '上高地': { lat: 36.2486, lng: 137.6375, zoom: 12 },
  '白馬': { lat: 36.6983, lng: 137.8617, zoom: 12 },
  '岐阜': { lat: 35.4233, lng: 136.7607, zoom: 11 },
  '高山': { lat: 36.1460, lng: 137.2522, zoom: 12 },
  '白川郷': { lat: 36.2562, lng: 136.9063, zoom: 13 },
  '下呂': { lat: 35.8078, lng: 137.2436, zoom: 13 },
  '静岡': { lat: 34.9756, lng: 138.3828, zoom: 10 },
  '熱海': { lat: 35.0963, lng: 139.0717, zoom: 13 },
  '伊豆': { lat: 34.9717, lng: 138.9553, zoom: 11 },
  '愛知': { lat: 35.1815, lng: 136.9066, zoom: 10 },
  '名古屋': { lat: 35.1815, lng: 136.9066, zoom: 12 },
  '三重': { lat: 34.7303, lng: 136.5086, zoom: 10 },
  '伊勢': { lat: 34.4875, lng: 136.7094, zoom: 12 },
  '滋賀': { lat: 35.0045, lng: 135.8686, zoom: 10 },
  '琵琶湖': { lat: 35.2000, lng: 136.0000, zoom: 10 },
  '京都': { lat: 35.0116, lng: 135.7681, zoom: 12 },
  '大阪': { lat: 34.6937, lng: 135.5023, zoom: 12 },
  '兵庫': { lat: 34.6913, lng: 135.1830, zoom: 10 },
  '神戸': { lat: 34.6901, lng: 135.1955, zoom: 12 },
  '有馬': { lat: 34.7972, lng: 135.2472, zoom: 13 },
  '城崎': { lat: 35.6267, lng: 134.8136, zoom: 13 },
  '奈良': { lat: 34.6851, lng: 135.8048, zoom: 12 },
  '和歌山': { lat: 34.2260, lng: 135.1675, zoom: 10 },
  '白浜': { lat: 33.6822, lng: 135.3444, zoom: 12 },
  '鳥取': { lat: 35.5036, lng: 134.2383, zoom: 11 },
  '島根': { lat: 35.4723, lng: 133.0505, zoom: 10 },
  '出雲': { lat: 35.3674, lng: 132.7554, zoom: 12 },
  '岡山': { lat: 34.6618, lng: 133.9350, zoom: 11 },
  '倉敷': { lat: 34.5850, lng: 133.7719, zoom: 12 },
  '広島': { lat: 34.3853, lng: 132.4553, zoom: 11 },
  '宮島': { lat: 34.2981, lng: 132.3197, zoom: 13 },
  '尾道': { lat: 34.4089, lng: 133.2049, zoom: 12 },
  '山口': { lat: 34.1859, lng: 131.4705, zoom: 10 },
  '下関': { lat: 33.9578, lng: 130.9415, zoom: 12 },
  '徳島': { lat: 34.0658, lng: 134.5594, zoom: 11 },
  '香川': { lat: 34.3401, lng: 134.0434, zoom: 11 },
  '高松': { lat: 34.3428, lng: 134.0466, zoom: 13 },
  '小豆島': { lat: 34.5083, lng: 134.2833, zoom: 11 },
  '愛媛': { lat: 33.8417, lng: 132.7661, zoom: 11 },
  '松山': { lat: 33.8392, lng: 132.7656, zoom: 12 },
  '道後': { lat: 33.8522, lng: 132.7850, zoom: 14 },
  '高知': { lat: 33.5597, lng: 133.5311, zoom: 11 },
  '福岡': { lat: 33.5904, lng: 130.4017, zoom: 11 },
  '博多': { lat: 33.5904, lng: 130.4180, zoom: 13 },
  '糸島': { lat: 33.5583, lng: 130.1972, zoom: 12 },
  '佐賀': { lat: 33.2494, lng: 130.2988, zoom: 11 },
  '長崎': { lat: 32.7448, lng: 129.8737, zoom: 12 },
  '熊本': { lat: 32.7898, lng: 130.7417, zoom: 11 },
  '阿蘇': { lat: 32.8842, lng: 131.0850, zoom: 11 },
  '黒川': { lat: 33.0786, lng: 131.1394, zoom: 13 },
  '大分': { lat: 33.2382, lng: 131.6126, zoom: 11 },
  '別府': { lat: 33.2796, lng: 131.4975, zoom: 12 },
  '由布院': { lat: 33.2625, lng: 131.3556, zoom: 13 },
  '宮崎': { lat: 31.9111, lng: 131.4239, zoom: 11 },
  '鹿児島': { lat: 31.5966, lng: 130.5571, zoom: 11 },
  '屋久島': { lat: 30.3444, lng: 130.5147, zoom: 10 },
  '沖縄': { lat: 26.35, lng: 127.8, zoom: 10 },
  '那覇': { lat: 26.2124, lng: 127.6809, zoom: 13 },
  '石垣': { lat: 24.3448, lng: 124.1572, zoom: 11 },
  '宮古': { lat: 24.8055, lng: 125.2811, zoom: 11 }
};

// Initialize Google Map
function initTravelMap() {
  const mapElement = document.getElementById('travel-map-container');
  if (!mapElement) return;

  const defaultCenter = { lat: 35.6812, lng: 139.7671 }; // 東京駅初期値

  mapInstance = new google.maps.Map(mapElement, {
    center: defaultCenter,
    zoom: 12,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: true,
    styles: [
      {
        featureType: "poi",
        elementType: "labels",
        stylers: [{ visibility: "off" }]
      }
    ]
  });
  window.mapInstance = mapInstance;

  directionsService = new google.maps.DirectionsService();

  // 初回スポット描画（0件の場合は旅行先エリアにセンタリング）
  renderStopsOnMap();

  // スポット追加用 Google Places Autocomplete 初期化
  initPlacesAutocomplete();
}
window.initTravelMap = initTravelMap;

// 旅行先エリア（Destination）をマップ中心＆サジェストバイアスに反映
function applyDestinationToMap(destination, map) {
  if (!destination || !map) return;

  // 1. プリセット辞書によるゼロ遅延センタリング
  let matchedPreset = false;
  for (const [key, loc] of Object.entries(PRESET_DESTINATIONS)) {
    if (destination.includes(key)) {
      map.setCenter({ lat: loc.lat, lng: loc.lng });
      map.setZoom(loc.zoom);
      matchedPreset = true;
      break;
    }
  }

  // 2. Google Geocoder で正確な境界領域 (Viewport / Bounds) を取得
  if (typeof google !== 'undefined' && google.maps && google.maps.Geocoder) {
    const geocoder = new google.maps.Geocoder();
    const cleanAddress = destination.replace(/[（\(][^）\)]*[）\)]/g, ' ').trim() || destination;
    geocoder.geocode({ address: cleanAddress, region: 'JP' }, (results, status) => {
      if (status === 'OK' && results[0] && results[0].geometry) {
        if (results[0].geometry.viewport) {
          map.fitBounds(results[0].geometry.viewport);
        } else if (results[0].geometry.location) {
          map.setCenter(results[0].geometry.location);
          if (!matchedPreset) map.setZoom(12);
        }

        if (autocompleteInstance && map.getBounds()) {
          autocompleteInstance.setBounds(map.getBounds());
        }
      }
    });
  }
}

// 既存のルート線とバッジをクリア
function clearRoutePolylinesAndBadges() {
  routePolylines.forEach(p => p.setMap(null));
  routePolylines = [];
  routeBadges.forEach(b => b.setMap(null));
  routeBadges = [];
}

// Render stops as markers and draw route
function renderStopsOnMap() {
  if (!mapInstance) return;

  // Clear previous markers & routes
  mapMarkers.forEach(m => m.setMap(null));
  mapMarkers = [];
  clearRoutePolylinesAndBadges();

  const stops = window.TRAVEL_STOPS_DATA ? window.TRAVEL_STOPS_DATA.filter(s => s.lat && s.lng) : [];

  // スポットがまだ未登録の場合: 旅行先（destination）エリアにマップとサジェストを適合
  if (stops.length === 0) {
    const destination = window.TRAVEL_CONFIG?.destination;
    if (destination) {
      applyDestinationToMap(destination, mapInstance);
    }
    return;
  }

  const bounds = new google.maps.LatLngBounds();

  // マーカー配置
  stops.forEach((stop, index) => {
    const position = { lat: parseFloat(stop.lat), lng: parseFloat(stop.lng) };
    bounds.extend(position);

    const marker = new google.maps.Marker({
      position: position,
      map: mapInstance,
      title: stop.name,
      label: {
        text: String(index + 1),
        color: '#FFFFFF',
        fontWeight: 'bold',
        fontSize: '12px'
      }
    });

    const tripId = window.TRAVEL_CONFIG?.tripId || document.getElementById('timeline-stops-container')?.getAttribute('data-trip-id');
    const detailUrl = tripId ? `/travel/trips/${tripId}/stops/${stop.id}/` : '#';

    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 6px; font-family: sans-serif; min-width: 175px;">
          <div style="font-weight: 700; font-size: 14px; margin-bottom: 2px;">${index + 1}. ${stop.name}</div>
          <div style="font-size: 12px; color: #64748B; margin-bottom: 4px;">${stop.category_display || ''}</div>
          ${stop.arrival_time ? `<div style="font-size: 12px; color: #0284C7; font-weight: 600; margin-bottom: 6px;">到着: ${stop.arrival_time}</div>` : ''}
          <div style="margin-top: 8px;">
            <a href="${detailUrl}" style="display: inline-flex; align-items: center; gap: 5px; background: #0284C7; color: #FFFFFF; padding: 5px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-decoration: none; box-shadow: 0 1px 3px rgba(2,132,199,0.3);">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
              <span>詳細・クチコミ・写真 ↗</span>
            </a>
          </div>
        </div>
      `
    });

    marker.stopId = stop.id;
    marker.infoWindow = infoWindow;

    marker.addListener('click', () => {
      focusStopAndNeighbors(stop.id, false, false);
    });

    mapMarkers.push(marker);
  });

  if (stops.length === 1) {
    mapInstance.setCenter({ lat: parseFloat(stops[0].lat), lng: parseFloat(stops[0].lng) });
    mapInstance.setZoom(14);
  } else if (stops.length >= 2) {
    drawTravelRoute(stops, bounds);
  }
}

// スポットタップ時: 前後のスポットを含めた縮尺に地図を自動ズーム＆ハイライト
// A→B→C→D→E のとき Dタップなら C, D, E が収まる縮尺に調整
// scrollTimeline: 地図のピンをクリックした場合は下のスポットへスクロールしない（false）
function focusStopAndNeighbors(stopId, triggerMarkerAnimation = true, scrollTimeline = false) {
  if (!mapInstance) return;

  const stops = window.TRAVEL_STOPS_DATA ? window.TRAVEL_STOPS_DATA.filter(s => s.lat && s.lng) : [];
  if (stops.length === 0) return;

  const targetIdx = stops.findIndex(s => String(s.id) === String(stopId));
  if (targetIdx === -1) return;

  // 前後のスポット（A→B→C→D→E のとき Dなら C, D, E）
  const startIdx = Math.max(0, targetIdx - 1);
  const endIdx = Math.min(stops.length - 1, targetIdx + 1);
  const neighborStops = stops.slice(startIdx, endIdx + 1);

  const bounds = new google.maps.LatLngBounds();
  neighborStops.forEach(s => {
    bounds.extend({ lat: parseFloat(s.lat), lng: parseFloat(s.lng) });
  });

  // 対象区間に飛行機・フェリーの放物線アーチがある場合、頂点も含めて見切れを防止
  for (let i = startIdx; i < endIdx; i++) {
    const s1 = stops[i];
    const s2 = stops[i + 1];
    if (s1.transport_mode === 'flight' || s1.transport_mode === 'boat') {
      const p1 = { lat: parseFloat(s1.lat), lng: parseFloat(s1.lng) };
      const p2 = { lat: parseFloat(s2.lat), lng: parseFloat(s2.lng) };
      const arc = generateCurvedArc(p1, p2, 20, s1.transport_mode === 'flight' ? 0.20 : 0.12);
      bounds.extend(arc.midPoint);
    }
  }

  if (neighborStops.length === 1) {
    const pos = { lat: parseFloat(neighborStops[0].lat), lng: parseFloat(neighborStops[0].lng) };
    mapInstance.panTo(pos);
    mapInstance.setZoom(15);
  } else {
    // 前後のスポットが余裕を持って収まるようにパディング指定
    mapInstance.fitBounds(bounds, { top: 75, bottom: 75, left: 75, right: 75 });

    // 近接スポットの場合の過剰ズーム防止
    const listener = google.maps.event.addListener(mapInstance, 'idle', () => {
      if (mapInstance.getZoom() > 16) {
        mapInstance.setZoom(16);
      }
      google.maps.event.removeListener(listener);
    });
  }

  // 該当スポットのマーカーのInfoWindowを開く＆バウンス演出
  const matched = mapMarkers.find(m => String(m.stopId) === String(stopId));
  if (matched) {
    mapMarkers.forEach(m => m.infoWindow?.close());
    matched.infoWindow?.open(mapInstance, matched);
    if (triggerMarkerAnimation && matched.setAnimation) {
      matched.setAnimation(google.maps.Animation.BOUNCE);
      setTimeout(() => matched.setAnimation(null), 700);
    }
  }

  // タイムラインカードのハイライト状態更新（ピンクリック時はスクロールしない）
  document.querySelectorAll('.timeline-stop-card').forEach(card => {
    if (card.getAttribute('data-stop-id') === String(stopId)) {
      card.classList.add('is-focused');
      if (scrollTimeline) {
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    } else {
      card.classList.remove('is-focused');
    }
  });

  // モバイル表示でタイムライン側から呼ばれ、マップが画面外にある場合のみマップ位置へスクロール
  if (window.innerWidth <= 768 && triggerMarkerAnimation) {
    const mapPane = document.querySelector('.workspace-map-pane');
    if (mapPane) {
      const rect = mapPane.getBoundingClientRect();
      if (rect.top < -50 || rect.bottom < 150) {
        mapPane.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }
}
window.focusStopAndNeighbors = focusStopAndNeighbors;

// 全スポットが収まる初期縮尺にリセット
function fitAllStopsOnMap() {
  if (!mapInstance) return;
  const stops = window.TRAVEL_STOPS_DATA ? window.TRAVEL_STOPS_DATA.filter(s => s.lat && s.lng) : [];
  if (stops.length === 0) return;

  const bounds = new google.maps.LatLngBounds();
  stops.forEach(s => bounds.extend({ lat: parseFloat(s.lat), lng: parseFloat(s.lng) }));

  for (let i = 0; i < stops.length - 1; i++) {
    const s1 = stops[i];
    const s2 = stops[i + 1];
    if (s1.transport_mode === 'flight' || s1.transport_mode === 'boat') {
      const p1 = { lat: parseFloat(s1.lat), lng: parseFloat(s1.lng) };
      const p2 = { lat: parseFloat(s2.lat), lng: parseFloat(s2.lng) };
      const arc = generateCurvedArc(p1, p2, 20, s1.transport_mode === 'flight' ? 0.20 : 0.12);
      bounds.extend(arc.midPoint);
    }
  }

  if (stops.length === 1) {
    mapInstance.setCenter({ lat: parseFloat(stops[0].lat), lng: parseFloat(stops[0].lng) });
    mapInstance.setZoom(14);
  } else {
    mapInstance.fitBounds(bounds, { top: 60, bottom: 60, left: 60, right: 60 });
  }

  // InfoWindowクリア＆カードハイライトクリア
  mapMarkers.forEach(m => m.infoWindow?.close());
  document.querySelectorAll('.timeline-stop-card').forEach(card => card.classList.remove('is-focused'));
}
window.fitAllStopsOnMap = fitAllStopsOnMap;

// Draw segment-by-segment route based on transport mode
function drawTravelRoute(stops, bounds) {
  if (stops.length < 2) return;

  for (let i = 0; i < stops.length - 1; i++) {
    const fromStop = stops[i];
    const toStop = stops[i + 1];
    const p1 = { lat: parseFloat(fromStop.lat), lng: parseFloat(fromStop.lng) };
    const p2 = { lat: parseFloat(toStop.lat), lng: parseFloat(toStop.lng) };
    const mode = fromStop.transport_mode || 'car';

    if (mode === 'flight') {
      // ✈️ 飛行機: 放物線（ベジェ曲線）の破線ルートとバッジを描画（車のルートは描画しない）
      drawFlightParabolicArc(p1, p2, fromStop, i, bounds);
    } else if (mode === 'boat') {
      // 🚢 船・フェリー: 航路アーチ破線を描画
      drawFerryArc(p1, p2, fromStop, i, bounds);
    } else {
      // 🚗 車（car）またはその他: 道路ルート検索 ＆ 自動所要時間計算・表示
      drawDrivingRoute(p1, p2, fromStop, toStop, i, bounds);
    }
  }

  // 地図の表示領域調整
  setTimeout(() => {
    mapInstance.fitBounds(bounds, { top: 60, bottom: 60, left: 60, right: 60 });
  }, 100);
}

// ✈️ 飛行機: 放物線（ベジェ曲線）の破線ルートと頂点バッジ描画
function drawFlightParabolicArc(p1, p2, fromStop, index, bounds) {
  const arc = generateCurvedArc(p1, p2, 40, 0.20);
  bounds.extend(arc.midPoint);

  const lineSymbol = {
    path: 'M 0,-1.5 0,1.5',
    strokeOpacity: 0.95,
    strokeWeight: 3.5,
    scale: 2.5,
    strokeColor: '#0284C7'
  };

  const polyline = new google.maps.Polyline({
    path: arc.points,
    strokeOpacity: 0,
    icons: [{
      icon: lineSymbol,
      offset: '0',
      repeat: '12px'
    }],
    map: mapInstance,
    zIndex: 20 + index
  });
  routePolylines.push(polyline);

  // 頂点に飛行機マーク付きバッジを表示
  const rawDuration = fromStop.transport_time_text || '';
  const cleanDuration = rawDuration.replace(/^✈️\s*/, '').trim() || '飛行機';
  const textLen = cleanDuration.length;
  const badgeWidth = Math.max(68, 30 + textLen * 11);

  const badgeSvg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${badgeWidth}" height="24" viewBox="0 0 ${badgeWidth} 24">
      <rect x="1" y="1" width="${badgeWidth - 2}" height="22" rx="11" fill="#0284C7" fill-opacity="0.95" stroke="#FFFFFF" stroke-width="1.8"/>
      <g transform="translate(7, 4) scale(0.65)" fill="#FFFFFF">
        <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
      </g>
      <text x="${(badgeWidth + 14) / 2}" y="15.5" font-size="11" font-weight="700" fill="#FFFFFF" text-anchor="middle" font-family="-apple-system, sans-serif">${cleanDuration}</text>
    </svg>
  `;

  const badgeMarker = new google.maps.Marker({
    position: arc.midPoint,
    map: mapInstance,
    zIndex: 60 + index,
    icon: {
      url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(badgeSvg),
      scaledSize: new google.maps.Size(badgeWidth, 24),
      anchor: new google.maps.Point(badgeWidth / 2, 12)
    }
  });
  routeBadges.push(badgeMarker);
}

// 🚢 船・フェリー: 航路アーチ破線描画
function drawFerryArc(p1, p2, fromStop, index, bounds) {
  const arc = generateCurvedArc(p1, p2, 30, 0.12);
  bounds.extend(arc.midPoint);

  const lineSymbol = {
    path: 'M 0,-1 0,1',
    strokeOpacity: 0.9,
    strokeWeight: 3,
    scale: 2,
    strokeColor: '#0D9488'
  };

  const polyline = new google.maps.Polyline({
    path: arc.points,
    strokeOpacity: 0,
    icons: [{
      icon: lineSymbol,
      offset: '0',
      repeat: '10px'
    }],
    map: mapInstance,
    zIndex: 15 + index
  });
  routePolylines.push(polyline);

  const rawDuration = fromStop.transport_time_text || '';
  const cleanDuration = rawDuration.replace(/^🚢\s*/, '').trim() || 'フェリー';
  const textLen = cleanDuration.length;
  const badgeWidth = Math.max(68, 30 + textLen * 11);

  const badgeSvg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${badgeWidth}" height="22" viewBox="0 0 ${badgeWidth} 22">
      <rect x="1" y="1" width="${badgeWidth - 2}" height="20" rx="10" fill="#0D9488" fill-opacity="0.95" stroke="#FFFFFF" stroke-width="1.5"/>
      <g transform="translate(6, 4) scale(0.65)" fill="#FFFFFF">
        <path d="M20 21c-1.39 0-2.78-.47-4-1.32-2.44 1.71-5.56 1.71-8 0C6.78 20.53 5.39 21 4 21H2v2h2c1.38 0 2.74-.35 4-.99 2.52 1.29 5.48 1.29 8 0 1.26.65 2.62.99 4 .99h2v-2h-2zM3.95 19H4c1.6 0 3.02-.88 4-2 .98 1.12 2.4 2 4 2s3.02-.88 4-2c.98 1.12 2.4 2 4 2h.05l1.89-6.68c.08-.26.06-.54-.06-.78s-.34-.42-.6-.47L20 11.23V7c0-.55-.45-1-1-1h-5V1l-4 3v2H5c-.55 0-1 .45-1 1v4.23l-1.28.24c-.26.05-.49.23-.6.47-.12.24-.14.52-.06.78L3.95 19z"/>
      </g>
      <text x="${(badgeWidth + 14) / 2}" y="14.5" font-size="10" font-weight="700" fill="#FFFFFF" text-anchor="middle" font-family="-apple-system, sans-serif">${cleanDuration}</text>
    </svg>
  `;

  const badgeMarker = new google.maps.Marker({
    position: arc.midPoint,
    map: mapInstance,
    zIndex: 55 + index,
    icon: {
      url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(badgeSvg),
      scaledSize: new google.maps.Size(badgeWidth, 22),
      anchor: new google.maps.Point(badgeWidth / 2, 11)
    }
  });
  routeBadges.push(badgeMarker);
}

// 🚗 自動車: Google Directions によるルート描画と移動時間の自動計算＆表示
function drawDrivingRoute(p1, p2, fromStop, toStop, index, bounds) {
  directionsService.route(
    {
      origin: p1,
      destination: p2,
      travelMode: google.maps.TravelMode.DRIVING
    },
    (result, status) => {
      if (status === google.maps.DirectionsStatus.OK && result.routes[0]) {
        const routePath = result.routes[0].overview_path;
        const polyline = new google.maps.Polyline({
          path: routePath,
          strokeColor: "#0284C7",
          strokeOpacity: 0.85,
          strokeWeight: 5,
          map: mapInstance,
          zIndex: 10 + index
        });
        routePolylines.push(polyline);

        // 移動時間の取得とフォーマット
        const leg = result.routes[0].legs[0];
        let dur = leg.duration.text
          .replace(' hours', '時間')
          .replace(' hour', '時間')
          .replace(' mins', '分')
          .replace(' min', '分')
          .replace(/\s+/g, '');

        // 地図上のルート中間地点に車移動時間バッジを配置
        if (routePath.length > 0) {
          const midIdx = Math.floor(routePath.length / 2);
          const badgePos = routePath[midIdx];
          const textLen = dur.length;
          const badgeWidth = Math.max(64, 30 + textLen * 11);

          const badgeSvg = `
            <svg xmlns="http://www.w3.org/2000/svg" width="${badgeWidth}" height="22" viewBox="0 0 ${badgeWidth} 22">
              <rect x="1" y="1" width="${badgeWidth - 2}" height="20" rx="10" fill="#1E293B" fill-opacity="0.92" stroke="#FFFFFF" stroke-width="1.5"/>
              <g transform="translate(6, 4) scale(0.65)" fill="#FFFFFF">
                <path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/>
              </g>
              <text x="${(badgeWidth + 14) / 2}" y="14.5" font-size="10" font-weight="800" fill="#FFFFFF" text-anchor="middle" font-family="-apple-system, sans-serif">${dur}</text>
            </svg>
          `;

          const badgeMarker = new google.maps.Marker({
            position: badgePos,
            map: mapInstance,
            zIndex: 50 + index,
            icon: {
              url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(badgeSvg),
              scaledSize: new google.maps.Size(badgeWidth, 22),
              anchor: new google.maps.Point(badgeWidth / 2, 11)
            }
          });
          routeBadges.push(badgeMarker);
        }

        // タイムライン側の表示自動更新（車の場合は自動計算時間を即時表示）
        const autoText = `車で約${dur}`;
        const pillEl = document.getElementById(`transport-time-pill-${fromStop.id}`);
        if (pillEl) {
          if (!fromStop.transport_departure_time && !fromStop.transport_arrival_time) {
            pillEl.textContent = autoText;
          }
        }

        // バックエンドに自動計算時間を保存（手動ダイヤ未設定の場合）
        if (!fromStop.transport_departure_time && !fromStop.transport_arrival_time && fromStop.id) {
          if (fromStop.transport_time_text !== autoText) {
            fromStop.transport_time_text = autoText;
            saveAutoCarDuration(fromStop.id, autoText);
          }
        }
      } else {
        // 車でのルート検索が失敗した場合（海・島等）のフォールバック
        handleDrivingFallback(p1, p2, fromStop, index);
      }
    }
  );
}

// 自動車ルートのフォールバック描画
function handleDrivingFallback(p1, p2, fromStop, index) {
  const calculatedMins = calculateDrivingMinutes(p1, p2);
  const dur = formatMinutes(calculatedMins);

  const fallbackPolyline = new google.maps.Polyline({
    path: [p1, p2],
    strokeColor: "#0284C7",
    strokeOpacity: 0.6,
    strokeWeight: 4,
    map: mapInstance,
    zIndex: 10 + index
  });
  routePolylines.push(fallbackPolyline);

  const autoText = `車で約${dur}`;
  const pillEl = document.getElementById(`transport-time-pill-${fromStop.id}`);
  if (pillEl && !fromStop.transport_departure_time && !fromStop.transport_arrival_time) {
    pillEl.textContent = autoText;
  }

  if (!fromStop.transport_departure_time && !fromStop.transport_arrival_time && fromStop.id) {
    if (fromStop.transport_time_text !== autoText) {
      fromStop.transport_time_text = autoText;
      saveAutoCarDuration(fromStop.id, autoText);
    }
  }
}

// バックエンドに車移動の自動計算時間を同期
function saveAutoCarDuration(stopId, durationText) {
  const tripId = window.TRAVEL_CONFIG?.tripId || document.getElementById('timeline-stops-container')?.getAttribute('data-trip-id');
  if (!tripId || !stopId) return;

  const formData = new FormData();
  formData.append('transport_mode', 'car');
  formData.append('transport_time_text', durationText);

  fetch(`/travel/api/trips/${tripId}/stops/${stopId}/update-transport/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    // 保存成功
  })
  .catch(err => console.debug('Auto duration save:', err));
}

// Google Places Autocomplete（マップ表示領域バインド付き）
function initPlacesAutocomplete() {
  const input = document.getElementById('places-autocomplete-input');
  if (!input || autocompleteInstance) return;
  if (typeof google === 'undefined' || !google.maps || !google.maps.places) return;

  autocompleteInstance = new google.maps.places.Autocomplete(input, {
    fields: ['place_id', 'name', 'formatted_address', 'geometry', 'photos', 'rating', 'types']
  });
  window.autocompleteInstance = autocompleteInstance;

  // マップの現在の表示領域（旅行先エリア）にサジェストの検索範囲を自動追従
  if (mapInstance) {
    autocompleteInstance.bindTo('bounds', mapInstance);
    if (mapInstance.getBounds()) {
      autocompleteInstance.setBounds(mapInstance.getBounds());
    }
  }

  autocompleteInstance.addListener('place_changed', onPlaceSelected);
}
window.initPlacesAutocomplete = initPlacesAutocomplete;

function onPlaceSelected() {
  const place = autocompleteInstance.getPlace();
  if (!place || !place.geometry) {
    return;
  }

  // 自動補完フォームに反映
  const form = document.getElementById('add-stop-form');
  if (!form) return;

  form.querySelector('[name=name]').value = place.name || '';
  form.querySelector('[name=address]').value = place.formatted_address || '';
  form.querySelector('[name=place_id]').value = place.place_id || '';
  form.querySelector('[name=lat]').value = place.geometry.location.lat();
  form.querySelector('[name=lng]').value = place.geometry.location.lng();

  if (place.photos && place.photos.length > 0) {
    const photoUrl = place.photos[0].getUrl({ maxWidth: 800, maxHeight: 600 });
    form.querySelector('[name=photo_url]').value = photoUrl;
  }

  // カテゴリ自動判定
  const types = place.types || [];
  const categorySelect = form.querySelector('[name=category]');
  if (categorySelect) {
    if (types.some(t => ['lodging', 'hotel'].includes(t))) {
      categorySelect.value = 'hotel';
    } else if (types.some(t => ['restaurant', 'food', 'cafe', 'bar'].includes(t))) {
      categorySelect.value = 'gourmet';
    } else if (types.some(t => ['transit_station', 'airport', 'train_station', 'bus_station'].includes(t))) {
      categorySelect.value = 'transport';
    } else if (types.some(t => ['amusement_park', 'spa', 'aquarium', 'zoo'].includes(t))) {
      categorySelect.value = 'activity';
    } else {
      categorySelect.value = 'sightseeing';
    }
    if (window.handleCategoryChange) {
      window.handleCategoryChange(categorySelect.value);
    }
  }

  // プレビュー表示
  const previewBox = document.getElementById('selected-place-preview');
  if (previewBox) {
    previewBox.style.display = 'block';
    previewBox.innerHTML = `
      <div style="font-weight: 700; color: #0284C7; font-size: 0.95rem;">${place.name}</div>
      <div style="font-size: 0.8rem; color: #64748B;">${place.formatted_address || ''}</div>
    `;
  }
}
