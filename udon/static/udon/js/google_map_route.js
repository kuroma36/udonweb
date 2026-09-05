/* Google Maps JS: Dynamic Accurate Driving Route Durations & Parabolic Dashed Arcs */

// Helper to compute driving minutes from coordinates (Kagawa road factors)
function calculateDrivingMinutes(p1, p2) {
  const R = 6371; // Earth radius in km
  const dLat = (p2.lat - p1.lat) * Math.PI / 180;
  const dLng = (p2.lng - p1.lng) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distKm = R * c;
  const roadKm = distKm * 1.35;
  const minutes = Math.round((roadKm / 35.0) * 60);
  return Math.max(5, minutes);
}

// Generates smooth Bézier curve points between two coordinates
function generateCurvedArc(p1, p2, numPoints = 30, curvature = 0.16) {
  const points = [];
  const dx = p2.lng - p1.lng;
  const dy = p2.lat - p1.lat;
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) return { points: [p1, p2], midPoint: p1 };

  let nx = -dy / dist;
  let ny = dx / dist;

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

function initGoogleMapRoute() {
  const mapElement = document.getElementById('map-container');
  if (!mapElement) return;

  const rawStopsData = mapElement.getAttribute('data-stops');
  let stops = [];
  try {
    stops = JSON.parse(rawStopsData || '[]');
  } catch (e) {
    console.error('Failed to parse stops data', e);
  }

  if (typeof google !== 'undefined' && google.maps) {
    const defaultCenter = { lat: 34.28, lng: 133.92 };
    
    // Modern Japanese Washi Map Style
    const map = new google.maps.Map(mapElement, {
      zoom: 11,
      center: defaultCenter,
      gestureHandling: 'greedy', // Allow natural 1-finger panning on mobile/touch without 'Use two fingers' prompt
      disableDefaultUI: true,
      zoomControl: false,
      mapTypeControl: false,
      streetViewControl: false,
      styles: [
        { featureType: "all", elementType: "geometry", stylers: [{ color: "#f5efe6" }] },
        { featureType: "water", elementType: "geometry", stylers: [{ color: "#cde4f0" }] },
        { featureType: "road", elementType: "geometry", stylers: [{ color: "#ffffff" }] },
        { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#fcd6a4" }] },
        { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#dbe8d8" }] },
        { featureType: "poi.business", stylers: [{ visibility: "off" }] }
      ]
    });
    window.googleMapInstance = map;

    const tripId = mapElement.getAttribute('data-trip-id') || (stops.length > 0 && stops[0].trip_id);
    const bounds = new google.maps.LatLngBounds();
    const segmentColors = ['#1E2B37', '#D99B26', '#C84B31', '#2E7D5B', '#8E44AD', '#2980B9', '#D35400'];
    const validStops = stops.filter(s => s.lat && s.lng);

    // 1. Draw Numbered Pins
    validStops.forEach((stop, index) => {
      const pos = { lat: parseFloat(stop.lat), lng: parseFloat(stop.lng) };
      bounds.extend(pos);
      const color = segmentColors[index % segmentColors.length];

      const markerSvg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="34" height="42" viewBox="0 0 34 42">
          <path d="M17 0C7.6 0 0 7.6 0 17C0 29.8 17 42 17 42S34 29.8 34 17C34 7.6 26.4 0 17 0Z" fill="${color}" stroke="#FFFFFF" stroke-width="2.5"/>
          <circle cx="17" cy="15" r="10" fill="${color}"/>
          <text x="17" y="19" font-size="13" font-weight="900" fill="#FFFFFF" text-anchor="middle" font-family="-apple-system, sans-serif">${stop.order}</text>
        </svg>
      `;

      const marker = new google.maps.Marker({
        position: pos,
        map: map,
        title: `${stop.order}. ${stop.name}`,
        zIndex: 100 + index,
        icon: {
          url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(markerSvg),
          scaledSize: new google.maps.Size(34, 42),
          anchor: new google.maps.Point(17, 42),
        },
      });

      const currentTripId = stop.trip_id || tripId;
      const detailUrl = currentTripId ? `/trips/${currentTripId}/shops/${stop.shop_id}/` : `/shops/${stop.shop_id}/`;

      const infoWindow = new google.maps.InfoWindow({
        content: `
          <div style="font-family: -apple-system, sans-serif; min-width: 170px; padding: 4px;">
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
              padding: 4px 12px;
              border-radius: 9999px;
              font-size: 11px;
              font-weight: 700;
              text-decoration: none;
            ">店舗詳細・レビューへ →</a>
          </div>
        `
      });

      marker.addListener('click', () => {
        infoWindow.open(map, marker);
      });
    });

    // 2. Draw Gentle Parabolic Dashed Arcs with Dynamic Duration Calculation
    if (validStops.length > 1) {
      map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });

      const distanceMatrixService = new google.maps.DistanceMatrixService();

      for (let i = 0; i < validStops.length - 1; i++) {
        const fromStop = validStops[i];
        const toStop = validStops[i + 1];
        const fromPos = { lat: parseFloat(fromStop.lat), lng: parseFloat(fromStop.lng) };
        const toPos = { lat: parseFloat(toStop.lat), lng: parseFloat(toStop.lng) };
        const segmentColor = segmentColors[i % segmentColors.length];

        // Generate gentle parabolic curve points
        const arc = generateCurvedArc(fromPos, toPos, 30, 0.16);

        // Dashed line styling
        const lineSymbol = {
          path: 'M 0,-1.2 0,1.2',
          strokeOpacity: 0.95,
          strokeWeight: 3.5,
          scale: 2.5,
          strokeColor: segmentColor
        };

        // Draw Parabolic Dashed Polyline
        new google.maps.Polyline({
          path: arc.points,
          strokeOpacity: 0,
          icons: [{
            icon: lineSymbol,
            offset: '0',
            repeat: '11px'
          }],
          map: map,
          zIndex: 10 + i
        });

        // Compute dynamic driving minutes fallback
        const calculatedMinutes = calculateDrivingMinutes(fromPos, toPos);

        // Query Distance Matrix with Real-Time Traffic support
        distanceMatrixService.getDistanceMatrix({
          origins: [fromPos],
          destinations: [toPos],
          travelMode: google.maps.TravelMode.DRIVING,
          drivingOptions: {
            departureTime: new Date(),
            trafficModel: google.maps.TrafficModel.BEST_GUESS
          }
        }, ((segmentIndex, apexPos, color, destStop, fallbackMins) => (response, status) => {
          let durationText = `${fallbackMins}分`;

          if (status === 'OK' && response.rows[0]?.elements[0]?.status === 'OK') {
            const elem = response.rows[0].elements[0];
            // Prefer real-time traffic duration if available, otherwise normal duration
            const duration = elem.duration_in_traffic || elem.duration;
            let formatted = duration.text.replace(' hours', '時間').replace(' mins', '分').replace(' min', '分').replace(/\s+/g, '');
            if (formatted) {
              durationText = formatted;
            }
          }

          const badgeWidth = durationText.length > 3 ? 58 : 46;

          // Render Sleek Micro-Pill Badge at the Apex of the Parabolic Arc
          const labelSvg = `
            <svg xmlns="http://www.w3.org/2000/svg" width="${badgeWidth}" height="20" viewBox="0 0 ${badgeWidth} 20">
              <rect x="1" y="1" width="${badgeWidth - 2}" height="18" rx="9" fill="${color}" fill-opacity="0.92" stroke="#FFFFFF" stroke-width="1.5"/>
              <text x="${badgeWidth / 2}" y="13.5" font-size="9.5" font-weight="800" fill="#FFFFFF" text-anchor="middle" font-family="-apple-system, sans-serif">${durationText}</text>
            </svg>
          `;

          new google.maps.Marker({
            position: apexPos,
            map: map,
            zIndex: 50 + segmentIndex,
            icon: {
              url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(labelSvg),
              scaledSize: new google.maps.Size(badgeWidth, 20),
              anchor: new google.maps.Point(badgeWidth / 2, 10),
            },
          });
        })(i, arc.midPoint, segmentColor, toStop, calculatedMinutes));
      }
    } else if (validStops.length === 1) {
      map.setCenter({ lat: parseFloat(validStops[0].lat), lng: parseFloat(validStops[0].lng) });
      map.setZoom(13);
    }

    // Current Location Marker state (Google Maps)
    let googleUserMarker = null;
    let googleUserAccuracyCircle = null;

    function fitAllRouteStopsGoogle() {
      if (validStops.length > 1) {
        map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });
      } else if (validStops.length === 1) {
        map.panTo({ lat: parseFloat(validStops[0].lat), lng: parseFloat(validStops[0].lng) });
        map.setZoom(14);
      }
      const currentLocBtn = document.getElementById('map-current-location-btn');
      if (currentLocBtn) currentLocBtn.classList.remove('active');
    }

    // 1. Fit Route Button
    const fitRouteBtn = document.getElementById('map-fit-route-btn') || document.getElementById('map-locate-btn');
    if (fitRouteBtn && validStops.length > 0) {
      fitRouteBtn.addEventListener('click', fitAllRouteStopsGoogle);
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

            const userPos = {
              lat: position.coords.latitude,
              lng: position.coords.longitude,
            };

            // Create or update marker
            if (!googleUserMarker) {
              googleUserMarker = new google.maps.Marker({
                position: userPos,
                map: map,
                title: '現在地',
                zIndex: 999,
                icon: {
                  path: google.maps.SymbolPath.CIRCLE,
                  scale: 8,
                  fillColor: '#1976D2',
                  fillOpacity: 1,
                  strokeColor: '#FFFFFF',
                  strokeWeight: 2.5,
                },
              });

              googleUserAccuracyCircle = new google.maps.Circle({
                map: map,
                center: userPos,
                radius: Math.min(position.coords.accuracy || 30, 200),
                fillColor: '#1976D2',
                fillOpacity: 0.15,
                strokeColor: '#1976D2',
                strokeOpacity: 0.35,
                strokeWeight: 1,
              });

              const infoWindow = new google.maps.InfoWindow({
                content: '<div style="font-weight:bold;font-size:13px;color:#1976D2;padding:2px;">📍 現在地</div>',
              });
              infoWindow.open(map, googleUserMarker);
            } else {
              googleUserMarker.setPosition(userPos);
              if (googleUserAccuracyCircle) {
                googleUserAccuracyCircle.setCenter(userPos);
                googleUserAccuracyCircle.setRadius(Math.min(position.coords.accuracy || 30, 200));
              }
            }

            // Fit bounds to include both current user location and other route stops
            if (validStops.length > 0) {
              const combinedBounds = new google.maps.LatLngBounds();
              combinedBounds.extend(userPos);
              validStops.forEach((stop) => {
                combinedBounds.extend({
                  lat: parseFloat(stop.lat),
                  lng: parseFloat(stop.lng),
                });
              });
              map.fitBounds(combinedBounds, { top: 60, right: 60, bottom: 80, left: 60 });
            } else {
              map.panTo(userPos);
              if (map.getZoom() < 13) {
                map.setZoom(13);
              }
            }
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

    if (window.initGooglePlacesMapSearch) {
      window.initGooglePlacesMapSearch();
    }
  }
}
