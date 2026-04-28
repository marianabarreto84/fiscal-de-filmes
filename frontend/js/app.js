const pages = {
  dashboard:     renderDashboard,
  filmes:        renderFilmes,
  diario:        renderDiario,
  projetos:      renderProjetos,
  stats:         renderStats,
  reports:       renderReports,
  configuracoes: renderConfiguracoes,
};

let currentPage = null;
let allFilmes = [];

function navigate(page, id = null) {
  if (!pages[page]) return;

  document.querySelectorAll('.nav-links a').forEach(a => {
    a.classList.toggle('active', a.dataset.page === page);
  });

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${page}`)?.classList.add('active');

  currentPage = page;

  const hash = id ? `#${page}/${id}` : `#${page}`;
  history.replaceState(null, '', hash);

  pages[page]();
}

document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    navigate(a.dataset.page);
  });
});

async function checkApiStatus() {
  const dot = document.getElementById('api-status')?.querySelector('.status-dot');
  const txt = document.getElementById('api-status')?.querySelector('.status-text');
  try {
    await fetch('http://localhost:8001/api/stats/overview', { signal: AbortSignal.timeout(3000) });
    if (dot) dot.className = 'status-dot ok';
    if (txt) txt.textContent = 'conectado';
  } catch {
    if (dot) dot.className = 'status-dot err';
    if (txt) txt.textContent = 'sem conexão';
  }
}

checkApiStatus();
setInterval(checkApiStatus, 30000);

function restoreFromHash() {
  const hash = location.hash.replace('#', '');
  if (!hash) { navigate('dashboard'); return; }

  const parts = hash.split('/');
  const page = parts[0];
  const subPath = parts.slice(1).join('/') || null;

  if (pages[page]) {
    navigate(page, subPath);
    if (subPath) {
      const id = parseInt(subPath);
      if (page === 'filmes' && id) setTimeout(() => openFilmeDetail(id), 100);
      if (page === 'projetos' && id) setTimeout(() => openProjetoDetail(id), 100);
    }
  } else {
    navigate('dashboard');
  }
}

restoreFromHash();
