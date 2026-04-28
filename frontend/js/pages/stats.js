let chartInstances = {};

function renderPaceCard(overview) {
  const tabs = [
    { id: 'week',  label: 'Esta semana', current: overview.this_week,  previous: overview.last_week,  daysInto: overview.days_into_week,  daysTotal: 7,                       prevLabel: 'semana passada' },
    { id: 'month', label: 'Este mês',    current: overview.this_month, previous: overview.last_month, daysInto: overview.days_into_month, daysTotal: overview.days_in_month,  prevLabel: 'mês passado' },
    { id: 'year',  label: 'Este ano',    current: overview.this_year,  previous: overview.last_year,  daysInto: overview.days_into_year,  daysTotal: overview.days_in_year,   prevLabel: 'ano passado' },
  ];

  function tabHtml(tab, active) {
    const pctVal   = tab.previous > 0 ? Math.min(tab.current / tab.previous, 1) : (tab.current > 0 ? 1 : 0);
    const projected = tab.daysInto > 0 ? Math.round((tab.current / tab.daysInto) * tab.daysTotal) : 0;
    const neededPerDay = tab.previous > tab.current && tab.daysInto < tab.daysTotal
      ? ((tab.previous - tab.current) / (tab.daysTotal - tab.daysInto)).toFixed(1)
      : null;
    const barWidth = Math.round(pctVal * 100);
    const ahead = projected >= tab.previous;
    const projection = tab.previous > 0
      ? (ahead
        ? `No ritmo atual, você vai terminar o período com <strong>${projected} filmes</strong> — melhor que os <strong>${tab.previous} filmes</strong> de ${tab.prevLabel}.`
        : neededPerDay
          ? `Você precisa de <strong>${neededPerDay} filmes/dia</strong> para superar ${tab.prevLabel}.`
          : `Você superou ${tab.prevLabel}!`)
      : `Você assistiu <strong>${tab.current} filmes</strong> até agora.`;

    return `
      <div class="pace-tab-content" id="pace-tab-${tab.id}" style="display:${active ? 'block' : 'none'}">
        <div style="margin-bottom:16px">
          <div style="font-size:12px;color:var(--text3);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">Total até agora</div>
          <div style="font-size:32px;font-family:var(--font-display);color:var(--text)">${tab.current} <span style="font-size:16px;color:var(--text3)">filmes</span></div>
        </div>
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text3);margin-bottom:6px">
            <span>Agora</span>
            <span>${tab.current} / ${tab.previous} filmes (${tab.prevLabel})</span>
          </div>
          <div style="background:var(--bg4);border-radius:4px;height:6px;margin-bottom:6px;overflow:hidden">
            <div style="height:100%;width:${barWidth}%;background:var(--accent);border-radius:4px;transition:width 0.4s ease"></div>
          </div>
        </div>
        <div style="font-size:13px;color:var(--text2);line-height:1.6">${projection}</div>
      </div>`;
  }

  return `
    <div class="stat-card" style="grid-column:1/-1">
      <div style="display:flex;gap:8px;margin-bottom:20px">
        ${tabs.map((t, i) => `
          <button class="btn btn-sm ${i === 0 ? 'btn-secondary' : 'btn-ghost'}"
                  id="pace-btn-${t.id}"
                  onclick="switchPaceTab('${t.id}')">${t.label}</button>
        `).join('')}
      </div>
      ${tabs.map((t, i) => tabHtml(t, i === 0)).join('')}
    </div>`;
}

function switchPaceTab(id) {
  ['week', 'month', 'year'].forEach(t => {
    document.getElementById('pace-tab-' + t).style.display = t === id ? 'block' : 'none';
    const btn = document.getElementById('pace-btn-' + t);
    btn.className = 'btn btn-sm ' + (t === id ? 'btn-secondary' : 'btn-ghost');
  });
}

