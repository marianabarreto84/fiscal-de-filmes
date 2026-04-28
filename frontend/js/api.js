const API_BASE = 'http://localhost:8001/api';

const api = {
  async get(path) {
    const r = await fetch(API_BASE + path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(API_BASE + path, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(API_BASE + path, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async patch(path, body) {
    const r = await fetch(API_BASE + path, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async delete(path) {
    const r = await fetch(API_BASE + path, { method: 'DELETE' });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },

  // Filmes
  getFilmes:       ()            => api.get('/filmes'),
  getFilmeById:    (id)          => api.get(`/filmes/${id}`),
  createFilme:     (data)        => api.post('/filmes', data),
  deleteFilme:     (id)          => api.delete(`/filmes/${id}`),
  syncMissingPosters: ()         => api.post('/filmes/posters/sync', {}),
  marcarAssistido: (id, data)    => api.post(`/filmes/${id}/assistir`, data),
  desmarcarAssistido: (id)       => api.delete(`/filmes/${id}/assistir`),
  removerEntradaDiario: (fid, did) => api.delete(`/filmes/${fid}/assistir/${did}`),
  addWatchlist:    (id)          => api.post(`/filmes/${id}/watchlist`, {}),
  removeWatchlist: (id)          => api.delete(`/filmes/${id}/watchlist`),

  // TMDB
  searchTmdb:       (q)         => api.get(`/tmdb/search?q=${encodeURIComponent(q)}`),
  getTmdbMovie:     (id)        => api.get(`/tmdb/movie/${id}`),
  getTmdbProviders: (id)        => api.get(`/tmdb/movie/${id}/providers`),

  // Plataformas
  getFilmePlataformas:    (fid) => api.get(`/plataformas/filme/${fid}`),
  getFilmePlataformasAll: (fid) => api.get(`/plataformas/filme/${fid}/all`),
  addFilmePlataforma:     (fid, pid) => api.post(`/plataformas/filme/${fid}`, { plataforma_id: pid }),
  removeFilmePlataforma:  (fid, pid) => api.delete(`/plataformas/filme/${fid}/${pid}`),
  getPlataformasCatalog:  ()    => api.get('/plataformas/catalog'),
  getPlataformaDefaults:  ()    => api.get('/plataformas/defaults'),
  getFilmePlataformaPadrao: (fid) => api.get(`/plataformas/defaults/${fid}`),
  setFilmePlataformaPadrao: (fid, pid) => api.put(`/plataformas/defaults/${fid}`, { plataforma_id: pid ?? null }),
  getPlataformasConfig:   ()    => api.get('/plataformas/config'),
  patchPlataformaConfig:  (id, data) => api.patch(`/plataformas/config/${id}`, data),
  reorderPlataformas:     (ids) => api.post('/plataformas/config/reorder', { plataforma_ids: ids }),
  syncAllPlataformas:       ()    => api.post('/plataformas/sync-all', {}),
  syncFilmePlataformas:     (fid) => api.post(`/plataformas/sync/${fid}`, {}),
  previewFilmePlataformas:  (fid) => api.get(`/plataformas/preview/${fid}`),

  // Diário
  getDiario:      (from, to) => api.get(`/diario${from && to ? `?date_from=${from}&date_to=${to}` : ''}`),
  reorderDiario:  (body)     => api.patch('/diario/reorder', body),

  // Projetos
  getProjetos:           ()           => api.get('/projetos'),
  getProjeto:            (id)         => api.get(`/projetos/${id}`),
  createProjeto:         (data)       => api.post('/projetos', data),
  updateProjeto:         (id, data)   => api.put(`/projetos/${id}`, data),
  deleteProjeto:         (id)         => api.delete(`/projetos/${id}`),
  addFilmesToProjeto:    (pid, fids)  => api.post(`/projetos/${pid}/filmes`, { filme_ids: fids }),
  removeFilmeFromProjeto:(pid, fid)   => api.delete(`/projetos/${pid}/filmes/${fid}`),

  // Configurações
  getConfig:  (chave)        => api.get(`/configuracao/${chave}`),
  setConfig:  (chave, valor) => api.put(`/configuracao/${chave}`, { valor }),

  // Storage
  getStorage:       () => api.get('/storage'),
  calculateStorage: () => api.post('/storage/calculate', {}),

  // Relatórios
  getReportDaily:   (date)       => api.get(`/reports/daily/${date}`),
  getReportWeekly:  (year, week) => api.get(`/reports/weekly/${year}/${week}`),
  getReportMonthly: (year, month)=> api.get(`/reports/monthly/${year}/${month}`),
  getReportAnnual:  (year)       => api.get(`/reports/annual/${year}`),

  // Stats
  getStatsOverview:    ()      => api.get('/stats/overview'),
  getStatsByMonth:     (year)  => api.get(`/stats/by-month${year ? '?year=' + year : ''}`),
  getStatsByYear:      ()      => api.get('/stats/by-year'),
  getStatsByDayOfWeek: ()      => api.get('/stats/by-day-of-week'),
  getTopFilmes:        ()      => api.get('/stats/top-filmes'),
  getRecent:           (n)     => api.get(`/stats/recent${n ? '?limit=' + n : ''}`),
  getAvailableYears:   ()      => api.get('/stats/available-years'),
};
