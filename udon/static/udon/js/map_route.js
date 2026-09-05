/* Leaflet Map: Dynamic Accurate Driving Route Durations & Parabolic Dashed Arcs */

function calculateDrivingMinutesLeaflet(p1, p2) {
  const R = 6371; // Earth radius in km
  const dLat = (p2[0] - p1[0]) * Math.PI / 180;
  const dLng = (p2[1] - p1[1]) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(p1[0] * Math.PI / 180) * Math.cos(p2[0] * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distKm = R * c;
  const roadKm = distKm * 1.35;
  const minutes = Math.round((roadKm / 35.0) * 60);
  return Math.max(5, minutes);
}

function generateCurvedArcLeaflet(p1, p2, numPoints = 30, curvature = 0.16) {
  const points = [];
  const dx = p2[1] - p1[1];
  const dy = p2[0] - p1[0];
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) return { points: [p1, p2], midPoint: p1 };

  let nx = -dy / dist;
  let ny = dx / dist;

  if (ny < 0) {
    nx = -nx;
    ny = -ny;
  }

  const offset = dist * curvature;
  const midLat = (p1[0] + p2[0]) / 2;
  const midLng = (p1[1] + p2[1]) / 2;
  const controlPoint = [midLat + ny * offset, midLng + nx * offset];

  for (let i = 0; i <= numPoints; i++) {
    const t = i / numPoints;
    const invT = 1 - t;
    const lat = invT * invT * p1[0] + 2 * invT * t * controlPoint[0] + t * t * p2[0];
    const lng = invT * invT * p1[1] + 2 * invT * t * controlPoint[1] + t * t * p2[1];
    points.push([lat, lng]);
  }

  const apex = [
    0.25 * p1[0] + 0.5 * controlPoint[0] + 0.25 * p2[0],
    0.25 * p1[1] + 0.5 * controlPoint[1] + 0.25 * p2[1]
  ];

  return { points, midPoint: apex };
}

