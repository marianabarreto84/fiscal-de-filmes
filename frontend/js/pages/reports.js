let reportChartInstances = {};

function destroyReportChart(id) {
  if (reportChartInstances[id]) { reportChartInstances[id].destroy(); delete reportChartInstances[id]; }
}

function _pad2(n) { return String(n).padStart(2, '0'); }

function _isoWeekOf(d) {
  const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = tmp.getUTCDay() || 7;
  tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
  return { year: tmp.getUTCFullYear(), week: Math.ceil(((tmp - yearStart) / 86400000 + 1) / 7) };
}

function getReportShortcuts() {
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const yDate = `${yesterday.getFullYear()}-${_pad2(yesterday.getMonth()+1)}-${_pad2(yesterday.getDate())}`;
  const lastWeekDate = new Date(today); lastWeekDate.setDate(today.getDate() - 7);
  const lw = _isoWeekOf(lastWeekDate);
  const lastMonthDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const prevYear = today.getFullYear() - 1;
  return [
    { label: 'Ontem',         sub: `${_pad2(yesterday.getDate())}/${_pad2(yesterday.getMonth()+1)}/${yesterday.getFullYear()}`, hash: `#reports/daily/${yDate}`,                                               icon: `<svg viewBox="0 0 24 24" style="width:22px;height:22px;fill:currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm4.24 16L11 13.45V7h1.5v5.8l4.62 3.07-1.28 1.96-.61-.83z"/></svg>` },
    { label: 'Semana passada',sub: `Semana ${lw.week} de ${lw.year}`,                                                           hash: `#reports/weekly/${lw.year}/${lw.week}`,                                 icon: `<svg viewBox="0 0 24 24" style="width:22px;height:22px;fill:currentColor"><path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/></svg>` },
    { label: 'Mês passado',   sub: `${monthFull(lastMonthDate.getMonth()+1)} de ${lastMonthDate.getFullYear()}`,                 hash: `#reports/monthly/${lastMonthDate.getFullYear()}/${lastMonthDate.getMonth()+1}`, icon: `<svg viewBox="0 0 24 24" style="width:22px;height:22px;fill:currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>` },
    { label: 'Ano passado',   sub: String(prevYear),                                                                             hash: `#reports/annual/${prevYear}`,                                           icon: `<svg viewBox="0 0 24 24" style="width:22px;height:22px;fill:currentColor"><path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z"/></svg>` },
  ];
}

async function renderReports() {
  const parts = location.hash.replace('#', '').split('/');
  const periodType = parts[1];
  if (!periodType) renderReportsHub();
  else await renderReportDetail(periodType, parts.slice(2));
}

function renderReportsHub() {
  const el = document.getElementById('page-reports');
  el.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Relatórios</div>
        <div class="page-subtitle">Análise detalhada por período</div>
      </div>
    </div>
    <div class="page-body">
      <div class="section-title">Acesso rápido</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px">
        ${getReportShortcuts().map(c => `
          <div class="stat-card" style="cursor:pointer;display:flex;flex-direction:column;gap:12px"
               onclick="openReport('${c.hash}')">
            <div style="color:var(--accent)">${c.icon}</div>
            <div>
              <div style="font-weight:500;margin-bottom:2px">${c.label}</div>
              <div style="font-size:12px;color:var(--text3)">${c.sub}</div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function openReport(hash) {
  history.replaceState(null, '', hash);
  renderReports();
}

async function renderReportDetail(periodType, params) {
  const el = document.getElementById('page-reports');
  el.innerHTML = loadingHtml();

  let data, label, periodLabel;

  try {
    if (periodType === 'daily') {
      const date = params[0];
      data = await api.getReportDaily(date);
    } else if (periodType === 'weekly') {
      data = await api.getReportWeekly(parseInt(params[0]), parseInt(params[1]));
    } else if (periodType === 'monthly') {
      data = await api.getReportMonthly(parseInt(params[0]), parseInt(params[1]));
    } else if (periodType === 'annual') {
      data = await api.getReportAnnual(parseInt(params[0]));
    } else {
      renderReportsHub();
      return;
    }

    el.innerHTML = `
      <div class="page-header">
        <div>
          <button class="btn btn-ghost" style="margin-bottom:8px" onclick="openReport('#reports')">
            <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
            Relatórios
          </button>
          <div class="page-title">${data.label}</div>
        </div>
      </div>
      <div class="page-body">
        <div class="stats-grid" style="margin-bottom:32px">
          <div class="stat-card">
            <div class="stat-label">Filmes assistidos</div>
            <div class="stat-value stat-accent">${data.total_filmes}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Tempo total</div>
            <div class="stat-value">${formatMinutes(data.total_minutos)}</div>
          </div>
        </div>

        ${data.top_filmes?.length > 0 ? `
          <div class="section-title">Filmes</div>
          <div class="series-grid" style="margin-bottom:32px">
            ${data.top_filmes.map(f => `
              <div class="series-card" onclick="openFilmeDetail(${f.filme_id})" style="cursor:pointer">
                <div class="series-poster">
                  ${f.poster_path
                    ? `<img src="${posterPathUrl(f.poster_path)}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=series-poster-placeholder>🎬</div>'">`
                    : `<div class="series-poster-placeholder">🎬</div>`
                  }
                </div>
                <div class="series-info">
                  <div class="series-title">${f.titulo}</div>
                  ${f.vezes > 1 ? `<div class="series-meta">${f.vezes}x</div>` : ''}
                </div>
              </div>
            `).join('')}
          </div>
        ` : ''}

        ${data.top_plataformas?.length > 0 ? `
          <div class="section-title">Plataformas</div>
          <div style="display:flex;flex-wrap:wrap;gap:12px">
            ${data.top_plataformas.map(p => `
              <div style="display:flex;align-items:center;gap:8px;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px 14px">
                ${p.logo_path || p.logo_url ? `<img src="${p.logo_path || p.logo_url}" style="width:24px;height:24px;border-radius:4px;object-fit:cover">` : ''}
                <span style="font-size:13px">${p.nome}</span>
                <span style="font-size:11px;color:var(--accent);margin-left:4px">${p.vezes}×</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  } catch(e) {
    el.innerHTML = `<div class="page-body text-muted">Erro: ${e.message}</div>`;
  }
}
