// ── Diário page ──────────────────────────────────────────────────────────────

let diarioDays = [];

let diarioRange = (() => {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  const lastDay = new Date(y, m, 0).getDate();
  return {
    from: `${y}-${String(m).padStart(2,'0')}-01`,
    to:   `${y}-${String(m).padStart(2,'0')}-${String(lastDay).padStart(2,'0')}`,
    preset: 'month',
  };
})();

function diarioRangePresets() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  const d = now.getDate();
  const pad = n => String(n).padStart(2,'0');
  const fmt = (yr, mo, dy) => `${yr}-${pad(mo)}-${pad(dy)}`;
  const thisMonthLast = new Date(y, m, 0).getDate();
  const prevM = m === 1 ? 12 : m - 1;
  const prevY = m === 1 ? y - 1 : y;
  const prevMonthLast = new Date(prevY, prevM, 0).getDate();
  const d7  = new Date(now); d7.setDate(d7.getDate() - 6);
  const d30 = new Date(now); d30.setDate(d30.getDate() - 29);
  return {
    month:      { from: fmt(y, m, 1), to: fmt(y, m, thisMonthLast), label: 'Este mês' },
    last_month: { from: fmt(prevY, prevM, 1), to: fmt(prevY, prevM, prevMonthLast), label: 'Mês passado' },
    '7d':       { from: fmt(d7.getFullYear(), d7.getMonth()+1, d7.getDate()), to: fmt(y,m,d), label: 'Últimos 7 dias' },
    '30d':      { from: fmt(d30.getFullYear(), d30.getMonth()+1, d30.getDate()), to: fmt(y,m,d), label: 'Últimos 30 dias' },
    year:       { from: fmt(y, 1, 1), to: fmt(y, 12, 31), label: `${y}` },
  };
}

function applyDiarioPreset(preset) {
  const presets = diarioRangePresets();
  const p = presets[preset];
  if (!p) return;
  diarioRange = { from: p.from, to: p.to, preset };
  renderDiario();
}

function applyDiarioCustomRange() {
  const from = document.getElementById('diario-range-from')?.value;
  const to   = document.getElementById('diario-range-to')?.value;
  if (!from || !to) return;
  if (from > to) { toast('Data inicial deve ser antes da data final.', 'error'); return; }
  diarioRange = { from, to, preset: 'custom' };
  renderDiario();
}

async function renderDiario() {
  const el = document.getElementById('page-diario');
  el.innerHTML = loadingHtml();
  try {
    diarioDays = await api.getDiario(diarioRange.from, diarioRange.to);

    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    const todayInRange = diarioRange.from <= todayStr && todayStr <= diarioRange.to;

    if (todayInRange) {
      const todayY = now.getFullYear();
      const todayM = now.getMonth() + 1;
      const todayD = now.getDate();
      const hasToday = diarioDays.some(d => d.ano === todayY && d.mes === todayM && d.dia === todayD);
      if (!hasToday) {
        diarioDays.unshift({ ano: todayY, mes: todayM, dia: todayD, filmes: [] });
      }
    }

    renderDiarioPage(el);
  } catch (e) {
    el.innerHTML = `<div class="page-body"><p style="color:var(--red)">Erro ao carregar diário: ${e.message}</p></div>`;
  }
}

function diarioRangeBarHtml() {
  const presets = diarioRangePresets();
  return `
    <div class="diary-range-bar">
      <div class="diary-range-presets">
        ${Object.entries(presets).map(([key, p]) => `
          <button class="diary-range-preset ${diarioRange.preset === key ? 'active' : ''}"
            onclick="applyDiarioPreset('${key}')">${p.label}</button>
        `).join('')}
      </div>
      <div class="diary-range-custom">
        <input type="date" class="diary-range-input" id="diario-range-from" value="${diarioRange.from}" onchange="applyDiarioCustomRange()">
        <span class="diary-range-sep">até</span>
        <input type="date" class="diary-range-input" id="diario-range-to" value="${diarioRange.to}" onchange="applyDiarioCustomRange()">
      </div>
    </div>
  `;
}

