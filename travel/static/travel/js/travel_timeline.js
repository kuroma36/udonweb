/**
 * Travel Timeline & Transport Settings Controller (Plan 1 Implementation)
 */

document.addEventListener('DOMContentLoaded', function() {
  initTimelineDnd();
  initTransportModal();
  initAddStopModal();
});

// CSRF Token Helper
function getCsrfToken() {
  const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
  if (cookieMatch) return decodeURIComponent(cookieMatch[1]);
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// -------------------------------------------------------------
// 1. Drag and Drop Reordering
// -------------------------------------------------------------
function initTimelineDnd() {
  const container = document.getElementById('timeline-stops-container');
  if (!container) return;

  let draggedItem = null;

  const cards = container.querySelectorAll('.timeline-stop-card');
  cards.forEach(card => {
    card.setAttribute('draggable', 'true');

    card.addEventListener('dragstart', (e) => {
      draggedItem = card;
      card.style.opacity = '0.5';
      e.dataTransfer.effectAllowed = 'move';
    });

    card.addEventListener('dragend', () => {
      draggedItem = null;
      card.style.opacity = '1';
      saveNewStopOrder();
    });

    card.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const targetCard = e.target.closest('.timeline-stop-card');
      if (targetCard && targetCard !== draggedItem) {
        const rect = targetCard.getBoundingClientRect();
        const next = (e.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;
        container.insertBefore(draggedItem, next ? targetCard.nextSibling : targetCard);
      }
    });
  });
}

// Helper functions to get current tripId and dayId safely
function getTripId() {
  return window.TRAVEL_CONFIG?.tripId ||
         document.getElementById('timeline-stops-container')?.getAttribute('data-trip-id') ||
         document.querySelector('[name=trip_id]')?.value;
}

function getDayId() {
  return window.TRAVEL_CONFIG?.dayId ||
         document.getElementById('timeline-stops-container')?.getAttribute('data-day-id') ||
         document.querySelector('[name=day_id]')?.value;
}

