// ── Toast ──
function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Format date from diario fields ──
function formatWatchDate(row) {
  const ano = row.ano_assistido || (row.assistido_em && new Date(row.assistido_em).getFullYear());
  const mes = row.mes_assistido || (row.assistido_em && new Date(row.assistido_em).getMonth() + 1);
  const dia = row.dia_assistido || (row.assistido_em && new Date(row.assistido_em).getDate());
  if (!ano) return '';
  let s = String(ano);
  if (mes) s = monthName(mes) + '/' + s;
  if (dia) s = String(dia).padStart(2, '0') + '/' + s;
  return s;
}

function monthName(m) {
  return ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][m-1] || m;
}

function monthFull(m) {
  return ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][m-1] || m;
}

// ── Progress pct ──
function pct(watched, total) {
  if (!total) return 0;
  return Math.round(watched / total * 100);
}

// ── Loading HTML ──
function loadingHtml() {
  return `<div class="loading"><div class="spinner"></div> carregando...</div>`;
}

// ── Empty state ──
function emptyState(icon, title, desc, btnHtml = '') {
  return `<div class="empty-state">
    <div class="empty-icon">${icon}</div>
    <div class="empty-title">${title}</div>
    <div class="empty-desc">${desc}</div>
    ${btnHtml}
  </div>`;
}

// ── Poster img ──
function posterImg(url, title, cls = '') {
  if (url) return `<img src="${url}" alt="${title}" class="${cls}" loading="lazy" onerror="this.style.display='none'">`;
  return `<div class="series-poster-placeholder">🎬</div>`;
}

// ── Color swatches ──
const PROJECT_COLORS = [
  '#00b020','#5a8aba','#8a5aba','#ba5a5a','#ba8a5a',
  '#5ababa','#aba85a','#ba5a8a','#7a7aaa','#40bc6a'
];

function colorSwatchesHtml(selected) {
  return `<div class="color-swatches">
    ${PROJECT_COLORS.map(c => `
      <div class="color-swatch ${c === selected ? 'selected' : ''}"
        style="background:${c}" data-color="${c}"
        onclick="document.querySelectorAll('.color-swatch').forEach(s=>s.classList.remove('selected'));this.classList.add('selected')">
      </div>
    `).join('')}
  </div>`;
}

function getSelectedColor() {
  const el = document.querySelector('.color-swatch.selected');
  return el ? el.dataset.color : PROJECT_COLORS[0];
}

// ── Date input group ──
function dateInputGroupHtml(prefix = '') {
  const now = new Date();
  return `<div class="date-group">
    <input class="form-input" id="${prefix}year"   type="number" placeholder="Ano"  min="1950" max="2099" value="${now.getFullYear()}"  oninput="updateDayMax('${prefix}')">
    <input class="form-input" id="${prefix}month"  type="number" placeholder="Mês"  min="1"    max="12"   value="${now.getMonth()+1}"    oninput="updateDayMax('${prefix}')">
    <input class="form-input" id="${prefix}day"    type="number" placeholder="Dia"  min="1"    max="31"   value="${now.getDate()}">
    <input class="form-input" id="${prefix}hour"   type="number" placeholder="Hora" min="0"    max="23">
    <input class="form-input" id="${prefix}minute" type="number" placeholder="Min"  min="0"    max="59">
  </div>
  <div class="form-hint">Preencha apenas o que souber. Mínimo: só o ano.</div>`;
}

function updateDayMax(prefix = '') {
  const yearEl  = document.getElementById(prefix + 'year');
  const monthEl = document.getElementById(prefix + 'month');
  const dayEl   = document.getElementById(prefix + 'day');
  if (!yearEl || !monthEl || !dayEl) return;
  const year  = parseInt(yearEl.value);
  const month = parseInt(monthEl.value);
  if (!year || !month) { dayEl.max = 31; return; }
  const maxDay = new Date(year, month, 0).getDate();
  dayEl.max = maxDay;
  if (parseInt(dayEl.value) > maxDay) dayEl.value = maxDay;
}

function getDateValues(prefix = '') {
  return {
    ano_assistido:    parseInt(document.getElementById(prefix + 'year')?.value)   || null,
    mes_assistido:    parseInt(document.getElementById(prefix + 'month')?.value)  || null,
    dia_assistido:    parseInt(document.getElementById(prefix + 'day')?.value)    || null,
    hora_assistido:   parseInt(document.getElementById(prefix + 'hour')?.value)   || null,
    minuto_assistido: parseInt(document.getElementById(prefix + 'minute')?.value) || null,
  };
}

// ── Format minutes ──
function formatMinutes(mins) {
  if (!mins) return '—';
  if (mins < 60) return `${mins}min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

// ── Image cache URLs ──
function cachedImg(url, category) {
  if (!url) return null;
  const match = url.match(/\/t\/p\/[^/]+\/(.+)$/);
  if (!match) return url;
  return `/images/${category}/${match[1]}`;
}

function posterUrl(url) { return cachedImg(url, 'posters'); }
function backdropUrl(url) { return cachedImg(url, 'backdrops'); }

// ── Local path → served URL (handles both "data/images/…" and "/images/…") ──
function _imagePathToUrl(path) {
  if (!path) return null;
  if (path.startsWith('http') || path.startsWith('/images/')) return path;
  const normalized = path.replace(/\\/g, '/');
  const match = normalized.match(/^(?:data\/)?images\/(.+)$/);
  if (match) return `/images/${match[1]}`;
  return '/' + normalized;
}

function posterPathUrl(path) { return _imagePathToUrl(path); }

function providerLogoUrl(p) {
  return _imagePathToUrl(p?.logo_path) || p?.logo_url || null;
}
