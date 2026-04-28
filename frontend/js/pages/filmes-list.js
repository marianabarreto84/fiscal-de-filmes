// ── Lista de filmes: três abas — Assistidos, Quero Assistir e Sem Categoria ───

let activeFilmesTab = 'assistidos';

function switchFilmesTab(tab) {
  activeFilmesTab = tab;
  renderFilmesGrid();
}

function classifyFilmes(filmes) {
  const watchlist     = filmes.filter(f => f.na_watchlist && !f.assistido);
  const assistidos    = filmes.filter(f => f.assistido);
  const sem_categoria = filmes.filter(f => !f.na_watchlist && !f.assistido);

  const alpha = (a, b) => a.titulo.localeCompare(b.titulo);
  watchlist.sort(alpha);
  sem_categoria.sort(alpha);
  const watchedTime = f => {
    const s = f.ultimo_assistido || f.ultimo_logado;
    return s ? new Date(s).getTime() : 0;
  };
  assistidos.sort((a, b) => watchedTime(b) - watchedTime(a) || a.titulo.localeCompare(b.titulo));
  return { watchlist, sem_categoria, assistidos };
}

function filmeSectionHtml(id, title, filmes, alwaysShow = false) {
  if (!filmes.length && !alwaysShow) return '';
  return `
    <div class="series-section" id="${id}">
      <div class="series-section-title">
        ${title}
        <span class="series-section-count">${filmes.length}</span>
      </div>
      <div class="series-grid">
        ${filmes.map(filmeCardHtml).join('')}
        ${!filmes.length ? '<div class="text-muted" style="font-size:13px;padding:8px">Nenhum filme aqui ainda.</div>' : ''}
      </div>
    </div>
  `;
}

function filmeCardHtml(f) {
  const imgSrc = f.poster_path ? posterPathUrl(f.poster_path) : null;
  const ano = f.ano ? ` · ${f.ano}` : '';
  const dur = f.duracao_min ? ` · ${formatMinutes(f.duracao_min)}` : '';

  return `
    <div class="series-card" data-filme-id="${f.id}" onclick="openFilmeModal('${f.id}')">
      <div class="series-poster">
        ${imgSrc
          ? `<img src="${imgSrc}" alt="${f.titulo}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=series-poster-placeholder>🎬</div>'">`
          : `<div class="series-poster-placeholder">🎬</div>`
        }
      </div>
      <div class="series-info">
        <div class="series-title">${f.titulo}</div>
        <div class="series-meta">${f.ano || ''}${dur}</div>
      </div>
    </div>
  `;
}

