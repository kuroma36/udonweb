/**
 * モグミル (Mogumiru) - メインJavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // ESCキーでモーダルを閉じる
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal();
    }
  });
});

/**
 * カードをクリックしたときにモーダルを開く
 * @param {HTMLElement} cardEl 
 */
function openModalFromCard(cardEl) {
  const jsonScript = cardEl.querySelector('.card-json-data');
  if (!jsonScript) return;

  try {
    const data = JSON.parse(jsonScript.textContent);
    showModalWithData(data);
  } catch (err) {
    console.error('Failed to parse card data:', err);
  }
}

/**
 * モーダルを表示
 * @param {Object} data 
 */
function showModalWithData(data) {
  const modal = document.getElementById('itemModal');
  const body = document.getElementById('modalBody');
  if (!modal || !body) return;

  let tagsHtml = '';
  if (data.tags && data.tags.length > 0) {
    tagsHtml = `
      <div style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:1rem;">
        ${data.tags.map(t => `<span style="font-size:0.75rem; background:#F1F5F9; border:1px solid #CBD5E1; color:#475569; padding:0.2rem 0.55rem; border-radius:9999px;">#${escapeHtml(t)}</span>`).join('')}
      </div>
    `;
  }

  let mediaHtml = '';
  if (data.image) {
    mediaHtml = `
      <div style="width:100%; max-height:280px; overflow:hidden; border-radius:12px; margin-bottom:1.25rem;">
        <img src="${escapeHtml(data.image)}" alt="${escapeHtml(data.title)}" style="width:100%; height:100%; object-fit:cover;">
      </div>
    `;
  }

  let locationHtml = '';
  if (data.venue) {
    locationHtml = `
      <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; font-size:0.88rem;">
        <span style="font-weight:700; color:#64748B; min-width:70px;">📍 会場:</span>
        <span style="color:#0F172A; font-weight:600;">${escapeHtml(data.venue)} ${data.venue_address ? `<small style="color:#64748B; font-weight:normal;">(${escapeHtml(data.venue_address)})</small>` : ''}</span>
      </div>
    `;
  } else if (data.area) {
    locationHtml = `
      <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; font-size:0.88rem;">
        <span style="font-weight:700; color:#64748B; min-width:70px;">🗺️ エリア:</span>
        <span style="color:#0F172A; font-weight:600;">${escapeHtml(data.area)}</span>
      </div>
    `;
  }

  body.innerHTML = `
    ${mediaHtml}
    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.75rem; margin-bottom:0.5rem;">
      <div style="display:flex; align-items:center; gap:0.5rem;">
        <span style="font-weight:800; color:#E11D48; font-size:0.88rem;">${escapeHtml(data.brand)}</span>
        ${data.category ? `<span style="background:#F1F5F9; padding:0.2rem 0.5rem; border-radius:6px; font-size:0.78rem; font-weight:600;">${escapeHtml(data.category_icon)} ${escapeHtml(data.category)}</span>` : ''}
      </div>
      <span style="background:${data.status_color}; color:#fff; font-size:0.75rem; font-weight:800; padding:0.25rem 0.65rem; border-radius:9999px;">
        ${escapeHtml(data.status_label)}
      </span>
    </div>

    <h2 style="font-size:1.35rem; font-weight:800; color:#0F172A; margin-bottom:0.6rem; line-height:1.3;">${escapeHtml(data.title)}</h2>

    ${data.catchphrase ? `<p style="font-size:0.95rem; color:#E11D48; font-weight:600; margin-bottom:1rem; border-left:3px solid #E11D48; padding-left:0.6rem;">${escapeHtml(data.catchphrase)}</p>` : ''}

    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.9rem 1rem; margin-bottom:1.25rem;">
      <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; font-size:0.88rem;">
        <span style="font-weight:700; color:#64748B; min-width:70px;">📅 日程:</span>
        <span style="color:#0F172A; font-weight:600;">${escapeHtml(data.date_str)}</span>
      </div>
      ${data.price ? `
      <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; font-size:0.88rem;">
        <span style="font-weight:700; color:#64748B; min-width:70px;">🏷️ 価格:</span>
        <span style="color:#E11D48; font-weight:700;">${escapeHtml(data.price)}</span>
      </div>` : ''}
      ${locationHtml}
    </div>

    <div style="font-size:0.92rem; line-height:1.7; color:#334155; margin-bottom:1.25rem; white-space:pre-line;">
      ${escapeHtml(data.description)}
    </div>

    ${tagsHtml}

    <div style="display:flex; gap:0.75rem; margin-top:1.5rem; padding-top:1rem; border-top:1px solid #F1F5F9; justify-content:flex-end; flex-wrap:wrap;">
      ${data.official_url ? `
        <a href="${escapeHtml(data.official_url)}" target="_blank" rel="noopener noreferrer" style="background:#0F172A; color:#fff; font-size:0.85rem; font-weight:700; padding:0.55rem 1.1rem; border-radius:9999px; text-decoration:none;">
          🌐 公式サイト
        </a>` : ''}
      <a href="${escapeHtml(data.detail_url)}" style="background:#E11D48; color:#fff; font-size:0.85rem; font-weight:700; padding:0.55rem 1.25rem; border-radius:9999px; text-decoration:none;">
        詳細ページを見る &rarr;
      </a>
    </div>
  `;

  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

/**
 * モーダルを閉じる
 */
function closeModal(e) {
  if (e && e.target !== e.currentTarget && !e.target.classList.contains('modal-close-btn')) return;
  const modal = document.getElementById('itemModal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

/**
 * ソート選択時のURL更新
 * @param {string} val 
 */
function applySort(val) {
  const url = new URL(window.location.href);
  url.searchParams.set('sort', val);
  window.location.href = url.toString();
}

/**
 * HTMLエスケープヘルパー
 */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
