(() => {
    const input = document.getElementById('address-search');
    if (!input) return;
    const latitude = document.getElementById('id_dados-latitude');
    const longitude = document.getElementById('id_dados-longitude');
    const results = document.getElementById('address-results');
    const mapElement = document.getElementById('cadastro-map');
    const map = L.map(mapElement).setView([-12.97, -38.50], 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    let marker, timer, sequence = 0;
    function point(lat, lng) {
        latitude.value = Number(lat).toFixed(8);
        longitude.value = Number(lng).toFixed(8);
        if (!marker) {
            marker = L.marker([lat, lng], {draggable: true}).addTo(map);
            marker.on('dragend', () => {
                const p = marker.getLatLng();
                point(p.lat, p.lng);
            });
        } else marker.setLatLng([lat, lng]);
    }
    map.on('click', e => point(e.latlng.lat, e.latlng.lng));
    if (latitude.value && longitude.value) {
        point(latitude.value, longitude.value);
        map.setView([latitude.value, longitude.value], 16);
    }
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const current = ++sequence;
        latitude.value = longitude.value = '';
        results.replaceChildren();
        if (input.value.trim().length < 3) return;
        timer = setTimeout(async () => {
            try {
                const url = new URL('https://api.geoapify.com/v1/geocode/autocomplete');
                url.search = new URLSearchParams({text: input.value, format: 'json', limit: '5', lang: 'pt', filter: 'countrycode:br', apiKey: mapElement.dataset.geocodingKey});
                const response = await fetch(url);
                if (!response.ok) throw new Error();
                const data = await response.json();
                if (current !== sequence) return;
                results.replaceChildren();
                for (const item of data.results || []) {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'list-group-item list-group-item-action';
                    button.textContent = item.formatted;
                    button.addEventListener('click', () => {
                        sequence++;
                        input.value = item.formatted;
                        point(item.lat, item.lon);
                        map.setView([item.lat, item.lon], 17);
                        results.replaceChildren();
                    });
                    results.appendChild(button);
                }
            } catch {
                if (current === sequence) results.textContent = 'Não foi possível buscar o endereço. Preencha o endereço e marque o ponto no mapa.';
            }
        }, 500);
    });
})();
