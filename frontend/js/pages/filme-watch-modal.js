// Modal para registrar visualização de filme

async function openFilmeWatchModal(filmeId) {
  let plataformas = [];
  try { plataformas = await api.getFilmePlataformas(filmeId); } catch(e) {}

  modal.show(`
    <div class="modal-header">
      <div class="modal-title">Registrar visualização</div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Data de visualização</label>
        ${dateInputGroupHtml('watch-')}
      </div>

      ${plataformas.length > 0 ? `
        <div class="form-group">
          <label class="form-label">Plataforma</label>
          <select class="form-select" id="watch-plataforma">
            <option value="">Não informar</option>
            ${plataformas.map(p => `<option value="${p.id}">${p.nome}</option>`).join('')}
          </select>
        </div>
      ` : ''}

      <div class="form-group">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
          <input type="checkbox" id="watch-rewatch" style="accent-color:var(--accent)">
          <span style="font-size:13px">Rewatch (já vi antes)</span>
        </label>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="modal.hide()">Cancelar</button>
      <button class="btn btn-primary" onclick="submitWatchFilme('${filmeId}')" data-label="Marcar assistido">Marcar assistido</button>
    </div>
  `);
}

async function submitWatchFilme(filmeId) {
  const dateVals = getDateValues('watch-');
  const platEl = document.getElementById('watch-plataforma');
  const rewatch = document.getElementById('watch-rewatch')?.checked || false;

  modal.setLoading('.modal-footer .btn-primary', true);

  try {
    await api.marcarAssistido(filmeId, {
      filme_id:         filmeId,
      ...dateVals,
      plataforma_id:    platEl ? (parseInt(platEl.value) || null) : null,
      rewatch,
    });
    toast('Filme marcado como assistido!');
    modal.hide();
    if (window._afterWatchCallback) {
      const cb = window._afterWatchCallback;
      window._afterWatchCallback = null;
      cb();
    } else {
      openFilmeDetail(filmeId);
    }
    allFilmes = await api.getFilmes();
  } catch(e) {
    toast('Erro: ' + e.message, 'error');
    modal.setLoading('.modal-footer .btn-primary', false);
  }
}
