async function openFilmeDetail(filmeId) {
  history.replaceState(null, '', `#filmes/${filmeId}`);
  const el = document.getElementById('page-filmes');
  el.innerHTML = `
    <div class="page-header">
      <button class="btn btn-ghost" onclick="navigate('filmes')">
        <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
        Voltar
      </button>
    </div>
    ${loadingHtml()}
  `;

  try {
    const f = await api.getFilmeById(filmeId);
    const imgSrc = f.poster_path ? posterPathUrl(f.poster_path) : null;

    el.innerHTML = `
      <div style="position:relative;overflow:hidden;border-bottom:1px solid var(--border)">
        <div class="page-header" style="position:relative">
          <div>
            <button class="btn btn-ghost" style="margin-bottom:12px" onclick="navigate('filmes')">
              <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
              Filmes
            </button>
            <div class="page-title">${f.titulo}</div>
            <div class="page-subtitle">${f.titulo_original || ''} · ${f.ano || ''} · ${formatMinutes(f.duracao_min)}</div>
            <div style="margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
              ${f.assistido
                ? `<button class="btn btn-secondary btn-sm" onclick="desmarcarAssistidoInline('${f.id}')">
                    <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    Desmarcar assistido
                  </button>`
                : `<button class="btn btn-primary btn-sm" onclick="openFilmeWatchModal('${f.id}')">
                    <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                    Marcar assistido
                  </button>`
              }
              ${f.na_watchlist
                ? `<button class="btn btn-secondary btn-sm" onclick="removeWatchlistInline('${f.id}')">
                    Remover da lista
                  </button>`
                : (!f.assistido
                    ? `<button class="btn btn-ghost btn-sm" onclick="addWatchlistInline('${f.id}')">
                        + Quero assistir
                      </button>`
                    : '')
              }
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:flex-start;flex-direction:column">
            ${imgSrc ? `<img src="${imgSrc}" style="width:80px;border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,0.5)" onerror="this.style.display='none'">` : ''}
            <button class="btn btn-danger btn-sm" onclick="confirmDeleteFilme('${f.id}', '${f.titulo.replace(/'/g,"\\'")}')">Remover</button>
          </div>
        </div>
      </div>

      <div class="page-body">
        ${f.sinopse ? `<div style="font-size:13px;color:var(--text2);line-height:1.7;margin-bottom:28px;max-width:700px">${f.sinopse}</div>` : ''}

        <div id="filme-plataformas-section-${filmeId}" style="margin-bottom:28px">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <div class="section-title" style="margin-bottom:0">Plataformas</div>
            <button class="btn btn-ghost btn-sm" id="sync-plat-btn-${filmeId}" onclick="syncFilmePlataformasInline('${filmeId}')">
              <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
              Sincronizar
            </button>
            <button class="btn btn-ghost btn-sm" onclick="showAddPlataformaInline('${filmeId}')">
              <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
              Adicionar
            </button>
          </div>
          <div id="filme-plataformas-chips-${filmeId}" style="display:flex;flex-wrap:wrap;gap:8px">
            <span style="font-size:12px;color:var(--text3)">Carregando…</span>
          </div>
        </div>

        ${f.diario && f.diario.length > 0 ? `
          <div>
            <div class="section-title">Histórico de visualização</div>
            <div style="display:flex;flex-direction:column;gap:8px">
              ${f.diario.map(d => `
                <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-sm)">
                  <div style="flex:1">
                    <div style="font-size:13px;color:var(--text2)">${formatWatchDate(d) || 'Data não informada'}${d.rewatch ? ' <span style="font-size:11px;color:var(--accent)">(rewatch)</span>' : ''}</div>
                    ${d.plataforma_nome ? `<div style="font-size:11px;color:var(--text3)">${d.plataforma_nome}</div>` : ''}
                  </div>
                  <button class="btn-icon" style="opacity:0.4" title="Remover entrada"
                    onclick="removerEntradaDiario('${filmeId}', '${d.id}')">
                    <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <div style="margin-top:28px">
          <button class="btn btn-primary" onclick="openFilmeWatchModal('${filmeId}')">
            <svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
            Registrar mais uma visualização
          </button>
        </div>
      </div>
    `;

    loadFilmePlataformasChips(filmeId);
  } catch(e) {
    el.innerHTML = `<div class="page-body text-muted">Erro: ${e.message}</div>`;
  }
}

async function desmarcarAssistidoInline(filmeId) {
  try {
    await api.desmarcarAssistido(filmeId);
    toast('Desmarcado como assistido.');
    openFilmeDetail(filmeId);
    allFilmes = await api.getFilmes();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function addWatchlistInline(filmeId) {
  try {
    await api.addWatchlist(filmeId);
    toast('Adicionado à watchlist.');
    openFilmeDetail(filmeId);
    allFilmes = await api.getFilmes();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function removeWatchlistInline(filmeId) {
  try {
    await api.removeWatchlist(filmeId);
    toast('Removido da watchlist.');
    openFilmeDetail(filmeId);
    allFilmes = await api.getFilmes();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function removerEntradaDiario(filmeId, diarioId) {
  try {
    await api.removerEntradaDiario(filmeId, diarioId);
    toast('Entrada removida.');
    openFilmeDetail(filmeId);
    allFilmes = await api.getFilmes();
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

// ── Plataformas inline ────────────────────────────────────────────────────────

async function loadFilmePlataformasChips(filmeId) {
  const el = document.getElementById(`filme-plataformas-chips-${filmeId}`);
  if (!el) return;
  try {
    const plats = await api.getFilmePlataformas(filmeId);
    if (!plats.length) {
      el.innerHTML = `<span style="font-size:12px;color:var(--text3)">Nenhuma plataforma cadastrada.</span>`;
      return;
    }
    el.innerHTML = plats.map(p => `
      <div style="display:flex;align-items:center;gap:6px;background:var(--bg3);border:1px solid var(--border);
                  border-radius:var(--radius-sm);padding:5px 10px">
        ${p.logo_path || p.logo_url
          ? `<img src="${p.logo_path || p.logo_url}" style="width:20px;height:20px;border-radius:4px;object-fit:cover" onerror="this.style.display='none'">`
          : ''
        }
        <span style="font-size:12px;color:var(--text2)">${p.nome}</span>
        <button class="btn-icon" style="padding:1px;margin-left:1px;opacity:0.5" title="Remover"
          onclick="removeFilmePlataformaChip('${filmeId}','${p.id}',this)">
          <svg viewBox="0 0 24 24" style="width:11px;height:11px;fill:currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>
    `).join('');
  } catch(e) {
    if (el) el.innerHTML = `<span style="font-size:12px;color:var(--text3)">Erro ao carregar plataformas.</span>`;
  }
}

async function syncFilmePlataformasInline(filmeId) {
  const btn = document.getElementById(`sync-plat-btn-${filmeId}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Carregando…'; }

  try {
    const preview = await api.previewFilmePlataformas(filmeId);
    const providers = preview.providers || [];
    const hasHidden = providers.some(p => !p.visivel);

    const listHtml = providers.length === 0
      ? `<p style="font-size:13px;color:var(--text3)">Nenhuma plataforma encontrada no TMDB.</p>`
      : providers.map(p => `
          <div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border)">
            ${p.logo_path || p.logo_url
              ? `<img src="${p.logo_path || p.logo_url}" style="width:24px;height:24px;border-radius:4px;object-fit:cover" onerror="this.style.display='none'">`
              : `<div style="width:24px;height:24px;border-radius:4px;background:var(--bg4)"></div>`
            }
            <span style="flex:1;font-size:13px;color:var(--text2)">${p.nome}</span>
            ${!p.visivel
              ? `<span style="font-size:11px;color:var(--text3);background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:2px 6px">oculta</span>`
              : ''
            }
          </div>
        `).join('');

    modal.show(`
      <div class="modal-header">
        <div class="modal-title">Sincronizar plataformas</div>
      </div>
      <div class="modal-body">
        <p style="font-size:13px;color:var(--text2);margin-bottom:12px">
          Plataformas encontradas no TMDB para <strong>${preview.titulo || ''}</strong>:
        </p>
        <div style="max-height:320px;overflow-y:auto;margin-bottom:${hasHidden ? '12px' : '0'}">
          ${listHtml}
        </div>
        ${hasHidden
          ? `<p style="font-size:12px;color:var(--text3)">Plataformas marcadas como <em>oculta</em> serão registradas mas não aparecerão nos chips.</p>`
          : ''
        }
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
        <button class="btn btn-primary" id="confirm-sync-btn-${filmeId}"
          onclick="confirmSyncFilmePlataformas('${filmeId}')">Sincronizar</button>
      </div>
    `);
  } catch(e) {
    toast('Erro ao carregar prévia: ' + e.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg> Sincronizar`;
    }
  }
}

async function confirmSyncFilmePlataformas(filmeId) {
  const confirmBtn = document.getElementById(`confirm-sync-btn-${filmeId}`);
  if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = 'Sincronizando…'; }
  try {
    await api.syncFilmePlataformas(filmeId);
    modal.hide();
    await loadFilmePlataformasChips(filmeId);
    toast('Plataformas sincronizadas.');
  } catch(e) {
    toast('Erro ao sincronizar: ' + e.message, 'error');
    modal.hide();
  }
}

async function showAddPlataformaInline(filmeId) {
  const existing = document.getElementById(`filme-plat-add-${filmeId}`);
  if (existing) { existing.remove(); return; }

  const section = document.getElementById(`filme-plataformas-section-${filmeId}`);
  if (!section) return;

  const div = document.createElement('div');
  div.id = `filme-plat-add-${filmeId}`;
  div.style.cssText = 'margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap';
  div.innerHTML = `<span style="font-size:12px;color:var(--text3)">Carregando…</span>`;
  section.appendChild(div);

  try {
    const [catalog, linked] = await Promise.all([
      api.getPlataformasCatalog(),
      api.getFilmePlataformasAll(filmeId),
    ]);
    const linkedIds = new Set(linked.map(p => p.id));
    const available = catalog.filter(p => !linkedIds.has(p.id));

    if (!available.length) {
      div.innerHTML = `<span style="font-size:12px;color:var(--text3)">Todas as plataformas já estão vinculadas.</span>
        <button class="btn btn-sm btn-ghost" onclick="document.getElementById('filme-plat-add-${filmeId}')?.remove()">Fechar</button>`;
      return;
    }

    div.innerHTML = `
      <select id="plat-add-select-${filmeId}"
        style="background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:var(--radius-sm);padding:4px 8px;font-size:12px">
        <option value="">Selecionar plataforma…</option>
        ${available.map(p => `<option value="${p.id}">${p.nome}</option>`).join('')}
      </select>
      <button class="btn btn-sm btn-primary" id="plat-add-btn-${filmeId}"
        onclick="confirmAddPlataforma('${filmeId}')">Adicionar</button>
      <button class="btn btn-sm btn-ghost"
        onclick="document.getElementById('filme-plat-add-${filmeId}')?.remove()">Cancelar</button>
    `;
  } catch(e) {
    toast('Erro ao carregar catálogo: ' + e.message, 'error');
    div.remove();
  }
}

async function confirmAddPlataforma(filmeId) {
  const select = document.getElementById(`plat-add-select-${filmeId}`);
  if (!select || !select.value) return;
  const btn = document.getElementById(`plat-add-btn-${filmeId}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Adicionando…'; }
  try {
    await api.addFilmePlataforma(filmeId, parseInt(select.value));
    document.getElementById(`filme-plat-add-${filmeId}`)?.remove();
    await loadFilmePlataformasChips(filmeId);
    toast('Plataforma adicionada.');
  } catch(e) {
    toast('Erro ao adicionar: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Adicionar'; }
  }
}

async function removeFilmePlataformaChip(filmeId, platId, btn) {
  btn.disabled = true;
  try {
    await api.removeFilmePlataforma(filmeId, platId);
    await loadFilmePlataformasChips(filmeId);
  } catch(e) {
    toast('Erro ao remover: ' + e.message, 'error');
    btn.disabled = false;
  }
}
