// Modal para registrar filme assistido a partir do diário

async function openWatchLogModal(ano, mes, dia) {
  let plataformas = [];
  try { plataformas = await api.getPlataformasCatalog(); } catch(e) {}

  const pad = n => String(n).padStart(2,'0');

  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Registrar filme — ${pad(dia)}/${pad(mes)}/${ano}</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Buscar filme</label>
        <div style="display:flex;gap:8px">
          <input class="form-input" id="wl-search" placeholder="Nome do filme..."
            oninput="searchFilmeWL()"
            onkeydown="if(event.key==='Enter')searchFilmeWL()">
        </div>
        <div id="wl-search-results" style="margin-top:8px"></div>
      </div>
      <div id="wl-selected-filme" style="display:none;margin-bottom:16px"></div>

      <div class="form-group">
        <label class="form-label">Hora (opcional)</label>
        <div style="display:flex;gap:8px">
          <input class="form-input" id="wl-hour"   type="number" placeholder="Hora" min="0" max="23" style="width:80px">
          <span style="color:var(--text3);padding:10px 4px">:</span>
          <input class="form-input" id="wl-minute" type="number" placeholder="Min"  min="0" max="59" style="width:80px">
        </div>
      </div>

      ${plataformas.length > 0 ? `
        <div class="form-group">
          <label class="form-label">Plataforma (opcional)</label>
          <select class="form-select" id="wl-plataforma">
            <option value="">Não informar</option>
            ${plataformas.map(p => `<option value="${p.id}">${p.nome}</option>`).join('')}
          </select>
        </div>
      ` : ''}

      <div class="form-group">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
          <input type="checkbox" id="wl-rewatch" style="accent-color:var(--accent)">
          <span style="font-size:13px">Rewatch (já vi antes)</span>
        </label>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-primary" id="wl-submit-btn" onclick="submitWatchLog(${ano}, ${mes}, ${dia})" data-label="Registrar" disabled>Registrar</button>
    </div>
  `);

  setTimeout(() => document.getElementById('wl-search')?.focus(), 50);
}

let _wlSelectedFilmeId = null;

async function searchFilmeWL() {
  const q = document.getElementById('wl-search')?.value?.trim().toLowerCase();
  const el = document.getElementById('wl-search-results');
  if (!q || q.length < 1) { el.innerHTML = ''; return; }

  const matches = allFilmes.filter(f =>
    f.titulo.toLowerCase().includes(q) ||
    (f.titulo_original || '').toLowerCase().includes(q) ||
    (f.titulo_pt || '').toLowerCase().includes(q)
  ).slice(0, 8);

  if (!matches.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--text3);padding:4px 0">Nenhum filme encontrado na lista.</div>';
    return;
  }

  el.innerHTML = `<div class="search-results">
    ${matches.map(f => `
      <div class="search-result-item" onclick="selectFilmeWL('${f.id}', '${f.titulo.replace(/'/g,"\\'")}')">
        ${f.poster_path
          ? `<img src="${posterPathUrl(f.poster_path)}" class="search-result-poster" onerror="this.style.display='none'">`
          : `<div class="search-result-poster" style="display:flex;align-items:center;justify-content:center;color:var(--text3)">🎬</div>`
        }
        <div class="search-result-info">
          <div class="search-result-title">${f.titulo}</div>
          <div class="search-result-meta">${f.ano || ''}</div>
        </div>
      </div>
    `).join('')}
  </div>`;
}

function selectFilmeWL(filmeId, titulo) {
  _wlSelectedFilmeId = filmeId;
  document.getElementById('wl-search-results').innerHTML = '';
  document.getElementById('wl-search').value = titulo;

  const el = document.getElementById('wl-selected-filme');
  el.style.display = 'block';
  el.innerHTML = `<div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm)">
    <span style="font-size:13px;color:var(--text2)">✓ ${titulo}</span>
    <button class="btn btn-sm btn-ghost" style="margin-left:auto" onclick="clearFilmeWL()">Trocar</button>
  </div>`;

  const btn = document.getElementById('wl-submit-btn');
  if (btn) btn.disabled = false;
}

function clearFilmeWL() {
  _wlSelectedFilmeId = null;
  const el = document.getElementById('wl-selected-filme');
  el.style.display = 'none';
  el.innerHTML = '';
  document.getElementById('wl-search').value = '';
  const btn = document.getElementById('wl-submit-btn');
  if (btn) btn.disabled = true;
}

async function submitWatchLog(ano, mes, dia) {
  if (!_wlSelectedFilmeId) { toast('Selecione um filme.', 'error'); return; }

  const hora   = parseInt(document.getElementById('wl-hour')?.value)   || null;
  const minuto = parseInt(document.getElementById('wl-minute')?.value) || null;
  const platEl = document.getElementById('wl-plataforma');
  const rewatch = document.getElementById('wl-rewatch')?.checked || false;

  const btn = document.getElementById('wl-submit-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Aguarde...'; }

  try {
    await api.marcarAssistido(_wlSelectedFilmeId, {
      filme_id:         _wlSelectedFilmeId,
      ano_assistido:    ano,
      mes_assistido:    mes,
      dia_assistido:    dia,
      hora_assistido:   hora,
      minuto_assistido: minuto,
      plataforma_id:    platEl ? (parseInt(platEl.value) || null) : null,
      rewatch,
    });
    toast('Filme registrado no diário!');
    modal.hide();
    allFilmes = await api.getFilmes();
    renderDiario();
  } catch(e) {
    toast('Erro: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Registrar'; }
  }
}
