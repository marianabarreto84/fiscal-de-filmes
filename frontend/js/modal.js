const modal = {
  show(content) {
    document.getElementById('modal').innerHTML = content;
    document.getElementById('modal-overlay').classList.remove('hidden');
  },
  hide() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.getElementById('modal').innerHTML = '';
  },
  setLoading(sel, loading) {
    const btn = document.querySelector(sel);
    if (!btn) return;
    btn.disabled = loading;
    btn.textContent = loading ? 'aguarde...' : btn.dataset.label || btn.textContent;
  }
};

document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === document.getElementById('modal-overlay')) modal.hide();
});
