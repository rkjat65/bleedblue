"""Crawlable Studio shell: a builder rail, a canvas with Visual / Table / SQL tabs, exports."""


def studio_markup(link):
    templates = [
        ('profile', 'Player profile', 'Every measure for one player, by format'),
        ('compare', 'Compare players', 'Up to six careers on one canvas'),
        ('leaderboard', 'Leaderboard', 'Qualified record holders for any measure'),
        ('timeline', 'Timeline', 'A career year by year'),
        ('batting', 'Batting explorer', 'Opponents, venues, positions'),
        ('bowling', 'Bowling explorer', 'Wickets, average, economy'),
        ('team', 'Team form', 'Recent results for a team'),
        ('venue', 'Venue', 'Who scores where'),
        ('year', 'Year recap', 'Rank a calendar year'),
        ('match', 'Match card', 'Export a scorecard card'),
        ('custom', 'Blank canvas', 'Choose everything yourself'),
    ]
    cards = ''.join(f'<button type="button" class="st-template" data-template="{key}" aria-pressed="false"><strong>{name}</strong><small>{desc}</small></button>' for key, name, desc in templates)

    def select(ident, label, items, extra=''):
        return f'<label class="st-field">{label}<select id="{ident}"{extra}>' + ''.join(f'<option value="{value}">{text}</option>' for value, text in items) + '</select></label>'

    def segmented(ident, label, items):
        buttons = ''.join(f'<button type="button" data-value="{value}" aria-pressed="{"true" if i == 0 else "false"}">{text}</button>' for i, (value, text) in enumerate(items))
        return f'<div class="st-field"><span class="st-label">{label}</span><div class="st-seg" id="{ident}" role="group" aria-label="{label}">{buttons}</div></div>'

    photo_slots = ''.join(
        f'<section id="card-photo-{i}" class="card-photo-slot"{" hidden" if i else ""}><h3 data-photo-name>{"Card image" if i == 0 else "Second player"}</h3>'
        f'<div class="card-photo-preview"><img hidden width="72" height="88" alt=""><span data-photo-credit></span></div>'
        f'<label>Photo source {i + 1}<select aria-label="Photo source {i + 1}"><option value="auto">Automatic player photo</option><option value="upload">My image</option><option value="none">No photo</option></select></label>'
        f'<label>Add card image {i + 1}<input type="file" accept="image/jpeg,image/png,image/webp" aria-label="Add card image {i + 1}"></label>'
        f'<button type="button" data-photo-remove>Remove photo {i + 1}</button><p class="note" data-photo-status role="status">Choose a player, or add your own card image.</p></section>'
        for i in range(2))

    return f'''<div class="studio-shell">
    <section class="st-mast"><div><p class="eyebrow">CRICKET STUDIO</p><h1>Ask the archive anything, then export the answer</h1><p class="st-lede">Pick players, measures and a breakdown. Studio queries every official career and every recorded innings in your browser and gives you a chart, the table and the SQL.</p></div>
      <dl class="st-mast-facts"><div><dt>Measures</dt><dd>17</dd></div><div><dt>Datasets</dt><dd>4</dd></div><div><dt>Exports</dt><dd>PNG · SVG · CSV</dd></div></dl></section>
    <section class="st-templates" aria-label="Start from a template"><div class="st-templates-row">{cards}</div></section>
    <section class="st-workspace">
      <form id="studio-form" class="st-builder" aria-label="Builder">
        <p id="studio-status" class="st-status" role="status">Loading the archive…</p>
        <details class="st-step" open><summary><span class="st-step-num">1</span>Data</summary>
          {select('st-dataset', 'Dataset', [('careers', 'Official careers'), ('batting', 'Batting innings'), ('bowling', 'Bowling innings'), ('matches', 'Match archive')])}
          {segmented('st-gender', 'Gender', [('Men', 'Men'), ('Women', 'Women')])}
          {segmented('st-format', 'Format', [('', 'All'), ('Test', 'Test'), ('ODI', 'ODI'), ('T20I', 'T20I'), ('IPL', 'IPL')])}
          <div class="st-field" id="st-players-field"><span class="st-label">Players <small>up to six</small></span><div class="st-players" id="st-players"></div><div class="st-add"><input id="st-player-input" list="studio-players" placeholder="Type a name and press Enter" autocomplete="off" aria-label="Add a player"><button type="button" id="st-player-add">Add</button></div><datalist id="studio-players"></datalist></div>
          <div class="st-grid2">{select('st-team', 'Team', [('', 'All teams')])}{select('st-opponent', 'Opponent', [('', 'All opponents')])}</div>
          <div class="st-grid2">{select('st-venue', 'Ground', [('', 'All grounds')])}{select('st-position', 'Batting position', [('', 'Any')] + [(str(i), f'No. {i}') for i in range(1, 12)])}</div>
          <div class="st-grid2"><label class="st-field">From year<input id="st-from" type="number" min="1877" max="2100" placeholder="1877"></label><label class="st-field">To year<input id="st-to" type="number" min="1877" max="2100" placeholder="today"></label></div>
          {select('st-innings', 'Innings of match', [('', 'Any'), ('1', '1st'), ('2', '2nd'), ('3', '3rd'), ('4', '4th')])}
          <label class="st-field" id="st-match-field" hidden>Match<select id="st-match"></select></label>
        </details>
        <details class="st-step" open><summary><span class="st-step-num">2</span>Measures</summary>
          <div class="st-field"><span class="st-label">Pick any number <small>the first is the sort order</small></span><div class="st-chips" id="st-metrics" role="group" aria-label="Measures"></div></div>
          <div class="st-grid2">{select('st-sort', 'Sort by', [('', 'First measure')])}{select('st-group', 'Break down by', [('player', 'Player')])}</div>
          <div class="st-grid2"><label class="st-field">Minimum matches<input id="st-minimum" type="number" min="0" max="100000" value="0"></label><label class="st-field">Rows<input id="st-limit" type="number" min="1" max="200" value="12"></label></div>
        </details>
        <details class="st-step"><summary><span class="st-step-num">3</span>Style</summary>
          {select('design-type', 'Visual', [('auto', 'Automatic'), ('bar', 'Bars with side figures'), ('grouped', 'Grouped bars, every measure'), ('multiples', 'Small multiples'), ('column', 'Columns'), ('line', 'Line'), ('table', 'Table'), ('number', 'Headline number'), ('card', 'Match card')])}
          <div class="st-grid2">{select('design-size', 'Canvas', [('landscape', 'Landscape 1200 × 675'), ('square', 'Square 1080 × 1080'), ('portrait', 'Portrait 1080 × 1920')])}{select('design-theme', 'Theme', [('wicket', 'Crickrida dark'), ('light', 'Light'), ('navy', 'Navy'), ('paper', 'Paper')])}</div>
          <div class="st-grid2"><label class="st-field">Accent<input type="color" id="design-accent" value="#00e5ff"></label>{select('design-labels', 'Value labels', [('on', 'Show values'), ('off', 'Hide values')])}</div>
          <label class="st-field">Title<input id="design-title" maxlength="100" placeholder="Automatic title"></label>
          <label class="st-field">Subtitle<input id="design-subtitle" maxlength="160" placeholder="Your line under the title"></label>
          <details class="card-photo-editor"><summary>Card photos</summary><p class="note">Use a verified player photo or add a JPEG, PNG or WebP (up to 12 MB). Images stay in this tab and are embedded in PNG and SVG downloads only.</p><div class="card-photo-grid">{photo_slots}</div></details>
        </details>
        <div class="st-run"><button type="submit" id="build-visual" class="primary">Run</button><button type="button" id="reset-design">Reset style</button></div>
      </form>
      <div class="st-canvas-col">
        <div class="st-canvas-bar"><div class="st-tabs" role="tablist" aria-label="Output"><button type="button" role="tab" data-out="visual" aria-selected="true">Visual</button><button type="button" role="tab" data-out="table" aria-selected="false">Table</button><button type="button" role="tab" data-out="sql" aria-selected="false">SQL</button></div>
          <div class="st-exports"><button id="download-card" disabled>PNG</button><button id="download-svg" disabled>SVG</button><button id="full-preview" disabled>Open</button><button id="copy-link">Copy link</button><button id="save-design">Save</button><button id="load-design">Load</button></div></div>
        <div id="export-frame" class="st-frame" data-out-panel="visual"><div id="story-card" aria-live="polite"><p class="studio-empty">Choose a template or build a query, then run it.</p></div><p id="preview-note" class="st-note"></p></div>
        <div id="studio-result-table" class="st-table" data-out-panel="table" hidden></div>
        <div class="st-sql" data-out-panel="sql" hidden><pre id="sql" class="studio-query"></pre><p id="lake-version" class="note"></p></div>
      </div>
    </section>
    <section class="panel studio-method"><h2>What Studio can answer</h2><div class="grid three"><div><h3>Official careers</h3><p>Compare recognised career records by format: runs, average, strike rate, hundreds, wickets, economy, catches and more, side by side.</p></div><div><h3>Every recorded innings</h3><p>Slice batting and bowling innings by opponent, ground, year, batting position or innings of the match. Unknown values stay unknown.</p></div><div><h3>Ready to publish</h3><p>Choose the visual, size and theme, then export PNG, SVG or CSV. Copy a link that rebuilds the exact setup.</p></div></div><p>{link('/data-coverage/', 'See dataset coverage')} · {link('/methodology/', 'Read statistical definitions')} · {link('/records/', 'Browse the records hub')}</p></section></div>'''