async function renderStats() {
  const el = document.getElementById('page-stats');
  el.innerHTML = loadingHtml();

  try {
    const [overview, byYear, topFilmes, byDow] = await Promise.all([
      api.getStatsOverview(),
      api.getStatsByYear(),
      api.getTopFilmes(8),
      api.getStatsByDayOfWeek(),
    ]);

    const years = byYear.map(r => r.ano);
    const currentYear = new Date().getFullYear();
    const selectedYear = years.includes(currentYear) ? currentYear : (years[years.length - 1] || currentYear);

    el.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-title">Estatísticas</div>
          <div class="page-subtitle">Seu histórico completo de visualização</div>
        </div>
      </div>
      <div class="page-body">

        <div class="section-title">Relatórios</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:32px">
          ${getReportShortcuts().map(c => `
            <div class="stat-card" style="cursor:pointer;display:flex;align-items:center;gap:12px"
                 onclick="openReport('${c.hash}')">
              <div style="color:var(--accent);flex-shrink:0">${c.icon}</div>
              <div>
                <div style="font-weight:500;color:var(--text);margin-bottom:2px">${c.label}</div>
                <div style="font-size:12px;color:var(--text3)">${c.sub}</div>
              </div>
            </div>
          `).join('')}
        </div>

        <div class="divider"></div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Total assistido</div>
            <div class="stat-value stat-accent">${overview.total_watched}</div>
            <div class="stat-sub">visualizações</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Filmes únicos</div>
            <div class="stat-value">${overview.total_filmes}</div>
            <div class="stat-sub">assistidos</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Horas totais</div>
            <div class="stat-value">${overview.total_hours_watched}</div>
            <div class="stat-sub">horas assistidas</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Hoje</div>
            <div class="stat-value">${overview.today}</div>
            <div class="stat-sub">filmes</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Esta semana</div>
            <div class="stat-value">${overview.this_week}</div>
            <div class="stat-sub">filmes</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Este mês</div>
            <div class="stat-value">${overview.this_month}</div>
            <div class="stat-sub">filmes</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Este ano</div>
            <div class="stat-value">${overview.this_year}</div>
            <div class="stat-sub">filmes</div>
          </div>
          ${renderPaceCard(overview)}
        </div>

        <div class="divider"></div>

        ${byYear.length > 0 ? `
        <div class="section-title">Filmes por ano</div>
        <div class="chart-card" style="margin-bottom:24px">
          <div class="chart-canvas-wrap"><canvas id="chart-year"></canvas></div>
        </div>
        ` : ''}

        <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
          <div class="section-title" style="margin-bottom:0">Filmes por mês</div>
          <select class="form-select" id="month-year-select" style="width:120px" onchange="loadMonthChart(this.value)">
            ${[...new Set([...years, currentYear])].sort((a,b) => b-a).map(y =>
              `<option value="${y}" ${y === selectedYear ? 'selected' : ''}>${y}</option>`
            ).join('')}
          </select>
        </div>
        <div class="chart-card" style="margin-bottom:24px">
          <div class="chart-canvas-wrap"><canvas id="chart-month"></canvas></div>
        </div>

        <div class="charts-grid">
          <div class="chart-card">
            <div class="chart-title">Dia da semana preferido</div>
            <div class="chart-canvas-wrap"><canvas id="chart-dow"></canvas></div>
          </div>
          <div class="chart-card">
            <div class="chart-title">Filmes mais assistidos</div>
            <div class="chart-canvas-wrap"><canvas id="chart-top"></canvas></div>
          </div>
        </div>

      </div>
    `;

    await loadChartJs();

    const accent    = '#00b020';
    const green     = '#5aba8a';
    const blue      = '#5a8aba';
    const textColor = '#9898a8';
    const gridColor = 'rgba(255,255,255,0.06)';

    const baseOpts = {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: textColor, font: { size: 11 } }, grid: { color: gridColor } },
        y: { ticks: { color: textColor, font: { size: 11 } }, grid: { color: gridColor }, beginAtZero: true }
      }
    };

    if (byYear.length > 0) {
      destroyChart('chart-year');
      chartInstances['chart-year'] = new Chart(document.getElementById('chart-year'), {
        type: 'bar',
        data: { labels: byYear.map(r => r.ano), datasets: [{ data: byYear.map(r => r.filmes), backgroundColor: accent, borderRadius: 4 }] },
        options: { ...baseOpts }
      });
    }

    await loadMonthChart(selectedYear);

    destroyChart('chart-dow');
    chartInstances['chart-dow'] = new Chart(document.getElementById('chart-dow'), {
      type: 'bar',
      data: { labels: byDow.map(r => r.dia), datasets: [{ data: byDow.map(r => r.filmes), backgroundColor: green, borderRadius: 4 }] },
      options: { ...baseOpts }
    });

    if (topFilmes.length > 0) {
      destroyChart('chart-top');
      chartInstances['chart-top'] = new Chart(document.getElementById('chart-top'), {
        type: 'bar',
        data: {
          labels: topFilmes.map(f => f.titulo.length > 18 ? f.titulo.slice(0,18)+'…' : f.titulo),
          datasets: [{ data: topFilmes.map(f => f.vezes_assistido), backgroundColor: accent, borderRadius: 4 }]
        },
        options: { ...baseOpts, indexAxis: 'y', scales: { x: baseOpts.scales.x, y: baseOpts.scales.y } }
      });
    }

  } catch(e) {
    el.innerHTML = `<div class="page-body text-muted">Erro: ${e.message}</div>`;
  }
}

function destroyChart(id) {
  if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

async function loadMonthChart(year) {
  const data = await api.getStatsByMonth(year);
  const textColor = '#9898a8';
  const gridColor = 'rgba(255,255,255,0.06)';
  const monthNames = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  destroyChart('chart-month');
  const canvas = document.getElementById('chart-month');
  if (!canvas) return;

  chartInstances['chart-month'] = new Chart(canvas, {
    type: 'bar',
    data: { labels: monthNames, datasets: [{ data: data.map(r => r.filmes), backgroundColor: '#00b020', borderRadius: 4 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: textColor, font: { size: 11 } }, grid: { color: gridColor } },
        y: { ticks: { color: textColor, font: { size: 11 } }, grid: { color: gridColor }, beginAtZero: true }
      }
    }
  });
}

function loadChartJs() {
  return new Promise((resolve) => {
    if (window.Chart) { resolve(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    s.onload = resolve;
    document.head.appendChild(s);
  });
}
