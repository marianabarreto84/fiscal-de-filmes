async function renderProjetos() {
  const el = document.getElementById('page-projetos');
  el.innerHTML = loadingHtml();
  try {
    const projetos = await api.getProjetos();
    el.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-title">Projetos</div>
          <div class="page-subtitle">${projetos.length} projeto${projetos.length !== 1 ? 's' : ''}</div>
        </div>
        <button class="btn btn-primary" onclick="openCreateProjetoModal()">
          <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
          Novo projeto
        </button>
      </div>
      <div class="page-body">
        ${projetos.length === 0
          ? emptyState('🎬', 'Nenhum projeto ainda', 'Crie um projeto para organizar listas de filmes.', `<button class="btn btn-primary" onclick="openCreateProjetoModal()">Criar projeto</button>`)
          : `<div class="projects-grid">${projetos.map(projetoCardHtml).join('')}</div>`
        }
      </div>
    `;
  } catch(e) {
    el.innerHTML = `<div class="page-body text-muted">Erro: ${e.message}</div>`;
  }
}

function projetoCardHtml(p) {
  const total    = p.total_filmes || 0;
  const watched  = p.filmes_assistidos || 0;
  const progress = pct(watched, total);
  return `
    <div class="project-card" style="--project-color:${p.cor}" onclick="openProjetoDetail('${p.id}')">
      <div class="project-name">${p.titulo}</div>
      ${p.descricao ? `<div class="project-desc">${p.descricao}</div>` : ''}
      <div class="project-type-badge">🎬 Filmes · ${total} filme${total !== 1 ? 's' : ''}</div>
      <div class="project-progress-wrap">
        <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
        <div class="progress-label">
          <span>${watched} / ${total} assistidos</span>
          <span>${progress}%</span>
        </div>
      </div>
    </div>
  `;
}

function openCreateProjetoModal() {
  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Novo projeto</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Nome do projeto</label>
        <input class="form-input" id="proj-titulo" placeholder="Ex: Filmes para assistir com a família">
      </div>
      <div class="form-group">
        <label class="form-label">Descrição (opcional)</label>
        <textarea class="form-textarea" id="proj-desc" placeholder="Sobre este projeto..."></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Cor</label>
        ${colorSwatchesHtml(PROJECT_COLORS[0])}
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-primary" onclick="createProjeto()" data-label="Criar">Criar projeto</button>
    </div>
  `);
  setTimeout(() => document.getElementById('proj-titulo')?.focus(), 50);
}