function renderDiarioPage(el) {
  const days = diarioDays;
  const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  el.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Diário</div>
        <div class="page-subtitle">Registro de filmes assistidos por dia</div>
      </div>
    </div>
    ${diarioRangeBarHtml()}
    <div class="page-body diary-body" id="diario-body">
      ${days.length === 0
        ? emptyState('📅', 'Nenhum filme neste período', 'Marque filmes como assistidos para que apareçam aqui.')
        : days.map(day => {
            const dateObj = new Date(day.ano, day.mes - 1, day.dia);
            const wday = weekdays[dateObj.getDay()];
            return `
              <div class="diary-day">
                <div class="diary-day-header">
                  <span class="diary-day-weekday">${wday}</span>
                  <span class="diary-day-date">${day.dia} de ${monthFull(day.mes)} de ${day.ano}</span>
                  <span class="diary-day-count">${day.filmes.length} filme${day.filmes.length !== 1 ? 's' : ''}</span>
                </div>
                <div class="diary-day-episodes">
                  ${day.filmes.map(f => filmeDiarioCardHtml(f)).join('')}
                  <div class="diary-ep-add card" onclick="openWatchLogModal(${day.ano}, ${day.mes}, ${day.dia})">
                    <div class="diary-ep-add-inner">
                      <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                    </div>
                  </div>
                </div>
              </div>
            `;
          }).join('')
      }
    </div>
  `;
}

function filmeDiarioCardHtml(f) {
  const imgSrc = f.poster_path ? posterPathUrl(f.poster_path) : null;
  const hora = (f.hora_assistido !== null && f.hora_assistido !== undefined)
    ? `${String(f.hora_assistido).padStart(2,'0')}:${String(f.minuto_assistido || 0).padStart(2,'0')}`
    : '';

  return `
    <div class="diary-ep-card" onclick="openFilmeDiarioModal('${f.diario_id}')">
      ${imgSrc
        ? `<img class="diary-ep-poster" src="${imgSrc}" alt="${f.filme_titulo}" onerror="this.classList.add('hidden');this.nextElementSibling.style.display='flex'">`
        : ''
      }
      <div class="diary-ep-poster-placeholder" style="${imgSrc ? 'display:none' : ''}"></div>
      <div class="diary-ep-info">
        <div class="diary-ep-series">${f.filme_titulo}</div>
        ${f.duracao_min ? `<div class="diary-ep-code">${formatMinutes(f.duracao_min)}</div>` : ''}
      </div>
      <div class="diary-ep-footer">
        <span class="diary-ep-time">${hora}</span>
        ${f.plataforma_logo
          ? `<img class="diary-ep-provider-logo" src="${f.plataforma_logo}" alt="${f.plataforma_nome || ''}" onerror="this.style.display='none'">`
          : ''
        }
      </div>
    </div>
  `;
}

// ── Modal de entrada do diário ───────────────────────────────────────────────

async function openFilmeDiarioModal(diarioId) {
  let entry = null;
  let day = null;
  for (const d of diarioDays) {
    const found = (d.filmes || []).find(fl => fl.diario_id === diarioId);
    if (found) { entry = found; day = d; break; }
  }
  if (!entry) { toast('Registro não encontrado.', 'error'); return; }

  modal.show(`<div class="modal-body" style="padding:40px 28px;text-align:center">${loadingHtml()}</div>`);

  let f;
  try {
    f = await api.getFilmeById(entry.filme_id);
  } catch (e) {
    modal.show(`<div class="modal-body" style="padding:32px 28px;color:var(--text3);font-size:13px">Erro ao carregar: ${e.message}</div>`);
    return;
  }

  const imgSrc = f.poster_path ? posterPathUrl(f.poster_path) : null;
  const metaParts = [];
  if (f.titulo_original && f.titulo_original !== f.titulo) metaParts.push(f.titulo_original);
  if (f.ano) metaParts.push(f.ano);
  if (f.duracao_min) metaParts.push(formatMinutes(f.duracao_min));

  const dataStr = `${String(day.dia).padStart(2,'0')} de ${monthFull(day.mes)} de ${day.ano}`;
  const horaStr = entry.hora_assistido != null
    ? `${String(entry.hora_assistido).padStart(2,'0')}:${String(entry.minuto_assistido ?? 0).padStart(2,'0')}`
    : null;

  modal.show(`
    <div class="modal-header">
      <div>
        ${metaParts.length
          ? `<div style="font-size:12px;color:var(--text3);margin-bottom:4px">${metaParts.join(' · ')}</div>`
          : ''
        }
        <div class="modal-title" style="font-family:var(--font-display)">${f.titulo}</div>
      </div>
      <button class="btn-icon" onclick="modal.hide()">
        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </button>
    </div>
    <div class="modal-body">
      ${imgSrc || f.sinopse
        ? `<div style="display:flex;gap:16px;margin-bottom:20px">
             ${imgSrc
               ? `<img src="${imgSrc}" alt="${f.titulo}" style="width:96px;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.4);flex-shrink:0;object-fit:cover;align-self:flex-start" onerror="this.style.display='none'">`
               : ''
             }
             ${f.sinopse
               ? `<div style="flex:1;min-width:0;font-size:12.5px;color:var(--text2);line-height:1.6">${f.sinopse}</div>`
               : ''
             }
           </div>`
        : ''
      }

      <div style="border-top:1px solid var(--border);padding-top:16px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
          <div>
            <div style="font-size:11px;color:var(--text3);margin-bottom:4px;text-transform:uppercase;letter-spacing:0.06em">Assistido em</div>
            <div style="font-size:16px;font-weight:500;color:var(--accent)">${dataStr}${horaStr ? ' · ' + horaStr : ''}</div>
            ${entry.plataforma_nome ? `<div style="font-size:12px;color:var(--text3);margin-top:4px">${entry.plataforma_nome}</div>` : ''}
            ${entry.rewatch ? `<div style="font-size:11px;color:var(--accent);margin-top:4px">rewatch</div>` : ''}
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0">
            <button class="btn btn-secondary btn-sm" onclick="modal.hide(); openFilmeModal('${f.id}')">Ver filme</button>
            <button class="btn btn-danger btn-sm" id="filme-diario-modal-delete">Remover</button>
          </div>
        </div>
      </div>
    </div>
  `);

  document.getElementById('filme-diario-modal-delete').onclick = async () => {
    try {
      await api.removerEntradaDiario(entry.filme_id, diarioId);
      modal.hide();
      toast('Registro removido.');
      await renderDiario();
    } catch (e) {
      toast('Erro ao remover: ' + e.message, 'error');
    }
  };
}
