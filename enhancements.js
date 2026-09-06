/* Shared navigation, accessibility and table downloads for India archive views. */
(() => {
  const bar = document.createElement('div');
  bar.className = 'professional-toolbar';
  bar.innerHTML = '<span><a href="/">Home</a> / <a href="/international/">International cricket</a> / India archive</span><form action="/search/"><input name="q" aria-label="Search India archive" placeholder="Search India archive…" required minlength="2"><button>Search</button></form>';
  document.querySelector('.content-wrap')?.prepend(bar);
  document.querySelectorAll('input,select').forEach(input => {
    if (!input.labels?.length && !input.getAttribute('aria-label')) input.setAttribute('aria-label', input.placeholder || input.id.replace(/([A-Z])/g, ' $1'));
  });
  function downloadTable(table) {
    const csv = [...table.rows].map(row => [...row.cells].map(cell => '"' + cell.innerText.replace(/^[=+@-]/, "'$&").replace(/"/g, '""') + '"').join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], {type: 'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = 'cricket-wicket-' + (table.id || 'table') + '.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  document.querySelectorAll('table[id]').forEach(table => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'export-btn'; button.textContent = 'Download visible rows CSV ↓'; button.addEventListener('click', () => downloadTable(table)); table.closest('.table-scroll')?.before(button);
  });
})();
