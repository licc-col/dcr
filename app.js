document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const listContainer = document.getElementById('lemaList');
    const searchInput = document.getElementById('searchInput');
    const alphabetNav = document.getElementById('alphabetNav');
    const viewerContent = document.getElementById('viewerContent');
    const welcomeScreen = document.getElementById('welcomeScreen');
    
    // Toggles
    const checkDef = document.getElementById('checkDef');
    const checkSub = document.getElementById('checkSub');
    const checkSubSub = document.getElementById('checkSubSub');
    const checkEje = document.getElementById('checkEje');
    
    // Output Areas
    const outLema = document.getElementById('outLema');
    const outCat = document.getElementById('outCat');
    const outIntro = document.getElementById('outIntro');
    const outAcepciones = document.getElementById('outAcepciones');
    const outEtim = document.getElementById('outEtim');
    
    // Modal
    const modal = document.getElementById('jsonModal');
    const jsonRawPre = document.getElementById('jsonRaw');
    const btnRaw = document.getElementById('viewRawJson');
    const btnCloseModal = document.getElementById('closeModal');
    
    let fullIndex = [];
    let currentData = null;
    let currentFilter = '';
    let selectedLetter = null;
    let abbreviationsDb = {};
    let authorsDb = {};

    // 1. Initial Load
    Promise.all([
        fetch('./json/index_db.json').then(r => r.json()),
        fetch('./json/abbreviations_db.json').then(r => r.json()).catch(e => { console.warn(e); return {}; }),
        fetch('./json/authors_db.json').then(r => r.json()).catch(e => { console.warn(e); return {}; })
    ])
    .then(([indexData, abbrevData, authorData]) => {
        fullIndex = indexData;
        abbreviationsDb = abbrevData;
        authorsDb = authorData;
        
        // Add core grammatical abbreviations for beautiful and premium popovers
        const extraAbbrevs = {
            "v": "verbo",
            "v.": "verbo",
            "s. f.": "sustantivo femenino",
            "s. m.": "sustantivo masculino",
            "s.f.": "sustantivo femenino",
            "s.m.": "sustantivo masculino",
            "sf": "sustantivo femenino",
            "sm": "sustantivo masculino",
            "f.": "femenino",
            "m.": "masculino",
            "f": "femenino",
            "m": "masculino",
            "v. tr.": "verbo transitivo",
            "v. intr.": "verbo intransitivo",
            "v. refl.": "verbo reflexivo",
            "v. prnl.": "verbo pronominal",
            "prep": "preposición",
            "prep.": "preposición",
            "adj.": "adjetivo",
            "adj": "adjetivo",
            "adv.": "adverbio",
            "adv": "adverbio",
            "s.": "sustantivo",
            "s": "sustantivo",
            "conj.": "conjunción",
            "conj": "conjunción",
            "pron.": "pronombre",
            "pron": "pronombre",
            "interj.": "interjección",
            "interj": "interjección",
            "part.": "participio",
            "part": "participio"
        };
        Object.assign(abbreviationsDb, extraAbbrevs);

        document.getElementById('viewerStats').innerText = `Base de datos cargada: ${fullIndex.length} lemas procesados.`;
        createAlphabetNav();
        renderList(fullIndex);
        setupPopoverListeners();
    })
    .catch(e => {
        console.error(e);
        listContainer.innerHTML = '<div class="loading">Error al cargar la base de datos de inicio. Verifique la carpeta /json.</div>';
    });

    // 2. Alphabet Navigation
    function createAlphabetNav() {
        const alphabet = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ".split("");
        alphabet.forEach(letter => {
            const btn = document.createElement('button');
            btn.className = 'alpha-btn';
            btn.innerText = letter;
            btn.onclick = () => filterByLetter(letter, btn);
            alphabetNav.appendChild(btn);
        });
    }

    function filterByLetter(letter, btn) {
        if (selectedLetter === letter) {
            selectedLetter = null;
            btn.classList.remove('active');
            renderList(fullIndex);
        } else {
            document.querySelectorAll('.alpha-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedLetter = letter;
            searchInput.value = '';
            
            const filtered = fullIndex.filter(item => {
                const first = prepareLema(item.lema).charAt(0).toUpperCase();
                return first === letter;
            });
            renderList(filtered);
        }
    }

    function prepareLema(text) {
        return text.replace(/^[«"¿¡\[\(-]+/, '').normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }

    // 3. List Rendering
    function renderList(items) {
        listContainer.innerHTML = '';
        // Limit to 300 items for performance
        const visible = items.slice(0, 300);
        
        visible.forEach(item => {
            const el = document.createElement('div');
            el.className = 'list-item';
            el.innerHTML = item.lema;
            el.onclick = () => {
                document.querySelectorAll('.list-item').forEach(i => i.classList.remove('selected'));
                el.classList.add('selected');
                loadEntry(item.file);
            };
            listContainer.appendChild(el);
        });
        
        if (items.length === 0) {
            listContainer.innerHTML = '<div class="loading">No hay resultados.</div>';
        }
    }

    // 4. Search
    searchInput.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        selectedLetter = null;
        document.querySelectorAll('.alpha-btn').forEach(b => b.classList.remove('active'));
        
        const filtered = fullIndex.filter(i => i.lema.toLowerCase().includes(val));
        renderList(filtered);
    });

    // 5. Load & Render Entry
    function loadEntry(file) {
        fetch(`./json/${file}`)
            .then(r => r.json())
            .then(data => {
                currentData = data;
                renderEntry(data);
                welcomeScreen.classList.add('hidden');
                viewerContent.classList.remove('hidden');
                
                // Reset scroll position to top
                const mainArea = document.querySelector('.main-area');
                if (mainArea) mainArea.scrollTop = 0;
            });
    }

    function linkifyText(text, isCategory = false) {
        if (!text) return "";
        if (!abbreviationsDb || Object.keys(abbreviationsDb).length === 0) return text;
        
        // Sort keys by length descending to match longer abbreviations first
        const keys = Object.keys(abbreviationsDb).sort((a, b) => b.length - a.length);
        
        // Build regex pattern for abbreviations
        const escapedKeys = keys.map(k => {
            let escaped = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            if (isCategory) {
                // In category grammatical field, trailing dot is optional
                if (escaped.endsWith('\\.')) {
                    escaped = escaped.slice(0, -2) + '\\.?';
                }
            }
            return escaped;
        });
        
        // Unicode-aware word boundary regex (supports Spanish accented chars)
        const pattern = new RegExp(`(?<!\\p{L})(${escapedKeys.join('|')})(?!\\p{L})`, 'gui');
        
        // Split by HTML tags to only replace text nodes
        const parts = text.split(/(<[^>]+>)/g);
        
        const processedParts = parts.map((part, index) => {
            if (index % 2 === 0) {
                return part.replace(pattern, (match) => {
                    // Normalize lookup key
                    let key = match;
                    let expansion = abbreviationsDb[key] || abbreviationsDb[key.toLowerCase()];
                    if (!expansion && !key.endsWith('.')) {
                        key = match + '.';
                        expansion = abbreviationsDb[key] || abbreviationsDb[key.toLowerCase()];
                    }
                    if (expansion) {
                        return `<span class="abbrev-tag popover-trigger" data-popover-type="abbreviation" data-popover-key="${key}">${match}</span>`;
                    }
                    return match;
                });
            } else {
                return part;
            }
        });
        
        return processedParts.join("");
    }

    function renderEntry(data) {
        outLema.innerHTML = data.lema;
        
        // Render grammatical category badge as an interactive popover trigger if it exists
        if (data.categoria_gramatical && data.categoria_gramatical.trim() !== "") {
            const catLimpio = data.categoria_gramatical.trim();
            const key = catLimpio.endsWith('.') ? catLimpio : catLimpio + '.';
            const expansion = abbreviationsDb[catLimpio] || abbreviationsDb[catLimpio.toLowerCase()] || abbreviationsDb[key] || abbreviationsDb[key.toLowerCase()];
            
            outCat.classList.remove('hidden');
            if (expansion) {
                outCat.className = 'badge popover-trigger';
                outCat.setAttribute('data-popover-type', 'abbreviation');
                outCat.setAttribute('data-popover-key', key);
            } else {
                outCat.className = 'badge';
                outCat.removeAttribute('data-popover-type');
                outCat.removeAttribute('data-popover-key');
            }
            outCat.innerHTML = catLimpio;
        } else {
            outCat.innerHTML = '';
            outCat.className = 'badge hidden';
        }
        
        outIntro.innerHTML = linkifyText(data.introduccion);
        
        outAcepciones.innerHTML = '';
        data.acepciones.forEach(acep => {
            // Check if this acep has any content whatsoever to display, or has a structural ID
            const hasContent = (acep.id && acep.id.trim() !== "") ||
                                (acep.definicion && acep.definicion.trim() !== "") || 
                                (acep.ejemplos_citas && acep.ejemplos_citas.length > 0) || 
                                (acep.subacepciones && acep.subacepciones.some(sub => 
                                    (sub.definicion && sub.definicion.trim() !== "") || 
                                    (sub.ejemplos_citas && sub.ejemplos_citas.length > 0) ||
                                    (sub.subsubacepciones && sub.subsubacepciones.some(ss => 
                                        (ss.definicion && ss.definicion.trim() !== "") || 
                                        (ss.ejemplos_citas && ss.ejemplos_citas.length > 0)
                                    ))
                                ));
            
            if (!hasContent) {
                return; // Skip rendering completely empty structural acepcion entirely
            }

            const div = document.createElement('div');
            const isDummyParent = !acep.id && !acep.definicion;
            div.className = 'acepcion-item' + (isDummyParent ? ' dummy-parent' : '');
            
            let html = '';
            if (!isDummyParent) {
                // Format structural number/roman IDs to render with a uniform trailing dot in the UI
                const displayId = /^\d+$|^[IVXLCDM]+$/i.test(acep.id) ? `${acep.id}.` : acep.id;
                html += `
                    <div class="acepcion-head">
                        <span class="acepcion-num">${displayId}</span>
                        <div class="acepcion-text">${linkifyText(acep.definicion)}</div>
                    </div>
                `;
            }
            html += renderCitas(acep.ejemplos_citas);
            
            if (acep.subacepciones.length > 0) {
                let subHtml = '';
                acep.subacepciones.forEach(sub => {
                    const hasSubContent = (sub.definicion && sub.definicion.trim() !== "") || 
                                          (sub.ejemplos_citas && sub.ejemplos_citas.length > 0) || 
                                          (sub.subsubacepciones && sub.subsubacepciones.some(ss => 
                                              (ss.definicion && ss.definicion.trim() !== "") || 
                                              (ss.ejemplos_citas && ss.ejemplos_citas.length > 0)
                                          ));
                    if (!hasSubContent) return;

                    subHtml += `
                        <div class="sub-item">
                            <div class="acepcion-head">
                                <span class="acepcion-num">${sub.id_limpio}</span>
                                <div class="sub-text">${linkifyText(sub.definicion)}</div>
                            </div>
                            ${renderCitas(sub.ejemplos_citas)}
                    `;
                    
                    if (sub.subsubacepciones && sub.subsubacepciones.length > 0) {
                        let subSubHtml = '';
                        sub.subsubacepciones.forEach(ss => {
                            const hasSubSubContent = (ss.definicion && ss.definicion.trim() !== "") || 
                                                     (ss.ejemplos_citas && ss.ejemplos_citas.length > 0);
                            if (!hasSubSubContent) return;

                            subSubHtml += `
                                <div class="sub-sub-item">
                                    <div class="acepcion-head">
                                        <span class="acepcion-num">${ss.id_limpio}</span>
                                        <div class="sub-sub-text">${linkifyText(ss.definicion)}</div>
                                    </div>
                                    ${renderCitas(ss.ejemplos_citas)}
                                </div>
                            `;
                        });
                        if (subSubHtml) {
                            subHtml += `<div class="sub-sub-list">${subSubHtml}</div>`;
                        }
                    }
                    
                    subHtml += `</div>`;
                });

                if (subHtml) {
                    html += `<div class="sub-list">${subHtml}</div>`;
                }
            }
            
            div.innerHTML = html;
            outAcepciones.appendChild(div);
        });

        // Add Extra/Tail sections if present
        outEtim.innerHTML = '';
        
        const extraSections = [
            { key: 'periodo_anteclasico', label: 'Período Anteclásico', className: 'antecl-box' },
            { key: 'testimonios_latino_hispanicos', label: 'Testimonios Latino-Hispánicos', className: 'lat-hisp-box' },
            { key: 'etimologia', label: 'Etimología', className: 'etim-box' },
            { key: 'nota', label: 'Nota', className: 'nota-box' },
            { key: 'forma', label: 'Forma', className: 'forma-box' },
            { key: 'ortografia', label: 'Ortografía', className: 'ortografia-box' },
            { key: 'conjugacion', label: 'Conjugación', className: 'conjugacion-box' },
            { key: 'construccion_sintactica', label: 'Construcciones', className: 'construction-box' },
            { key: 'prosodia', label: 'Prosodia', className: 'prosodia-box' },
            { key: 'colocacion_concordancia', label: 'Colocación y Concordancia', className: 'colocacion-box' }
        ];

        extraSections.forEach(sec => {
            if (data[sec.key] && data[sec.key].trim() !== "") {
                const secDiv = document.createElement('div');
                secDiv.className = `extra-section ${sec.className}`;
                secDiv.innerHTML = `
                    <h3>${sec.label}</h3>
                    <div class="section-content">${linkifyText(data[sec.key])}</div>
                `;
                outEtim.appendChild(secDiv);
            }
        });
    }

    function renderCitas(citas) {
        if (!citas || citas.length === 0) return '';
        let html = '<div class="examples-grid">';
        citas.forEach(c => {
            let hasAuthorInfo = false;
            let authorKey = '';
            
            if (c.autor) {
                const authorTrimmed = c.autor.trim();
                if (authorsDb[authorTrimmed]) {
                    hasAuthorInfo = true;
                    authorKey = authorTrimmed;
                } else if (authorsDb[authorTrimmed.replace(/\.$/, '')]) {
                    hasAuthorInfo = true;
                    authorKey = authorTrimmed.replace(/\.$/, '');
                } else {
                    const match = Object.keys(authorsDb).find(k => k.toLowerCase() === authorTrimmed.toLowerCase() || k.toLowerCase().replace(/\.$/, '') === authorTrimmed.toLowerCase().replace(/\.$/, ''));
                    if (match) {
                        hasAuthorInfo = true;
                        authorKey = match;
                    }
                }
            }
            
            const authorSpan = hasAuthorInfo 
                ? `<span class="author popover-trigger" data-popover-type="author" data-popover-key="${authorKey}">${c.autor}</span>` 
                : `<span class="author">${c.autor || ''}</span>`;

            html += `
                <div class="example-card">
                    <span class="quote">${c.texto_cita}</span>
                    <div class="meta">
                        ${authorSpan}
                        <span class="cite">${c.referencia_obra || ''}</span>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        return html;
    }

    // 6. View Control Toggles
    const updateToggles = () => {
        viewerContent.classList.toggle('hide-def', !checkDef.checked);
        viewerContent.classList.toggle('hide-sub', !checkSub.checked);
        viewerContent.classList.toggle('hide-subsub', !checkSubSub.checked);
        viewerContent.classList.toggle('hide-eje', !checkEje.checked);
    };
    
    checkDef.onchange = updateToggles;
    checkSub.onchange = updateToggles;
    checkSubSub.onchange = updateToggles;
    checkEje.onchange = updateToggles;

    // 7. JSON Modal
    btnRaw.onclick = () => {
        jsonRawPre.innerText = JSON.stringify(currentData, null, 2);
        modal.classList.remove('hidden');
    };
    btnCloseModal.onclick = () => modal.classList.add('hidden');
    modal.onclick = (e) => { if(e.target === modal) modal.classList.add('hidden'); };

    // 8. Premium Glassmorphic Popover
    const popover = document.createElement('div');
    popover.className = 'premium-popover hidden';
    document.body.appendChild(popover);

    let hoverTimeout = null;
    let activeTrigger = null;

    function setupPopoverListeners() {
        // Event delegation on viewerContent for ultra-performance and dynamic content support
        viewerContent.addEventListener('mouseover', (e) => {
            const trigger = e.target.closest('.popover-trigger');
            if (!trigger) return;
            
            // If we came from another element within the same trigger, do nothing
            if (e.relatedTarget && e.relatedTarget.closest('.popover-trigger') === trigger) {
                return;
            }
            
            clearTimeout(hoverTimeout);
            activeTrigger = trigger;
            
            hoverTimeout = setTimeout(() => {
                showPopover(trigger);
            }, 150);
        });
        
        viewerContent.addEventListener('mouseout', (e) => {
            const trigger = e.target.closest('.popover-trigger');
            if (!trigger) return;
            
            // If we are moving to another element within the same trigger, do nothing
            if (e.relatedTarget && e.relatedTarget.closest('.popover-trigger') === trigger) {
                return;
            }
            
            clearTimeout(hoverTimeout);
            
            hoverTimeout = setTimeout(() => {
                hidePopover();
            }, 250);
        });

        popover.addEventListener('mouseenter', () => {
            clearTimeout(hoverTimeout);
        });

        popover.addEventListener('mouseleave', () => {
            hoverTimeout = setTimeout(() => {
                hidePopover();
            }, 150);
        });
        
        viewerContent.addEventListener('click', (e) => {
            const trigger = e.target.closest('.popover-trigger');
            if (!trigger) {
                hidePopover();
                return;
            }
            
            e.preventDefault();
            e.stopPropagation();
            
            clearTimeout(hoverTimeout);
            activeTrigger = trigger;
            showPopover(trigger);
        });

        document.addEventListener('click', () => {
            hidePopover();
        });
    }

    function showPopover(trigger) {
        const type = trigger.getAttribute('data-popover-type');
        const key = trigger.getAttribute('data-popover-key');
        
        let content = '';
        if (type === 'abbreviation') {
            const expansion = abbreviationsDb[key] || abbreviationsDb[key.toLowerCase()];
            if (!expansion) return;
            content = `
                <div class="popover-abbr-header">
                    <span class="abbr-icon">📖</span>
                    <span>Término Lexicográfico</span>
                </div>
                <div class="popover-abbr-body">
                    <span class="abbr-key">${key}</span> &rarr; <span class="abbr-val">${expansion}</span>
                </div>
            `;
        } else if (type === 'author') {
            const authorData = authorsDb[key];
            if (!authorData) return;
            content = authorData;
        } else {
            return;
        }
        
        popover.innerHTML = content;
        popover.style.display = 'block';
        popover.classList.remove('hidden');
        
        const rect = trigger.getBoundingClientRect();
        const popoverRect = popover.getBoundingClientRect();
        
        let top = rect.top - popoverRect.height - 10 + window.scrollY;
        let left = rect.left + (rect.width - popoverRect.width) / 2 + window.scrollX;
        
        // Position validation
        if (top < window.scrollY + 10) {
            top = rect.bottom + 10 + window.scrollY;
        }
        if (left < 10) left = 10;
        if (left + popoverRect.width > window.innerWidth - 10) {
            left = window.innerWidth - popoverRect.width - 10;
        }
        
        popover.style.top = `${top}px`;
        popover.style.left = `${left}px`;
        
        // Trigger reflow for animation
        popover.offsetHeight;
        popover.classList.add('visible');
    }

    function hidePopover() {
        popover.classList.remove('visible');
        setTimeout(() => {
            if (!popover.classList.contains('visible')) {
                popover.classList.add('hidden');
                popover.style.display = 'none';
                activeTrigger = null;
            }
        }, 150);
    }
});
