let configTab = 'plataformas';

function renderConfiguracoes() {
  const el = document.getElementById('page-configuracoes');
  el.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Configurações</div>
      </div>
    </div>
    <div class="settings-layout">
      <div class="settings-sidebar">
        <button class="settings-nav-btn ${configTab === 'plataformas' ? 'active' : ''}" onclick="switchConfigTab('plataformas')">Plataformas</button>
        <button class="settings-nav-btn ${configTab === 'padrao' ? 'active' : ''}" onclick="switchConfigTab('padrao')">Padrão por filme</button>
        <button class="settings-nav-btn ${configTab === 'armazenamento' ? 'active' : ''}" onclick="switchConfigTab('armazenamento')">Armazenamento</button>
      </div>
      <div class="settings-content" id="config-content">
        ${loadingHtml()}
      </div>
    </div>
  `;
  loadConfigTab(configTab);
}

function switchConfigTab(tab) {
  configTab = tab;
  document.querySelectorAll('.settings-nav-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.trim().toLowerCase().startsWith(tab === 'padrao' ? 'padrão' : tab));
  });
  loadConfigTab(tab);
}

async function loadConfigTab(tab) {
  const el = document.getElementById('config-content');
  el.innerHTML = loadingHtml();

  try {
    if (tab === 'plataformas') {
      await renderPlataformasConfig(el);
    } else if (tab === 'padrao') {
      await renderPadraoConfig(el);
    } else if (tab === 'armazenamento') {
      await renderArmazenamentoConfig(el);
    }
  } catch(e) {
    el.innerHTML = `<div class="text-muted">Erro: ${e.message}</div>`;
  }
}

// ── Plataformas config ────────────────────────────────────────────────────────

async function renderPlataformasConfig(el) {
  const plats = await api.getPlataformasConfig();

  el.innerHTML = `
    <div class="settings-section">
      <div class="settings-section-title">Plataformas</div>
      <div class="settings-section-desc">Configure a visibilidade e ordem das plataformas. Arraste para reordenar.</div>
      <div style="margin-bottom:16px;display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" onclick="syncAllPlataformas()">
          Sincronizar todas com TMDB
        </button>
      </div>
      <div id="plat-config-list">
        ${plats.map(p => `
          <div class="provider-config-row" data-plat-id="${p.id}" id="pcr-${p.id}">
            <div class="provider-config-handle">
              <svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:currentColor;opacity:0.5"><path d="M11 18c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm-2-8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm6 4c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
            </div>
            ${providerLogoUrl(p)
              ? `<img src="${providerLogoUrl(p)}" style="width:28px;height:28px;border-radius:6px;object-fit:cover" onerror="this.style.display='none'">`
              : `<div style="width:28px;height:28px;border-radius:6px;background:var(--bg4);display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--text3)">${p.nome.slice(0,2)}</div>`
            }
            <span style="flex:1;font-size:13px;color:var(--text2)">${p.nome}</span>
            <button class="provider-toggle ${p.visivel ? 'on' : 'off'}" id="ptoggle-${p.id}"
              onclick="togglePlataformaVisivel('${p.id}')">
              ${p.visivel ? 'visível' : 'oculta'}
            </button>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  if (window.Sortable) {
    Sortable.create(document.getElementById('plat-config-list'), {
      handle: '.provider-config-handle',
      animation: 150,
      ghostClass: 'provider-config-ghost',
      onEnd: async () => {
        const ids = [...document.querySelectorAll('#plat-config-list [data-plat-id]')]
          .map(el => el.dataset.platId);
        try {
          await api.reorderPlataformas(ids);
        } catch(e) { toast('Erro ao salvar ordem: ' + e.message, 'error'); }
      }
    });
  }
}

async function togglePlataformaVisivel(id) {
  const btn = document.getElementById(`ptoggle-${id}`);
  if (!btn) return;
  const isNowVisible = btn.classList.contains('on');
  const newVisible = !isNowVisible;
  btn.classList.toggle('on',  newVisible);
  btn.classList.toggle('off', !newVisible);
  btn.textContent = newVisible ? 'visível' : 'oculta';
  try {
    await api.patchPlataformaConfig(id, { visivel: newVisible });
  } catch(e) {
    // Reverte em caso de erro
    btn.classList.toggle('on',  isNowVisible);
    btn.classList.toggle('off', !isNowVisible);
    btn.textContent = isNowVisible ? 'visível' : 'oculta';
    toast('Erro: ' + e.message, 'error');
  }
}

async function syncAllPlataformas() {
  toast('Sincronizando plataformas com o TMDB...');
  try {
    const result = await api.syncAllPlataformas();
    toast(`Sincronizado! ${result.ok} filmes atualizados.`);
    loadConfigTab('plataformas');
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

// ── Padrão por filme ──────────────────────────────────────────────────────────

async function renderPadraoConfig(el) {
  const defaults = await api.getPlataformaDefaults();

  el.innerHTML = `
    <div class="settings-section">
      <div class="settings-section-title">Plataforma padrão por filme</div>
      <div class="settings-section-desc">Defina qual plataforma aparece pré-selecionada ao marcar cada filme como assistido.</div>
      <div>
        ${defaults.map(d => `
          <div class="provider-default-row">
            <span style="flex:1;font-size:13px">${d.filme_titulo}</span>
            <select style="background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:var(--radius-sm);padding:4px 8px;font-size:12px"
              onchange="setFilmePadraoPlataforma(${d.filme_id}, this.value)">
              <option value="">Nenhuma</option>
              ${d.plataformas.map(p => `
                <option value="${p.id}" ${d.default_plataforma_id === p.id ? 'selected' : ''}>${p.nome}</option>
              `).join('')}
            </select>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

async function setFilmePadraoPlataforma(filmeId, platId) {
  try {
    await api.setFilmePlataformaPadrao(filmeId, platId ? parseInt(platId) : null);
    toast('Padrão atualizado.');
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

// ── Armazenamento ─────────────────────────────────────────────────────────────

function _fmt(bytes) {
  if (!bytes) return '0 B';
  const units = ['B','KB','MB','GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

async function renderArmazenamentoConfig(el) {
  let storage = await api.getStorage();

  const renderContent = (s) => {
    if (!s) return `<div class="text-muted">Nenhum dado calculado ainda. Clique em "Calcular" para analisar o disco.</div>`;
    return `
      <div class="settings-row">
        <div><div class="settings-row-label">Total</div></div>
        <div class="settings-row-value">${_fmt(s.total_bytes)}</div>
      </div>
      <div class="settings-row">
        <div><div class="settings-row-label">Posters</div></div>
        <div class="settings-row-value">${_fmt(s.posters_bytes)}</div>
      </div>
      <div class="settings-row">
        <div><div class="settings-row-label">Logos de plataformas</div></div>
        <div class="settings-row-value">${_fmt(s.providers_bytes)}</div>
      </div>
      <div style="font-size:11px;color:var(--text3);margin-top:8px">Calculado em ${new Date(s.calculated_at).toLocaleString('pt-BR')}</div>
    `;
  };

  el.innerHTML = `
    <div class="settings-section">
      <div class="settings-section-title">Armazenamento</div>
      <div class="settings-section-desc">Uso de disco pelos arquivos de imagem.</div>
      <div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap">
        <button class="btn btn-secondary btn-sm" onclick="calculateStorage()">Calcular uso de disco</button>
        <button class="btn btn-secondary btn-sm" id="btn-sync-posters" onclick="syncMissingPosters()">Baixar posters ausentes</button>
      </div>
      <div id="storage-data">${renderContent(storage)}</div>
    </div>
  `;
}

async function syncMissingPosters() {
  const btn = document.getElementById('btn-sync-posters');
  if (btn) { btn.disabled = true; btn.textContent = 'Baixando…'; }
  try {
    const r = await api.syncMissingPosters();
    toast(`Posters: ${r.ok} baixados, ${r.skipped} já existiam${r.errors ? `, ${r.errors} erros` : ''}.`);
  } catch(e) {
    toast('Erro: ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Baixar posters ausentes'; }
  }
}

async function calculateStorage() {
  const el = document.getElementById('storage-data');
  if (el) el.innerHTML = loadingHtml();
  try {
    const s = await api.calculateStorage();
    if (el) el.innerHTML = `
      <div class="settings-row"><div><div class="settings-row-label">Total</div></div><div class="settings-row-value">${_fmt(s.total_bytes)}</div></div>
      <div class="settings-row"><div><div class="settings-row-label">Posters</div></div><div class="settings-row-value">${_fmt(s.posters_bytes)}</div></div>
      <div class="settings-row"><div><div class="settings-row-label">Logos de plataformas</div></div><div class="settings-row-value">${_fmt(s.providers_bytes)}</div></div>
      <div style="font-size:11px;color:var(--text3);margin-top:8px">Calculado em ${new Date(s.calculated_at).toLocaleString('pt-BR')}</div>
    `;
    toast('Armazenamento calculado.');
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}
