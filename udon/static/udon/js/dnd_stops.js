/* Drag and Drop Stop List Reordering (Screen 3) */
document.addEventListener('DOMContentLoaded', () => {
  const stopList = document.getElementById('dnd-stop-list');
  if (!stopList) return;

  const tripId = stopList.getAttribute('data-trip-id');
  let draggedItem = null;

  // Get CSRF Token helper
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  function initDraggableItems() {
    const items = stopList.querySelectorAll('.dnd-stop-item');
    items.forEach(item => {
      item.setAttribute('draggable', 'true');

      item.addEventListener('dragstart', (e) => {
        draggedItem = item;
        item.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', item.getAttribute('data-stop-id'));
      });

      item.addEventListener('dragend', () => {
        draggedItem = null;
        item.classList.remove('dragging');
        items.forEach(i => i.classList.remove('drag-over'));
        saveNewOrder();
      });

      item.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const bounding = item.getBoundingClientRect();
        const offset = bounding.y + bounding.height / 2;
        if (e.clientY - offset > 0) {
          item.style.borderBottom = '3px solid #D99B26';
          item.style.borderTop = '';
        } else {
          item.style.borderTop = '3px solid #D99B26';
          item.style.borderBottom = '';
        }
      });

      item.addEventListener('dragleave', () => {
        item.style.borderTop = '';
        item.style.borderBottom = '';
      });

      item.addEventListener('drop', (e) => {
        e.preventDefault();
        item.style.borderTop = '';
        item.style.borderBottom = '';
        if (draggedItem && draggedItem !== item) {
          const bounding = item.getBoundingClientRect();
          const offset = bounding.y + bounding.height / 2;
          if (e.clientY - offset > 0) {
            item.after(draggedItem);
          } else {
            item.before(draggedItem);
          }
        }
      });
    });
  }

  function saveNewOrder() {
    const currentItems = stopList.querySelectorAll('.dnd-stop-item');
    const stopsPayload = [];

    currentItems.forEach((item, index) => {
      const stopId = item.getAttribute('data-stop-id');
      const order = index + 1;
      stopsPayload.push({
        id: parseInt(stopId),
        order: order
      });
    });

    if (tripId && stopsPayload.length > 0) {
      fetch(`/udon/api/trips/${tripId}/reorder-stops/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ stops: stopsPayload })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          showNotification('ストップの巡回順を更新しました ✨');
        }
      })
      .catch(err => console.error('Failed to update stop order', err));
    }
  }

  // Delete Stop Button
  stopList.addEventListener('click', (e) => {
    const deleteBtn = e.target.closest('.btn-delete-stop');
    if (deleteBtn) {
      e.stopPropagation();
      const stopItem = deleteBtn.closest('.dnd-stop-item');
      const stopId = stopItem.getAttribute('data-stop-id');

      if (confirm('この店舗を旅程から削除しますか？')) {
        if (tripId) {
          fetch(`/udon/api/trips/${tripId}/stops/${stopId}/delete/`, {
            method: 'POST',
            headers: {
              'X-CSRFToken': csrftoken,
            }
          })
          .then(res => res.json())
          .then(data => {
            if (data.status === 'ok') {
              stopItem.remove();
              showNotification('店舗を削除しました');
              saveNewOrder();
            }
          });
        } else {
          stopItem.remove();
        }
      }
    }
  });

  function showNotification(msg) {
    let toast = document.getElementById('app-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'app-toast';
      toast.className = 'toast-msg';
      toast.style.position = 'fixed';
      toast.style.bottom = '80px';
      toast.style.left = '50%';
      toast.style.transform = 'translateX(-50%)';
      toast.style.zIndex = '9999';
      toast.style.backgroundColor = '#1E2B37';
      toast.style.color = '#FFF';
      toast.style.padding = '8px 16px';
      toast.style.borderRadius = '9999px';
      toast.style.fontSize = '12px';
      toast.style.fontWeight = '700';
      toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 2200);
  }

  initDraggableItems();
});
