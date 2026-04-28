async function renderDashboard() {
  const el = document.getElementById('page-dashboard');
  el.innerHTML = loadingHtml();

  try {
    const [overview, recent, topFilmes] = await Promise.all([
      api.getStatsOverview(),
      api.getRecent(10),
      api.getTopFilmes(5),
    ]);

    el.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-title">Dashboard</div>
          <div class="page-subtitle">Seu progresso geral</div>
        </div>
      </div>
      <div class="page-body">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Filmes</div>
            <div class="stat-value">${overview.total_filmes}</div>
            <div class="stat-sub">assistidos</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Total registros</div>
            <div class="stat-value stat-accent">${overview.total_watched}</div>
            <div class="stat-sub">visualizações</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Horas assistidas</div>
            <div class="stat-value">${overview.total_hours_watched}</div>
            <div class="stat-sub">horas no total</div>
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
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:8px">
          <div>
            <div class="section-title">Assistidos recentemente</div>
            ${recent.length === 0
              ? '<div class="text-muted" style="font-size:13px">Nenhum filme marcado ainda.</div>'
              : `<div class="recent-list">
                ${recent.map(r => `
                  <div class="recent-item" onclick="openFilmeDetail('${r.filme_id}')" style="cursor:pointer">
                    ${r.poster_path
                      ? `<img src="${posterPathUrl(r.poster_path)}" class="recent-poster" onerror="this.style.display='none'">`
                      : `<div class="recent-poster" style="display:flex;align-items:center;justify-content:center;color:var(--text3)">🎬</div>`
                    }
                    <div class="recent-info">
                      <div class="recent-ep" style="font-weight:500">${r.filme_titulo}</div>
                      <div class="recent-series">${r.duracao_min ? formatMinutes(r.duracao_min) : ''}</div>
                    </div>
                    <div class="recent-date">${r.assistido_em ? new Date(r.assistido_em).toLocaleDateString('pt-BR') : ''}</div>
                  </div>
                `).join('')}
              </div>`
            }
          </div>

          <div>
            <div class="section-title">Filmes mais assistidos</div>
            ${topFilmes.length === 0
              ? '<div class="text-muted" style="font-size:13px">Nenhum filme ainda.</div>'
              : `<div class="recent-list">
                ${topFilmes.map(f => `
                  <div class="recent-item">
                    <div class="recent-info">
                      <div class="recent-ep" style="font-weight:500">${f.titulo}</div>
                      <div class="recent-series">${f.vezes_assistido}x · ${formatMinutes(f.minutos_totais)}</div>
                    </div>
                  </div>
                `).join('')}
              </div>`
            }
          </div>
        </div>
      </div>
    `;
  } catch (e) {
    el.innerHTML = `<div class="page-body"><div class="text-muted">Erro ao carregar dashboard: ${e.message}</div></div>`;
  }
}