async function renderFilmes() {
  const el = document.getElementById('page-filmes');
  el.innerHTML = loadingHtml();

  try {
    allFilmes = await api.getFilmes();
    const total = allFilmes.length;

    el.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-title">Filmes</div>
          <div class="page-subtitle">${total} filme${total !== 1 ? 's' : ''} cadastrado${total !== 1 ? 's' : ''}</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <input id="filmes-search" class="form-input" placeholder="Buscar filme..." oninput="renderFilmesGrid()" style="width:220px">
          <button class="btn btn-primary" onclick="openAddFilmeModal()">
            <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            Adicionar filme
          </button>
        </div>
      </div>
      <div class="page-body">
        ${total === 0
          ? emptyState('🎬', 'Nenhum filme ainda', 'Adicione seu primeiro filme buscando pelo nome.', `<button class="btn btn-primary" onclick="openAddFilmeModal()">Adicionar filme</button>`)
          : `<div id="filmes-sections"></div>`
        }
      </div>
    `;

    if (total > 0) renderFilmesGrid();
  } catch(e) {
    el.innerHTML = `<div class="page-body text-muted">Erro: ${e.message}</div>`;
  }
}

let _tmdbIdSearchTimeout = null;

function renderFilmesGrid() {
  const container = document.getElementById('filmes-sections');
  if (!container) return;

  const raw = document.getElementById('filmes-search')?.value?.trim() || '';

  const tmdbMatch = raw.match(/^TMDB:(\d+)$/i);
  if (tmdbMatch) {
    container.innerHTML = loadingHtml();
    clearTimeout(_tmdbIdSearchTimeout);
    _tmdbIdSearchTimeout = setTimeout(() => showTmdbImportPrompt(tmdbMatch[1], container), 400);
    return;
  }

  const q = raw.toLowerCase();
  const list = q
    ? allFilmes.filter(f =>
        f.titulo.toLowerCase().includes(q) ||
        (f.titulo_original || '').toLowerCase().includes(q) ||
        (f.titulo_pt || '').toLowerCase().includes(q)
      )
    : allFilmes;

  const { watchlist, sem_categoria, assistidos } = classifyFilmes(list);

  const counts = {
    assistidos:    assistidos.length,
    watchlist:     watchlist.length,
    sem_categoria: sem_categoria.length,
  };

  const tabsHtml = q ? '' : `
    <div class="tabs">
      <button class="tab-btn ${activeFilmesTab === 'assistidos' ? 'active' : ''}" onclick="switchFilmesTab('assistidos')">
        Assistidos <span class="series-section-count">${counts.assistidos}</span>
      </button>
      <button class="tab-btn ${activeFilmesTab === 'watchlist' ? 'active' : ''}" onclick="switchFilmesTab('watchlist')">
        Quero Assistir <span class="series-section-count">${counts.watchlist}</span>
      </button>
      <button class="tab-btn ${activeFilmesTab === 'sem_categoria' ? 'active' : ''}" onclick="switchFilmesTab('sem_categoria')">
        Sem Categoria <span class="series-section-count">${counts.sem_categoria}</span>
      </button>
    </div>
  `;

  let sectionsHtml;
  if (q) {
    sectionsHtml = `
      ${filmeSectionHtml('section-sem-categoria', 'Sem categoria',  sem_categoria, false)}
      ${filmeSectionHtml('section-assistidos',    'Assistidos',     assistidos,    false)}
      ${filmeSectionHtml('section-watchlist',     'Quero Assistir', watchlist,     false)}
    `;
  } else if (activeFilmesTab === 'assistidos') {
    sectionsHtml = filmeSectionHtml('section-assistidos', 'Assistidos', assistidos, true);
  } else if (activeFilmesTab === 'watchlist') {
    sectionsHtml = filmeSectionHtml('section-watchlist', 'Quero Assistir', watchlist, true);
  } else {
    sectionsHtml = filmeSectionHtml('section-sem-categoria', 'Sem categoria', sem_categoria, true);
  }

  container.innerHTML = tabsHtml + sectionsHtml;
}

async function showTmdbImportPrompt(tmdbId, container) {
  try {
    const m = await api.getTmdbMovie(tmdbId);
    const exists = allFilmes.find(f => String(f.tmdb_id) === String(tmdbId));

    container.innerHTML = `
      <div class="card" style="padding:16px;max-width:500px">
        <div style="display:flex;gap:14px;align-items:flex-start">
          ${m.poster_url ? `<img src="${m.poster_url}" style="width:60px;border-radius:6px;flex-shrink:0">` : ''}
          <div style="flex:1">
            <div style="font-family:var(--font-display);font-size:18px;margin-bottom:4px">${m.titulo}</div>
            <div style="font-size:12px;color:var(--text3)">${m.ano || ''} · ${formatMinutes(m.duracao_min)} · ★ ${m.nota_tmdb?.toFixed(1) || '—'}</div>
            <div style="font-size:12px;color:var(--text3);margin-top:4px">${(m.generos || []).join(', ')}</div>
          </div>
        </div>
        <div style="font-size:13px;color:var(--text3);margin-top:10px;line-height:1.5">${m.sinopse?.slice(0, 200) || ''}${(m.sinopse?.length || 0) > 200 ? '…' : ''}</div>
        <div style="margin-top:14px">
          ${exists
            ? `<span style="font-size:13px;color:var(--text3)">✓ Já está no banco como "${exists.titulo}"</span>`
            : `<button class="btn btn-primary" id="btn-import-tmdb" onclick="importFromTmdbId('${tmdbId}')">Adicionar ao banco</button>`
          }
        </div>
      </div>
    `;
    window._pendingTmdbImport = m;
  } catch(e) {
    container.innerHTML = `<div class="text-muted" style="font-size:13px;padding:12px 0">TMDB ID não encontrado: ${e.message}</div>`;
  }
}

async function importFromTmdbId(tmdbId) {
  const m = window._pendingTmdbImport;
  const btn = document.getElementById('btn-import-tmdb');
  if (btn) { btn.disabled = true; btn.textContent = 'Adicionando…'; }

  try {
    const created = await api.createFilme({
      tmdb_id:         m.tmdb_id,
      titulo:          m.titulo,
      titulo_original: m.titulo_original,
      duracao_min:     m.duracao_min,
      sinopse:         m.sinopse,
      ano:             m.ano,
      nota_tmdb:       m.nota_tmdb,
      poster_url:      m.poster_url,
    });

    api.syncFilmePlataformas(created.id).catch(() => {});

    toast(`"${m.titulo}" adicionado!`);
    document.getElementById('filmes-search').value = '';
    await renderFilmes();
  } catch(e) {
    toast('Erro ao adicionar: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Adicionar ao banco'; }
  }
}

// ── Add filme modal ───────────────────────────────────────────────────────────
function openAddFilmeModal() {
  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Adicionar filme</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Buscar no TMDB</label>
        <div style="display:flex;gap:8px">
          <input class="form-input" id="tmdb-search" placeholder="Nome do filme..." onkeydown="if(event.key==='Enter')searchTmdbFilme()">
          <button class="btn btn-secondary" onclick="searchTmdbFilme()">Buscar</button>
        </div>
      </div>
      <div id="tmdb-results"></div>
    </div>
  `);
  setTimeout(() => document.getElementById('tmdb-search')?.focus(), 50);
}

