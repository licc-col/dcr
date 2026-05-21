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

    // 1. Initial Load
    fetch('./json/index_db.json')
        .then(r => r.json())
        .then(data => {
            fullIndex = data;
            document.getElementById('viewerStats').innerText = `Base de datos cargada: ${fullIndex.length} lemas procesados.`;
            createAlphabetNav();
            renderList(fullIndex);
        })
        .catch(e => {
            listContainer.innerHTML = '<div class="loading">Error al cargar _index.json. Verifique la carpeta /json.</div>';
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
            });
    }

    function renderEntry(data) {
        outLema.innerHTML = data.lema;
        outCat.innerText = data.categoria_gramatical;
        outIntro.innerHTML = data.introduccion;
        
        outAcepciones.innerHTML = '';
        data.acepciones.forEach(acep => {
            const div = document.createElement('div');
            const isDummyParent = !acep.id && !acep.definicion;
            div.className = 'acepcion-item' + (isDummyParent ? ' dummy-parent' : '');
            
            let html = '';
            if (!isDummyParent) {
                html += `
                    <div class="acepcion-head">
                        <span class="acepcion-num">${acep.id}</span>
                        <div class="acepcion-text">${acep.definicion}</div>
                    </div>
                `;
            }
            html += renderCitas(acep.ejemplos_citas);
            
            if (acep.subacepciones.length > 0) {
                html += `<div class="sub-list">`;
                acep.subacepciones.forEach(sub => {
                    html += `
                        <div class="sub-item">
                            <div class="acepcion-head">
                                <span class="acepcion-num">${sub.id_limpio}</span>
                                <div class="sub-text">${sub.definicion}</div>
                            </div>
                            ${renderCitas(sub.ejemplos_citas)}
                    `;
                    
                    if (sub.subsubacepciones && sub.subsubacepciones.length > 0) {
                        html += `<div class="sub-sub-list">`;
                        sub.subsubacepciones.forEach(ss => {
                            html += `
                                <div class="sub-sub-item">
                                    <div class="acepcion-head">
                                        <span class="acepcion-num">${ss.id_limpio}</span>
                                        <div class="sub-sub-text">${ss.definicion}</div>
                                    </div>
                                    ${renderCitas(ss.ejemplos_citas)}
                                </div>
                            `;
                        });
                        html += `</div>`;
                    }
                    
                    html += `</div>`;
                });
                html += `</div>`;
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
                    <div class="section-content">${data[sec.key]}</div>
                `;
                outEtim.appendChild(secDiv);
            }
        });
    }

    function renderCitas(citas) {
        if (!citas || citas.length === 0) return '';
        let html = '<div class="examples-grid">';
        citas.forEach(c => {
            html += `
                <div class="example-card">
                    <span class="quote">${c.texto_cita}</span>
                    <div class="meta">
                        <span class="author">${c.author || ''}</span>
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
});