window.initLeafletMap = function() {
  const mapElement = document.getElementById('map-container');
  if (!mapElement || mapElement.hasAttribute('data-leaflet-initialized')) return;
  mapElement.setAttribute('data-leaflet-initialized', 'true');
  mapElement.innerHTML = '';

  const rawStopsData = mapElement.getAttribute('data-stops');
  let stops = [];
  try {
    stops = JSON.parse(rawStopsData || '[]');
  } catch (e) {
    console.error('Failed to parse stops data', e);
  }

  const defaultCenter = [34.25, 133.90];
  const map = L.map('map-container', {
    center: defaultCenter,
    zoom: 11,
    zoomControl: false,
    attributionControl: false
  });
  window.leafletMapInstance = map;

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd',
  }).addTo(map);

  const tripId = mapElement.getAttribute('data-trip-id') || (stops.length > 0 && stops[0].trip_id);
  const latLngs = [];
  const markers = [];
  const segmentColors = ['#1E2B37', '#D99B26', '#C84B31', '#2E7D5B', '#8E44AD', '#2980B9', '#D35400'];

  stops.forEach((stop, index) => {
    if (!stop.lat || !stop.lng) return;
    const latLng = [stop.lat, stop.lng];
    latLngs.push(latLng);

    const pinColor = segmentColors[index % segmentColors.length];

    const customIcon = L.divIcon({
      className: 'custom-pin-wrapper',
      html: `
        <div style="
          width: 32px;
          height: 32px;
          background-color: ${pinColor};
          border: 2.5px solid #FFFFFF;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
        ">
          <span style="
            transform: rotate(45deg);
            color: #FFFFFF;
            font-size: 13px;
            font-weight: 800;
            font-family: inherit;
          ">${stop.order}</span>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
      popupAnchor: [0, -32],
    });

    const marker = L.marker(latLng, { icon: customIcon }).addTo(map);
    
    const currentTripId = stop.trip_id || tripId;
    const detailUrl = currentTripId ? `/trips/${currentTripId}/shops/${stop.shop_id}/` : `/shops/${stop.shop_id}/`;

    const popupContent = `
      <div style="font-family: var(--font-family); min-width: 160px; padding: 4px;">
        <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px; color: #2A2421;">
          ${stop.order}. ${stop.name}
        </div>
        <div style="font-size: 12px; color: #D99B26; font-weight: 700; margin-bottom: 6px;">
          ★ ${stop.score || '未評価'}
        </div>
        <a href="${detailUrl}" style="
          display: inline-block;
          background: #1E2B37;
          color: #FFFFFF;
          padding: 4px 10px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          text-decoration: none;
        ">店舗詳細・レビューへ →</a>
      </div>
    `;
    marker.bindPopup(popupContent);
    markers.push(marker);
  });

  // Draw Parabolic Dashed Arcs with Dynamic Duration
  if (latLngs.length > 1) {
    const allBounds = L.latLngBounds(latLngs);

    for (let i = 0; i < latLngs.length - 1; i++) {
      const p1 = latLngs[i];
      const p2 = latLngs[i + 1];
      const segmentColor = segmentColors[i % segmentColors.length];
      const mins = calculateDrivingMinutesLeaflet(p1, p2);
      const durationText = `${mins}分`;

      const arc = generateCurvedArcLeaflet(p1, p2, 30, 0.16);

      // Draw Dashed Curve
      L.polyline(arc.points, {
        color: segmentColor,
        weight: 3.5,
        opacity: 0.9,
        dashArray: '7, 8',
        lineCap: 'round',
      }).addTo(map);

      // Draw Label Badge at the Apex of the Curve
      const labelIcon = L.divIcon({
        className: 'route-label-wrapper',
        html: `
          <div style="
            background: ${segmentColor};
            color: #FFFFFF;
            padding: 2px 7px;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 800;
            white-space: nowrap;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            border: 1.2px solid #FFFFFF;
            transform: translate(-50%, -50%);
          ">${durationText}</div>
        `,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });
      L.marker(arc.midPoint, { icon: labelIcon, interactive: false }).addTo(map);
    }

    map.fitBounds(allBounds, { padding: [50, 50] });
  } else if (latLngs.length === 1) {
    map.setView(latLngs[0], 13);
  }

  // Current Location Marker state
  let userLocationMarker = null;

  function fitAllRouteStops() {
    if (latLngs.length > 1) {
      map.fitBounds(L.latLngBounds(latLngs), { padding: [50, 50], duration: 0.8 });
    } else if (latLngs.length === 1) {
      map.flyTo(latLngs[0], 14, { duration: 0.8 });
    }
    const currentLocBtn = document.getElementById('map-current-location-btn');
    if (currentLocBtn) currentLocBtn.classList.remove('active');
  }

  // 1. Fit Route Button
  const fitRouteBtn = document.getElementById('map-fit-route-btn') || document.getElementById('map-locate-btn');
  if (fitRouteBtn && latLngs.length > 0) {
    fitRouteBtn.addEventListener('click', fitAllRouteStops);
  }

  // 2. Current Location (GPS) Button
  const currentLocBtn = document.getElementById('map-current-location-btn');
  if (currentLocBtn) {
    currentLocBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        alert('お使いのブラウザは現在地取得に対応していません。');
        return;
      }

      currentLocBtn.classList.add('locating');

      navigator.geolocation.getCurrentPosition(
        (position) => {
          currentLocBtn.classList.remove('locating');
          currentLocBtn.classList.add('active');

          const userLat = position.coords.latitude;
          const userLng = position.coords.longitude;
          const userLatLng = [userLat, userLng];

          // Create or update current location marker
          if (!userLocationMarker) {
            const userIcon = L.divIcon({
              className: 'user-location-marker-container',
              html: `
                <div class="user-location-pulse"></div>
                <div class="user-location-dot"></div>
              `,
              iconSize: [22, 22],
              iconAnchor: [11, 11],
              popupAnchor: [0, -12],
            });

            userLocationMarker = L.marker(userLatLng, {
              icon: userIcon,
              zIndexOffset: 1000,
            }).addTo(map);

            userLocationMarker.bindPopup(`
              <div style="font-family: inherit; font-size: 13px; font-weight: 700; color: #1976D2; padding: 2px;">
                📍 現在地
              </div>
            `);
          } else {
            userLocationMarker.setLatLng(userLatLng);
          }

          // Fit bounds to include both current user location and other route stops
          if (latLngs.length > 0) {
            const allPoints = [userLatLng, ...latLngs];
            const combinedBounds = L.latLngBounds(allPoints);
            map.fitBounds(combinedBounds, { padding: [60, 60], maxZoom: 15, duration: 1.0 });
          } else {
            map.flyTo(userLatLng, 13, { duration: 1.0 });
          }

          // Auto open popup briefly
          userLocationMarker.openPopup();
        },
        (error) => {
          currentLocBtn.classList.remove('locating');
          let msg = '現在地を取得できませんでした。';
          if (error.code === error.PERMISSION_DENIED) {
            msg = '位置情報の利用が許可されていません。ブラウザの設定で位置情報を許可してください。';
          } else if (error.code === error.TIMEOUT) {
            msg = '位置情報の取得がタイムアウトしました。電波の良い場所で再度お試しください。';
          }
          alert(msg);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 30000,
        }
      );
    });
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (typeof google === 'undefined' || !window.GOOGLE_MAPS_ACTIVE) {
    window.initLeafletMap();
  }
});