async function searchTmdbFilme() {
  const q = document.getElementById('tmdb-search')?.value?.trim();
  if (!q) return;
  const el = document.getElementById('tmdb-results');
  el.innerHTML = loadingHtml();
  try {
    const results = await api.searchTmdb(q);
    if (!results.length) {
      el.innerHTML = '<div class="text-muted" style="font-size:13px;padding:12px 0">Nenhum resultado encontrado.</div>';
      return;
    }
    el.innerHTML = `<div class="search-results">
      ${results.map(r => `
        <div class="search-result-item" onclick="selectTmdbFilme('${r.tmdb_id}')">
          ${r.poster_url
            ? `<img src="${posterUrl(r.poster_url)}" class="search-result-poster" onerror="this.style.display='none'">`
            : `<div class="search-result-poster" style="display:flex;align-items:center;justify-content:center;color:var(--text3)">🎬</div>`
          }
          <div class="search-result-info">
            <div class="search-result-title">${r.titulo}</div>
            <div class="search-result-meta">${r.titulo_original !== r.titulo ? r.titulo_original + ' · ' : ''}${r.ano || ''}</div>
          </div>
        </div>
      `).join('')}
    </div>`;
  } catch(e) {
    el.innerHTML = `<div class="text-muted" style="font-size:13px">Erro: ${e.message}</div>`;
  }
}

async function selectTmdbFilme(tmdbId) {
  const el = document.getElementById('tmdb-results');
  el.innerHTML = loadingHtml();
  try {
    const m = await api.getTmdbMovie(tmdbId);
    el.innerHTML = `
      <div class="card" style="padding:16px;margin-top:8px">
        <div style="display:flex;gap:14px;align-items:flex-start">
          ${m.poster_url ? `<img src="${m.poster_url}" style="width:60px;border-radius:6px">` : ''}
          <div style="flex:1">
            <div style="font-family:var(--font-display);font-size:18px;margin-bottom:4px">${m.titulo}</div>
            <div style="font-size:12px;color:var(--text3)">${m.ano || ''} · ${formatMinutes(m.duracao_min)} · ★ ${m.nota_tmdb?.toFixed(1) || '—'}</div>
            <div style="font-size:12px;color:var(--text3);margin-top:4px">${(m.generos || []).join(', ')}</div>
          </div>
        </div>
        <div style="font-size:12px;color:var(--text3);margin-top:10px;line-height:1.5">${m.sinopse?.slice(0,200) || ''}${m.sinopse?.length > 200 ? '...' : ''}</div>
      </div>
    `;
    document.querySelector('.modal-footer')?.remove();
    const footer = document.createElement('div');
    footer.className = 'modal-footer';
    footer.innerHTML = `
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-primary" onclick="importFilme('${tmdbId}')">Adicionar filme</button>
    `;
    document.getElementById('modal').appendChild(footer);
    window._pendingTmdbFilme = m;
  } catch(e) {
    el.innerHTML = `<div class="text-muted" style="font-size:13px">Erro: ${e.message}</div>`;
  }
}

async function importFilme(tmdbId) {
  const m = window._pendingTmdbFilme;
  const btn = document.querySelector('.modal-footer .btn-primary');
  if (btn) { btn.disabled = true; btn.textContent = 'Adicionando...'; }

  try {
    const created = await api.createFilme({
      tmdb_id:         m.tmdb_id,
      titulo:          m.titulo,
      titulo_original: m.titulo_original,
      duracao_min:     m.duracao_min,
      sinopse:         m.sinopse,
      ano:             m.ano,
      nota_tmdb:       m.nota_tmdb,
      poster_url:      m.poster_url,
    });

    api.syncFilmePlataformas(created.id).catch(() => {});

    toast(`"${m.titulo}" adicionado!`);
    modal.hide();
    renderFilmes();
  } catch(e) {
    toast('Erro ao adicionar: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Adicionar filme'; }
  }
}

function confirmDeleteFilme(id, titulo) {
  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Remover filme</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <p>Tem certeza que deseja remover <strong>"${titulo}"</strong>? Todas as entradas de diário serão apagadas.</p>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-danger" onclick="deleteFilme('${id}')">Remover</button>
    </div>
  `);
}

async function deleteFilme(id) {
  try {
    await api.deleteFilme(id);
    toast('Filme removido.');
    modal.hide();
    renderFilmes();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}