function saveNewStopOrder() {
  const container = document.getElementById('timeline-stops-container');
  if (!container) return;

  const tripId = getTripId();
  const dayId = getDayId();
  const cards = container.querySelectorAll('.timeline-stop-card');

  const payload = [];
  cards.forEach((card, index) => {
    const stopId = card.getAttribute('data-stop-id');
    const newOrder = index + 1;
    card.querySelector('.stop-order-number').textContent = newOrder;
    payload.push({ id: parseInt(stopId), order: newOrder });
  });

  if (payload.length > 0 && tripId) {
    fetch(`/travel/api/trips/${tripId}/reorder-stops/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ day_id: dayId, stops: payload })
    })
    .then(async res => {
      let data;
      try { data = await res.json(); } catch(e) { throw new Error(`サーバーエラー (HTTP ${res.status})`); }
      if (!res.ok || data.status !== 'ok') {
        throw new Error((data && data.message) || '順序保存に失敗しました');
      }
      return data;
    })
    .then(() => {
      window.location.reload();
    })
    .catch(err => console.error('Order save error:', err));
  }
}

// -------------------------------------------------------------
// 2. Transport Settings Modal (Plan 1)
// -------------------------------------------------------------
let currentEditingStopId = null;

function initTransportModal() {
  const depInput = document.getElementById('transport-dep-time');
  const arrInput = document.getElementById('transport-arr-time');

  if (depInput && arrInput) {
    depInput.addEventListener('input', calculateLiveDuration);
    arrInput.addEventListener('input', calculateLiveDuration);
  }

  // 交通手段変更時
  const modeSelect = document.getElementById('transport-mode-select');
  if (modeSelect) {
    modeSelect.addEventListener('change', updateTransportHelperUi);
  }
}

// 所要時間のリアルタイム自動計算
function calculateLiveDuration() {
  const depVal = document.getElementById('transport-dep-time')?.value;
  const arrVal = document.getElementById('transport-arr-time')?.value;
  const previewEl = document.getElementById('transport-duration-preview');
  const hiddenTimeText = document.getElementById('transport-time-text-input');

  if (!depVal || !arrVal || !previewEl) return;

  const [h1, m1] = depVal.split(':').map(Number);
  const [h2, m2] = arrVal.split(':').map(Number);

  let diffMinutes = (h2 * 60 + m2) - (h1 * 60 + m1);
  if (diffMinutes < 0) {
    diffMinutes += 24 * 60; // 日跨ぎ
  }

  const hours = Math.floor(diffMinutes / 60);
  const minutes = diffMinutes % 60;

  let text = '';
  if (hours > 0 && minutes > 0) {
    text = `${hours}時間${minutes}分`;
  } else if (hours > 0) {
    text = `${hours}時間`;
  } else {
    text = `${minutes}分`;
  }

  previewEl.textContent = `所要時間: ${text}（自動計算）`;
  previewEl.style.display = 'block';
  if (hiddenTimeText) {
    hiddenTimeText.value = text;
  }
}

// 外部乗換案内ディープリンク生成
function openTransitSearchUrl(originName, destName) {
  if (!originName || !destName) return;
  const url = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(originName)}&destination=${encodeURIComponent(destName)}&travelmode=transit`;
  window.open(url, '_blank');
}

function openTransportModal(stopId, currentMode, depTime, arrTime, timeText, memo, originName, destName) {
  currentEditingStopId = stopId;
  const modal = document.getElementById('transport-modal');
  if (!modal) return;

  const mode = currentMode || 'car';
  const modeSelect = document.getElementById('transport-mode-select');
  if (modeSelect) modeSelect.value = mode;

  document.getElementById('transport-dep-time').value = depTime || '';
  document.getElementById('transport-arr-time').value = arrTime || '';
  document.getElementById('transport-memo-input').value = memo || '';
  document.getElementById('transport-time-text-input').value = timeText || '';

  // 次のスポット名（乗換案内用）を TRAVEL_STOPS_DATA から安全に解決
  const stops = window.TRAVEL_STOPS_DATA || [];
  const currentIndex = stops.findIndex(s => s.id === stopId);
  const nextStop = currentIndex >= 0 && currentIndex < stops.length - 1 ? stops[currentIndex + 1] : null;
  const currentStop = currentIndex >= 0 ? stops[currentIndex] : null;
  const actualOriginName = originName || currentStop?.name || '';
  const actualDestName = destName || nextStop?.name || '';

  // 乗換案内ボタンの設定
  const transitBtn = document.getElementById('btn-open-transit-search');
  if (transitBtn) {
    if (actualDestName) {
      transitBtn.style.display = 'inline-flex';
      transitBtn.onclick = () => openTransitSearchUrl(actualOriginName, actualDestName);
    } else {
      transitBtn.style.display = 'none';
    }
  }

  updateTransportHelperUi();
  calculateLiveDuration();

  // 手動入力された出発・到着時刻がない場合
  if (!depTime && !arrTime) {
    const previewEl = document.getElementById('transport-duration-preview');
    if (previewEl) {
      if (timeText) {
        previewEl.textContent = `所要時間: ${timeText}（${mode === 'car' ? '車ルート自動計算' : '設定済み'}）`;
        previewEl.style.display = 'block';
      } else if (mode === 'car') {
        previewEl.textContent = '🚗 車のルート・所要時間は地図から自動計算されます';
        previewEl.style.display = 'block';
      } else {
        previewEl.style.display = 'none';
      }
    }
  }

  modal.classList.add('is-active');
}

function closeTransportModal() {
  const modal = document.getElementById('transport-modal');
  if (modal) modal.classList.remove('is-active');
  currentEditingStopId = null;
}

function saveTransportSettings() {
  if (!currentEditingStopId) return;

  const tripId = getTripId();
  if (!tripId) {
    alert('旅行情報が見つかりません');
    return;
  }

  const form = document.getElementById('transport-settings-form');
  const formData = new FormData(form);

  fetch(`/travel/api/trips/${tripId}/stops/${currentEditingStopId}/update-transport/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
    },
    body: formData
  })
  .then(async res => {
    let data;
    try { data = await res.json(); } catch(e) { throw new Error(`サーバーエラー (HTTP ${res.status})`); }
    if (!res.ok || data.status !== 'ok') {
      throw new Error((data && data.message) || '保存に失敗しました');
    }
    return data;
  })
  .then(() => {
    closeTransportModal();
    window.location.reload();
  })
  .catch(err => {
    alert(err.message || 'エラーが発生しました');
  });
}

function updateTransportHelperUi() {
  const mode = document.getElementById('transport-mode-select')?.value;
  const transitSection = document.getElementById('transit-helper-section');
  const carAutoHint = document.getElementById('car-auto-hint');
  const memoInput = document.getElementById('transport-memo-input');

  if (carAutoHint) {
    carAutoHint.style.display = (mode === 'car') ? 'block' : 'none';
  }

  if (transitSection) {
    if (['train', 'flight', 'bus', 'boat'].includes(mode)) {
      transitSection.style.display = 'block';
      if (mode === 'flight') {
        memoInput.placeholder = '例: ANA 55便 24A席 / 予約番号 ABC123';
      } else if (mode === 'train') {
        memoInput.placeholder = '例: のぞみ15号 7号車12番A席';
      } else {
        memoInput.placeholder = '便名・予約番号・乗り場メモ';
      }
    } else {
      transitSection.style.display = 'none';
      memoInput.placeholder = '移動に関するメモ（レンタカー会社、駐車場など）';
    }
  }
}

// -------------------------------------------------------------
// 3. Add Stop & Delete Stop
// -------------------------------------------------------------
function initAddStopModal() {
  const form = document.getElementById('add-stop-form');
  if (!form) return;

  const placesInput = document.getElementById('places-autocomplete-input');

  // 入力ボックスの文字列とhidden[name=name]を即時連動（手動入力対応）
  if (placesInput) {
    placesInput.addEventListener('input', function() {
      const nameField = form.querySelector('[name=name]');
      if (nameField) nameField.value = this.value;
    });

    // Enterキーの誤送信防止＆候補選択サポート
    placesInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault(); // フォーム即時送信を防止

        // Google Placesの候補がキーボードで選択されているかチェック
        const selectedPac = document.querySelector('.pac-item-selected');
        if (!selectedPac) {
          // 候補未選択時: 入力テキストを名前としてフォーム送信
          const nameField = form.querySelector('[name=name]');
          if (nameField && !nameField.value.trim()) {
            nameField.value = placesInput.value.trim();
          }
          if (nameField && nameField.value.trim()) {
            setTimeout(() => {
              if (typeof form.requestSubmit === 'function') {
                form.requestSubmit();
              } else {
                form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
              }
            }, 50);
          }
        }
      }
    });
  }

  // スポット追加フォーム送信ハンドラ
  form.addEventListener('submit', function(e) {
    e.preventDefault();

    const tripId = getTripId();
    const dayId = getDayId();

    if (!tripId) {
      alert('旅行情報が取得できませんでした。ページを再読み込みしてください。');
      return;
    }

    const nameField = form.querySelector('[name=name]');
    if ((!nameField || !nameField.value.trim()) && placesInput && placesInput.value.trim()) {
      if (nameField) nameField.value = placesInput.value.trim();
    }

    if (!nameField || !nameField.value.trim()) {
      alert('スポット名を入力してください');
      placesInput?.focus();
      return;
    }

    const formData = new FormData(form);
    if (!formData.get('day_id') && dayId) {
      formData.append('day_id', dayId);
    }
    if (!formData.get('trip_id') && tripId) {
      formData.append('trip_id', tripId);
    }

    const submitBtn = form.querySelector('button[type=submit]');
    if (submitBtn) submitBtn.disabled = true;

    fetch(`/travel/api/trips/${tripId}/add-stop/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
      },
      body: formData
    })
    .then(async res => {
      let data;
      try {
        data = await res.json();
      } catch (e) {
        throw new Error(`サーバーエラー (HTTP ${res.status})`);
      }
      if (!res.ok || data.status !== 'ok') {
        throw new Error((data && data.message) || `スポットの追加に失敗しました (HTTP ${res.status})`);
      }
      return data;
    })
    .then(() => {
      closeAddStopModal();
      window.location.reload();
    })
    .catch(err => {
      alert(err.message || 'エラーが発生しました');
      if (submitBtn) submitBtn.disabled = false;
    });
  });
}

