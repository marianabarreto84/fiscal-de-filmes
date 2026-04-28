async function openFilmeModal(filmeId) {
  modal.show(`<div class="modal-body" style="padding:40px 28px;text-align:center">${loadingHtml()}</div>`);

  try {
    const f = await api.getFilmeById(filmeId);
    const imgSrc = f.poster_path ? posterPathUrl(f.poster_path) : null;

    const metaParts = [];
    if (f.titulo_original && f.titulo_original !== f.titulo) metaParts.push(f.titulo_original);
    if (f.ano) metaParts.push(f.ano);
    if (f.duracao_min) metaParts.push(formatMinutes(f.duracao_min));
    if (f.nota_tmdb) metaParts.push(`★ ${f.nota_tmdb.toFixed(1)}`);

    modal.show(`
      <div class="modal-header">
        <div class="modal-title" style="font-family:var(--font-display)">${f.titulo}</div>
        <button class="btn-icon" onclick="modal.hide()">
          <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>
      <div class="modal-body">
        <div style="display:flex;gap:16px;margin-bottom:${f.sinopse || (f.diario && f.diario.length) ? '20px' : '0'}">
          ${imgSrc
            ? `<img src="${imgSrc}" alt="${f.titulo}" style="width:72px;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.4);flex-shrink:0;object-fit:cover;align-self:flex-start" onerror="this.style.display='none'">`
            : ''
          }
          <div style="flex:1;min-width:0">
            <div style="font-size:12px;color:var(--text3);line-height:1.6;margin-bottom:10px">${metaParts.join(' · ')}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              ${f.assistido
                ? `<span style="font-size:11px;background:var(--accent);color:#000;border-radius:4px;padding:2px 8px;font-weight:500">Assistido</span>`
                : ''
              }
              ${f.na_watchlist && !f.assistido
                ? `<span style="font-size:11px;background:var(--bg3);color:var(--text2);border:1px solid var(--border);border-radius:4px;padding:2px 8px">Quero Assistir</span>`
                : ''
              }
            </div>
          </div>
        </div>

        ${f.sinopse
          ? `<div style="font-size:13px;color:var(--text2);line-height:1.7;margin-bottom:20px">${f.sinopse}</div>`
          : ''
        }

        ${f.diario && f.diario.length > 0
          ? `<div>
              <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--text3);margin-bottom:8px;font-weight:500">Histórico</div>
              <div style="display:flex;flex-direction:column;gap:5px">
                ${f.diario.map(d => `
                  <div style="display:flex;align-items:center;gap:10px;padding:7px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm)">
                    <div style="flex:1;font-size:12px;color:var(--text2)">
                      ${formatWatchDate(d) || 'Data não informada'}
                      ${d.rewatch ? `<span style="font-size:10px;color:var(--accent);margin-left:6px">rewatch</span>` : ''}
                      ${d.plataforma_nome ? `<span style="font-size:10px;color:var(--text3);margin-left:6px">${d.plataforma_nome}</span>` : ''}
                    </div>
                    <button class="btn-icon" style="opacity:0.4" title="Remover entrada"
                      onclick="removerEntradaDiarioModal(${filmeId}, ${d.id})">
                      <svg viewBox="0 0 24 24" style="width:12px;height:12px;fill:currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                  </div>
                `).join('')}
              </div>
            </div>`
          : ''
        }
      </div>
      <div class="modal-footer" style="justify-content:space-between">
        <button class="btn btn-danger btn-sm" onclick="confirmDeleteFilme(${f.id}, '${f.titulo.replace(/'/g, "\\'")}')">Remover</button>
        <div style="display:flex;gap:8px">
          ${f.assistido
            ? `<button class="btn btn-secondary btn-sm" onclick="desmarcarAssistidoModal(${f.id})">Desmarcar</button>`
            : (f.na_watchlist
                ? `<button class="btn btn-ghost btn-sm" onclick="removeWatchlistModal(${f.id})">Tirar da lista</button>`
                : `<button class="btn btn-ghost btn-sm" onclick="addWatchlistModal(${f.id})">+ Quero assistir</button>`
              )
          }
          <button class="btn btn-primary btn-sm" onclick="registrarVisualizacaoModal(${f.id})">
            ${f.assistido ? '+ Visualização' : 'Marcar assistido'}
          </button>
        </div>
      </div>
    `);
  } catch(e) {
    modal.show(`<div class="modal-body" style="padding:32px 28px;color:var(--text3);font-size:13px">Erro ao carregar: ${e.message}</div>`);
  }
}

function registrarVisualizacaoModal(filmeId) {
  window._afterWatchCallback = () => openFilmeModal(filmeId);
  openFilmeWatchModal(filmeId);
}

async function desmarcarAssistidoModal(filmeId) {
  try {
    await api.desmarcarAssistido(filmeId);
    toast('Desmarcado como assistido.');
    openFilmeModal(filmeId);
    api.getFilmes().then(list => { allFilmes = list; renderFilmesGrid(); }).catch(() => {});
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function addWatchlistModal(filmeId) {
  try {
    await api.addWatchlist(filmeId);
    toast('Adicionado à watchlist.');
    openFilmeModal(filmeId);
    api.getFilmes().then(list => { allFilmes = list; renderFilmesGrid(); }).catch(() => {});
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function removeWatchlistModal(filmeId) {
  try {
    await api.removeWatchlist(filmeId);
    toast('Removido da watchlist.');
    openFilmeModal(filmeId);
    api.getFilmes().then(list => { allFilmes = list; renderFilmesGrid(); }).catch(() => {});
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

async function removerEntradaDiarioModal(filmeId, diarioId) {
  try {
    await api.removerEntradaDiario(filmeId, diarioId);
    toast('Entrada removida.');
    openFilmeModal(filmeId);
    api.getFilmes().then(list => { allFilmes = list; renderFilmesGrid(); }).catch(() => {});
  } catch(e) { toast('Erro: ' + e.message, 'error'); }
}