async function createProjeto() {
  const titulo = document.getElementById('proj-titulo')?.value?.trim();
  if (!titulo) { toast('Informe o nome do projeto.', 'error'); return; }
  const desc  = document.getElementById('proj-desc')?.value?.trim() || null;
  const cor   = getSelectedColor();
  try {
    await api.createProjeto({ titulo, descricao: desc, cor });
    toast('Projeto criado!');
    modal.hide();
    renderProjetos();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function openProjetoDetail(projetoId) {
  history.replaceState(null, '', `#projetos/${projetoId}`);
  const el = document.getElementById('page-projetos');
  el.innerHTML = loadingHtml();

  try {
    const p = await api.getProjeto(projetoId);
    const total    = p.total_filmes || 0;
    const watched  = p.filmes_assistidos || 0;
    const progress = pct(watched, total);

    el.innerHTML = `
      <div class="project-detail-header" style="--project-color:${p.cor}">
        <button class="btn btn-ghost" style="margin-bottom:12px" onclick="navigate('projetos')">
          <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
          Projetos
        </button>
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px">
          <div>
            <div class="page-title">${p.titulo}</div>
            ${p.descricao ? `<div style="font-size:13px;color:var(--text3);margin-top:6px">${p.descricao}</div>` : ''}
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary btn-sm" onclick="openEditProjetoModal('${p.id}', '${p.titulo.replace(/'/g,"\\'")}', ${JSON.stringify(p.descricao || '')}, '${p.cor}')">Editar</button>
            <button class="btn btn-danger btn-sm" onclick="confirmDeleteProjeto('${p.id}', '${p.titulo.replace(/'/g,"\\'")}')">Excluir</button>
          </div>
        </div>
        <div class="project-big-progress">
          <div class="big-progress-bar">
            <div class="big-progress-fill" style="width:${progress}%"></div>
          </div>
          <div style="font-size:12px;color:var(--text3)">${watched} / ${total} assistidos · ${progress}%</div>
        </div>
      </div>

      <div class="page-body">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
          <div class="section-title" style="margin-bottom:0">Filmes</div>
          <button class="btn btn-secondary btn-sm" onclick="openAddFilmesToProjetoModal('${p.id}')">
            <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            Adicionar filmes
          </button>
        </div>

        ${p.items.length === 0
          ? '<div class="text-muted" style="font-size:13px">Nenhum filme neste projeto ainda.</div>'
          : `<div class="series-grid">
              ${p.items.map(f => projetoFilmeCardHtml(p.id, f)).join('')}
            </div>`
        }
      </div>
    `;
  } catch(e) {
    el.innerHTML = `<div class="page-body text-muted">Erro: ${e.message}</div>`;
  }
}

function projetoFilmeCardHtml(projetoId, f) {
  const imgSrc = f.poster_path ? posterPathUrl(f.poster_path) : null;
  return `
    <div class="series-card">
      <div class="series-poster" onclick="openFilmeDetail('${f.id}')" style="cursor:pointer">
        ${imgSrc
          ? `<img src="${imgSrc}" alt="${f.titulo}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=series-poster-placeholder>🎬</div>'">`
          : `<div class="series-poster-placeholder">🎬</div>`
        }
        ${f.assistido ? `<div class="series-progress-bar"><div class="series-progress-fill" style="width:100%"></div></div>` : ''}
      </div>
      <div class="series-info">
        <div class="series-title">${f.titulo}</div>
        <div class="series-meta" style="display:flex;align-items:center;justify-content:space-between">
          ${f.ano || ''}
          <button class="btn-icon" style="padding:2px;opacity:0.4" title="Remover do projeto"
            onclick="event.stopPropagation();removeFilmeFromProjeto('${projetoId}', '${f.id}', this)">
            <svg viewBox="0 0 24 24" style="width:12px;height:12px;fill:currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
          </button>
        </div>
      </div>
    </div>
  `;
}

async function removeFilmeFromProjeto(projetoId, filmeId, btn) {
  btn.disabled = true;
  try {
    await api.removeFilmeFromProjeto(projetoId, filmeId);
    toast('Filme removido do projeto.');
    openProjetoDetail(projetoId);
  } catch(e) {
    toast('Erro: ' + e.message, 'error');
    btn.disabled = false;
  }
}

async function openAddFilmesToProjetoModal(projetoId) {
  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Adicionar filmes</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <input class="form-input" id="proj-filme-search" placeholder="Buscar filme..." oninput="searchFilmesProjeto()">
      </div>
      <div id="proj-filmes-list" style="max-height:300px;overflow-y:auto"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Fechar</button>
      <button class="btn btn-primary" onclick="addSelectedFilmesProjeto('${projetoId}')" data-label="Adicionar">Adicionar selecionados</button>
    </div>
  `);
  setTimeout(() => {
    renderFilmesListProjeto(allFilmes);
    document.getElementById('proj-filme-search')?.focus();
  }, 50);
}

function searchFilmesProjeto() {
  const q = document.getElementById('proj-filme-search')?.value?.trim().toLowerCase() || '';
  const list = q
    ? allFilmes.filter(f => f.titulo.toLowerCase().includes(q) || (f.titulo_original || '').toLowerCase().includes(q))
    : allFilmes;
  renderFilmesListProjeto(list);
}

function renderFilmesListProjeto(filmes) {
  const el = document.getElementById('proj-filmes-list');
  if (!el) return;
  el.innerHTML = filmes.slice(0, 50).map(f => `
    <label style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--border);cursor:pointer">
      <input type="checkbox" data-filme-id="${f.id}" style="accent-color:var(--accent)">
      <span style="font-size:13px;color:var(--text2)">${f.titulo}${f.ano ? ` (${f.ano})` : ''}</span>
    </label>
  `).join('');
}

async function addSelectedFilmesProjeto(projetoId) {
  const checked = [...document.querySelectorAll('#proj-filmes-list input[type=checkbox]:checked')];
  if (!checked.length) { toast('Selecione ao menos um filme.', 'error'); return; }
  const ids = checked.map(c => c.dataset.filmeId);
  try {
    await api.addFilmesToProjeto(projetoId, ids);
    toast(`${ids.length} filme${ids.length > 1 ? 's' : ''} adicionado${ids.length > 1 ? 's' : ''}!`);
    modal.hide();
    openProjetoDetail(projetoId);
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

function openEditProjetoModal(id, titulo, descricao, cor) {
  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Editar projeto</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Nome</label>
        <input class="form-input" id="edit-proj-titulo" value="${titulo}">
      </div>
      <div class="form-group">
        <label class="form-label">Descrição</label>
        <textarea class="form-textarea" id="edit-proj-desc">${descricao || ''}</textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Cor</label>
        ${colorSwatchesHtml(cor)}
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-primary" onclick="updateProjeto('${id}')" data-label="Salvar">Salvar</button>
    </div>
  `);
}

async function updateProjeto(id) {
  const titulo = document.getElementById('edit-proj-titulo')?.value?.trim();
  if (!titulo) { toast('Informe o nome.', 'error'); return; }
  const descricao = document.getElementById('edit-proj-desc')?.value?.trim() || null;
  const cor = getSelectedColor();
  try {
    await api.updateProjeto(id, { titulo, descricao, cor });
    toast('Projeto atualizado!');
    modal.hide();
    openProjetoDetail(id);
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

function confirmDeleteProjeto(id, titulo) {
  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Excluir projeto</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <p>Tem certeza que deseja excluir o projeto <strong>"${titulo}"</strong>?</p>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-danger" onclick="deleteProjeto('${id}')">Excluir</button>
    </div>
  `);
}

async function deleteProjeto(id) {
  try {
    await api.deleteProjeto(id);
    toast('Projeto excluído.');
    modal.hide();
    renderProjetos();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}