function openAddStopModal() {
  const modal = document.getElementById('add-stop-modal');
  if (modal) {
    modal.classList.add('is-active');

    // Places Autocomplete を確実に初期化し、現在のマップ表示領域（旅行先エリア）にバイアス設定
    if (window.initPlacesAutocomplete) {
      window.initPlacesAutocomplete();
    }
    if (window.autocompleteInstance && window.mapInstance && window.mapInstance.getBounds()) {
      window.autocompleteInstance.setBounds(window.mapInstance.getBounds());
    }

    // フォームと検索欄のクリア
    const input = document.getElementById('places-autocomplete-input');
    if (input) {
      input.value = '';
      setTimeout(() => input.focus(), 150);
    }

    const preview = document.getElementById('selected-place-preview');
    if (preview) {
      preview.style.display = 'none';
      preview.innerHTML = '';
    }

    const form = document.getElementById('add-stop-form');
    if (form) {
      const nameInput = form.querySelector('[name=name]');
      if (nameInput) nameInput.value = '';
      const addressInput = form.querySelector('[name=address]');
      if (addressInput) addressInput.value = '';
      const latInput = form.querySelector('[name=lat]');
      if (latInput) latInput.value = '';
      const lngInput = form.querySelector('[name=lng]');
      if (lngInput) lngInput.value = '';
      const placeIdInput = form.querySelector('[name=place_id]');
      if (placeIdInput) placeIdInput.value = '';
      const photoInput = form.querySelector('[name=photo_url]');
      if (photoInput) photoInput.value = '';
      const arrivalInput = form.querySelector('[name=arrival_time]');
      if (arrivalInput) arrivalInput.value = '';
      const memoInput = form.querySelector('[name=memo]');
      if (memoInput) memoInput.value = '';

      const catSelect = form.querySelector('[name=category]');
      if (catSelect) {
        catSelect.value = 'sightseeing';
        handleCategoryChange('sightseeing');
      }

      const submitBtn = form.querySelector('button[type=submit]');
      if (submitBtn) submitBtn.disabled = false;
    }
  }
}

