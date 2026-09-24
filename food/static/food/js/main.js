/**
 * モグミル (Mogumiru) - Web食ニュースキュレーション用 JavaScript
 */

/**
 * 画面上からWeb食ニュースの最新取得をトリガーする
 */
async function triggerNewsFetch() {
  const btn = document.getElementById('btnFetchNews');
  if (!btn || btn.classList.contains('loading')) return;

  btn.classList.add('loading');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<span class="fetch-icon">🔄</span> <span class="fetch-text">Webから収集中...</span>';

  showToast('Web上の最新食ニュース・イベント記事を巡回取得しています...');

  try {
    // CSRFトークンの取得
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfInput ? csrfInput.value : '';

    const resp = await fetch('/food/api/fetch/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
    });

    const data = await resp.json();

    if (resp.ok && data.status === 'ok') {
      showToast(`🎉 ${data.message}`);
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } else {
      showToast(`⚠️ 取得に失敗しました: ${data.message || '不明なエラー'}`);
      btn.classList.remove('loading');
      btn.innerHTML = originalText;
    }
  } catch (err) {
    console.error('Fetch error:', err);
    showToast('⚠️ 通信エラーが発生しました。接続を確認してください。');
    btn.classList.remove('loading');
    btn.innerHTML = originalText;
  }
}

/**
 * 配信元メディアの絞り込み変更
 */
function applySourceFilter(sourceName) {
  const url = new URL(window.location.href);
  if (sourceName) {
    url.searchParams.set('source', sourceName);
  } else {
    url.searchParams.delete('source');
  }
  url.searchParams.delete('page'); // ページを1に戻す
  window.location.href = url.toString();
}

/**
 * トースト通知の表示
 */
function showToast(msg) {
  let toast = document.getElementById('fetchToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'fetchToast';
    toast.className = 'fetch-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.display = 'block';

  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    toast.style.display = 'none';
  }, 4000);
}
