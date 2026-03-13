/* ───── Toetsdruk Monitor — App Logic ───── */
(function () {
    'use strict';

    let DATA = null;

    // Current filter state
    let state = {
        jaarlaag: '1',
        module: '2',
        locatie: 'Alle',
    };

    const tooltip = document.getElementById('tooltip');

    // ── Data loading ──
    async function loadData() {
        const resp = await fetch('data/toetsdruk.json');
        DATA = await resp.json();
        render();
    }

    // ── Filter button wiring ──
    function setupControls() {
        wireGroup('jaarlaag-btns', 'jaarlaag');
        wireGroup('module-btns', 'module');
        wireGroup('locatie-btns', 'locatie');
    }

    function wireGroup(groupId, stateKey) {
        const group = document.getElementById(groupId);
        group.addEventListener('click', e => {
            const btn = e.target.closest('button');
            if (!btn) return;
            group.querySelectorAll('button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state[stateKey] = btn.dataset.value;
            render();
        });
    }

    // ── Main render ──
    function render() {
        if (!DATA) return;

        const lj = state.jaarlaag;
        const mod = state.module;
        const loc = state.locatie;
        const kalender = DATA.kalender;
        const weeks = kalender.module_weken[mod] || [];
        const toetsweken = new Set(kalender.toetsweken);
        const vakanties = new Set(kalender.vakanties);

        // Determine which classes to show
        const klassenDef = DATA.klassen[lj] || {};
        let klassen = [];
        if (loc === 'Alle') {
            klassen = [...(klassenDef.Athena || []), ...(klassenDef.Socrates || [])];
        } else {
            klassen = klassenDef[loc] || [];
        }

        // Info bar
        const infoBar = document.getElementById('info-bar');
        const totalTests = klassen.reduce((sum, klas) => {
            return sum + weeks.reduce((wsum, w) => {
                const tests = (DATA.toetsen[klas] || {})[String(w)] || [];
                return wsum + tests.length;
            }, 0);
        }, 0);
        infoBar.innerHTML = `
            <span class="info-item"><strong>${klassen.length}</strong> klassen</span>
            <span class="info-item"><strong>${weeks.length}</strong> weken</span>
            <span class="info-item"><strong>${totalTests}</strong> toetsen (excl. proefwerkweken)</span>
            <span class="info-item">Schooljaar <strong>${DATA.schooljaar}</strong></span>
        `;

        // Build header
        const head = document.getElementById('heatmap-head');
        let headerHtml = '<tr><th>Klas</th>';
        for (const w of weeks) {
            const label = kalender.week_labels[String(w)] || `wk${w}`;
            const cls = toetsweken.has(w) ? ' class="week-toetsweek"' : vakanties.has(w) ? ' class="week-vakantie"' : '';
            headerHtml += `<th${cls}>${label}<span class="week-nr">wk ${w}</span></th>`;
        }
        headerHtml += '</tr>';
        head.innerHTML = headerHtml;

        // Build body rows
        const body = document.getElementById('heatmap-body');
        let bodyHtml = '';

        // Track column totals
        const colTotals = {};
        weeks.forEach(w => colTotals[w] = 0);

        for (const klas of klassen) {
            bodyHtml += `<tr><td>${klas}</td>`;
            const klasData = DATA.toetsen[klas] || {};

            for (const w of weeks) {
                if (toetsweken.has(w)) {
                    bodyHtml += '<td class="week-toetsweek">PW-week</td>';
                    continue;
                }
                if (vakanties.has(w)) {
                    bodyHtml += '<td class="week-vakantie">vakantie</td>';
                    continue;
                }

                const tests = klasData[String(w)] || [];
                const count = tests.length;
                colTotals[w] += count;
                const heatClass = `heat-${Math.min(count, 5)}`;

                if (count === 0) {
                    bodyHtml += `<td class="${heatClass}"></td>`;
                } else {
                    const cellContent = tests.map(t =>
                        `<div class="toets-entry"><span class="vak">${esc(t.vak_kort)}</span>: <span class="type">${esc(t.type_kort)}</span></div>`
                    ).join('');
                    bodyHtml += `<td class="${heatClass}" data-klas="${esc(klas)}" data-week="${w}">${cellContent}</td>`;
                }
            }
            bodyHtml += '</tr>';
        }

        // TOTAAL row
        bodyHtml += '<tr class="totaal-row"><td>TOTAAL</td>';
        for (const w of weeks) {
            if (toetsweken.has(w)) {
                bodyHtml += '<td class="week-toetsweek">PW</td>';
                continue;
            }
            if (vakanties.has(w)) {
                bodyHtml += '<td class="week-vakantie"></td>';
                continue;
            }
            const total = colTotals[w];
            const heatClass = `heat-${Math.min(Math.ceil(total / klassen.length), 5)}`;
            bodyHtml += `<td class="${heatClass}">${total || ''}</td>`;
        }
        bodyHtml += '</tr>';

        body.innerHTML = bodyHtml;

        // Wire up tooltips on data cells
        body.querySelectorAll('td[data-klas]').forEach(td => {
            td.addEventListener('mouseenter', showTooltip);
            td.addEventListener('mousemove', moveTooltip);
            td.addEventListener('mouseleave', hideTooltip);
        });
    }

    // ── Tooltip ──
    function showTooltip(e) {
        const td = e.currentTarget;
        const klas = td.dataset.klas;
        const week = td.dataset.week;
        const tests = ((DATA.toetsen[klas] || {})[week]) || [];
        if (!tests.length) return;

        const weekLabel = DATA.kalender.week_labels[week] || `wk ${week}`;

        let html = `<h4>${klas} — ${weekLabel} (wk ${week})</h4>`;
        for (const t of tests) {
            html += `<div class="tt-entry">
                <span class="tt-vak">${esc(t.vak || t.vak_kort)}</span>
                <span class="tt-type">${esc(t.type_kort)}</span>`;
            if (t.beschrijving) {
                html += `<div class="tt-desc">${esc(t.beschrijving)}</div>`;
            }
            html += '</div>';
        }

        tooltip.innerHTML = html;
        tooltip.classList.add('visible');
        positionTooltip(e);
    }

    function moveTooltip(e) {
        positionTooltip(e);
    }

    function positionTooltip(e) {
        const pad = 12;
        let x = e.clientX + pad;
        let y = e.clientY + pad;
        const rect = tooltip.getBoundingClientRect();
        if (x + rect.width > window.innerWidth - pad) x = e.clientX - rect.width - pad;
        if (y + rect.height > window.innerHeight - pad) y = e.clientY - rect.height - pad;
        tooltip.style.left = x + 'px';
        tooltip.style.top = y + 'px';
    }

    function hideTooltip() {
        tooltip.classList.remove('visible');
    }

    // ── Utility ──
    function esc(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // ── Init ──
    document.addEventListener('DOMContentLoaded', () => {
        setupControls();
        loadData();
    });
})();