function handleCategoryChange(category) {
  const syncOptions = document.getElementById('hotel-sync-options');
  if (syncOptions) {
    if (category === 'hotel') {
      syncOptions.style.display = 'block';
    } else {
      syncOptions.style.display = 'none';
    }
  }
}
window.handleCategoryChange = handleCategoryChange;

function closeAddStopModal() {
  const modal = document.getElementById('add-stop-modal');
  if (modal) modal.classList.remove('is-active');
}

function deleteStop(stopId, stopName, isPaired = false) {
  let msg = `「${stopName}」をこの日程から削除しますか？`;
  if (isPaired) {
    msg = `「${stopName}」は連動している宿泊スポットです。\n削除すると、前日または翌日の連動スポットも一緒に削除されます。\n\n本当に削除しますか？`;
  }
  if (!confirm(msg)) return;

  const tripId = getTripId();
  if (!tripId) {
    alert('旅行情報が見つかりません');
    return;
  }

  fetch(`/travel/api/trips/${tripId}/stops/${stopId}/delete/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
    }
  })
  .then(async res => {
    let data;
    try { data = await res.json(); } catch(e) { throw new Error(`サーバーエラー (HTTP ${res.status})`); }
    if (!res.ok || data.status !== 'ok') {
      throw new Error((data && data.message) || '削除に失敗しました');
    }
    return data;
  })
  .then(() => {
    window.location.reload();
  })
  .catch(err => alert(err.message || 'エラーが発生しました'));
}
window.deleteStop = deleteStop;
