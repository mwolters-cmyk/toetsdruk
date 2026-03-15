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

    // ── Helper: is dit bovenbouw? ──
    function isBovenbouw() {
        return parseInt(state.jaarlaag) >= 4;
    }

    // ── Module mapping: klas 6 gebruikt modules 4-5 ──
    function getEffectiveModule() {
        const lj = parseInt(state.jaarlaag);
        const mod = parseInt(state.module);
        if (lj === 6) {
            return String(mod + 3); // knop 1→mod 4, knop 2→mod 5
        }
        return state.module;
    }

    // ── Update module-knoplabels voor klas 6 ──
    function updateModuleLabels() {
        const lj = parseInt(state.jaarlaag);
        const btns = document.querySelectorAll('#module-btns button');
        if (lj === 6) {
            btns[0].textContent = '4';
            btns[1].textContent = '5';
            btns[2].style.display = 'none';
            // Als module 3 actief was, reset naar module 1 (=4)
            if (state.module === '3') {
                btns[2].classList.remove('active');
                btns[0].classList.add('active');
                state.module = '1';
            }
        } else {
            btns[0].textContent = '1';
            btns[1].textContent = '2';
            btns[2].textContent = '3';
            btns[2].style.display = '';
        }
    }

    // ── Main render ──
    function render() {
        if (!DATA) return;

        // Toggle locatie-filter visibility
        const locatieGroup = document.getElementById('locatie-btns').closest('.control-group');
        locatieGroup.style.display = isBovenbouw() ? 'none' : '';

        // Update module labels (klas 6 = modules 4-5)
        updateModuleLabels();

        if (isBovenbouw()) {
            renderBovenbouw();
        } else {
            renderOnderbouw();
        }
    }

    // ── Onderbouw render (bestaande logica) ──
    function renderOnderbouw() {
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
        klassen.sort((a, b) => a.localeCompare(b, 'nl'));

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

        // Wire up tooltips
        body.querySelectorAll('td[data-klas]').forEach(td => {
            td.addEventListener('mouseenter', showTooltip);
            td.addEventListener('mousemove', moveTooltip);
            td.addEventListener('mouseleave', hideTooltip);
        });
    }

    // ── Bovenbouw render (rijen = vakken) ──
    function renderBovenbouw() {
        const lj = state.jaarlaag;
        const mod = getEffectiveModule();
        const kalender = DATA.kalender;
        const weeks = kalender.module_weken[mod] || [];
        const toetsweken = new Set(kalender.toetsweken);
        const vakanties = new Set(kalender.vakanties);

        // Bovenbouw data
        const bvData = (DATA.bovenbouw || {})[lj] || {};
        const vakken = bvData.vakken || [];
        const vakToetsen = bvData.toetsen || {};

        // Info bar
        const infoBar = document.getElementById('info-bar');
        const totalTests = vakken.reduce((sum, vak) => {
            return sum + weeks.reduce((wsum, w) => {
                const tests = (vakToetsen[vak] || {})[String(w)] || [];
                return wsum + tests.length;
            }, 0);
        }, 0);
        infoBar.innerHTML = `
            <span class="info-item"><strong>${vakken.length}</strong> vakken</span>
            <span class="info-item"><strong>${weeks.length}</strong> weken</span>
            <span class="info-item"><strong>${totalTests}</strong> toetsen (excl. proefwerkweken)</span>
            <span class="info-item">Schooljaar <strong>${DATA.schooljaar}</strong></span>
        `;

        // Build header
        const head = document.getElementById('heatmap-head');
        let headerHtml = '<tr><th>Vak</th>';
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
        const colTotals = {};
        weeks.forEach(w => colTotals[w] = 0);

        for (const vak of vakken) {
            bodyHtml += `<tr><td>${esc(vak)}</td>`;
            const vakData = vakToetsen[vak] || {};

            for (const w of weeks) {
                if (toetsweken.has(w)) {
                    bodyHtml += '<td class="week-toetsweek">PW-week</td>';
                    continue;
                }
                if (vakanties.has(w)) {
                    bodyHtml += '<td class="week-vakantie">vakantie</td>';
                    continue;
                }

                const tests = vakData[String(w)] || [];
                const count = tests.length;
                colTotals[w] += count;
                const heatClass = `heat-${Math.min(count, 5)}`;

                if (count === 0) {
                    bodyHtml += `<td class="${heatClass}"></td>`;
                } else {
                    // Bovenbouw: toon alleen type (vak is al de rij)
                    const cellContent = tests.map(t =>
                        `<div class="toets-entry"><span class="type">${esc(t.type_kort)}</span></div>`
                    ).join('');
                    bodyHtml += `<td class="${heatClass}" data-vak="${esc(vak)}" data-week="${w}">${cellContent}</td>`;
                }
            }
            bodyHtml += '</tr>';
        }

        // TOTAAL row
        const rowCount = Math.max(vakken.length, 1);
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
            const heatClass = `heat-${Math.min(Math.ceil(total / rowCount), 5)}`;
            bodyHtml += `<td class="${heatClass}">${total || ''}</td>`;
        }
        bodyHtml += '</tr>';

        body.innerHTML = bodyHtml;

        // Wire up tooltips on data cells (bovenbouw uses data-vak)
        body.querySelectorAll('td[data-vak]').forEach(td => {
            td.addEventListener('mouseenter', showTooltipBovenbouw);
            td.addEventListener('mousemove', moveTooltip);
            td.addEventListener('mouseleave', hideTooltip);
        });
    }

    // ── Tooltip (onderbouw) ──
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

    // ── Tooltip (bovenbouw) ──
    function showTooltipBovenbouw(e) {
        const td = e.currentTarget;
        const vak = td.dataset.vak;
        const week = td.dataset.week;
        const lj = state.jaarlaag;
        const tests = (((DATA.bovenbouw || {})[lj] || {}).toetsen || {})[vak] || {};
        const weekTests = tests[week] || [];
        if (!weekTests.length) return;

        const weekLabel = DATA.kalender.week_labels[week] || `wk ${week}`;

        let html = `<h4>${esc(vak)} — ${weekLabel} (wk ${week})</h4>`;
        for (const t of weekTests) {
            html += `<div class="tt-entry">
                <span class="tt-type">${esc(t.type_kort)}</span>`;
            if (t.beschrijving) {
                html += `<div class="tt-desc">${esc(t.beschrijving)}</div>`;
            }
            if (t.stof) {
                html += `<div class="tt-stof">${esc(t.stof)}</div>`;
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
