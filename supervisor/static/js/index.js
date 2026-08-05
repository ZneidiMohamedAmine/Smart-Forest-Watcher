document.addEventListener('DOMContentLoaded', function() {
    const mapWrapper = document.getElementById('mapWrapper');
    if (!mapWrapper) {
        console.error('Map wrapper not found');
        return;
    }

    const defaultLat = 37.207400;
    const defaultLng = 10.116500;
    const defaultZoom = 6;  
    let map;

    window.onload = function() {
        const initializeMap = (lat, lng, zoom) => {
            if (map !== undefined) {
                map.remove();
            }

            map = L.map('map', {
                center: [lat, lng],
                zoom: zoom,
                zoomControl: false // We'll add it in a better position
            });
            window.map = map;

            L.control.zoom({ position: 'topright' }).addTo(window.map);

            const satelliteTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                 maxZoom: 19,
                 attribution: '&copy; Esri'
            }).addTo(window.map);

            // Add a style to the map container for dark mode filtering
            const updateMapFilter = () => {
                const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
                const mapEl = document.getElementById('map');
                if (isDark && mapEl) {
                    mapEl.style.filter = 'brightness(0.7) contrast(1.2) saturate(0.5) hue-rotate(15deg)';
                } else if (mapEl) {
                    mapEl.style.filter = 'none';
                }
            };
            updateMapFilter();
            
            // Re-run filter update when theme changes
            const observer = new MutationObserver(updateMapFilter);
            observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });

            const displayLayerGroup = new L.LayerGroup().addTo(window.map);
            const nodeMarkers = {};
            
            const cameraIcon = L.divIcon({
                html: '<div style="background-color: white; border-radius: 50%; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.5); border: 2px solid #ddd; font-size: 20px;">📷</div>',
                className: '',
                iconSize: [36, 36], iconAnchor: [18, 36], popupAnchor: [0, -36]
            });
            const fireIcon = L.divIcon({
                html: '<div style="background-color: white; border-radius: 50%; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.5); border: 2px solid red; font-size: 24px;">🔥</div>',
                className: '',
                iconSize: [40, 40], iconAnchor: [20, 40], popupAnchor: [0, -40]
            });

            function getColorFromPrediction(fwi_predit) {
                if (fwi_predit < 11.2) return 'green';
                else if (fwi_predit < 21.3) return 'yellow';
                else if (fwi_predit < 38.0) return 'orange';
                else if (fwi_predit < 50.0) return 'red';
                else return 'purple';
            }

            function getPredictionMessageFromPrediction(fwi_predit) {
                if (fwi_predit < 11.2) return 'Low risk';
                else if (fwi_predit < 21.3) return 'Moderate risk';
                else if (fwi_predit < 38.0) return 'High risk';
                else if (fwi_predit < 50.0) return 'Very high risk';
                else return 'Extreme risk';
            }

            function generatePopupContent(node, nodeData, projectName) {
                return `
                        <div class="node-popup">
                            <div class="node-label" style="background-color: ${getColorFromPrediction(nodeData.fwi_predit || 0)}; color:white; padding: 2px 6px; border-radius:3px; display:inline-block; font-weight:bold; margin-bottom:5px;">Node</div><br>
                            <b>Project:</b> ${projectName}<br>
                            <b>Name:</b> ${node.name}<br>
                            <b>ID / Ref:</b> ${node.ref || 'N/A'}<br>
                            <b>RSSI:</b> ${nodeData.rssi || 'N/A'}<br>
                            <b>FWI:</b> ${nodeData.fwi || 'N/A'}<br>
                            <b>Predicted FWI:</b> ${nodeData.fwi_predit || 'N/A'}<br>
                            <b>Prediction result:</b>
                            <span style="color: ${getColorFromPrediction(nodeData.fwi_predit || 0)}; font-weight: bold;">
                                ${getPredictionMessageFromPrediction(nodeData.fwi_predit || 0)}
                            </span><br><br>
                            <b>Temperature:</b> ${nodeData.temperature || 'N/A'} °C<br>
                            <b>Humidity:</b> ${nodeData.humidity || 'N/A'} %<br>
                            <b>Pressure:</b> ${nodeData.pressure || 'N/A'} hPa<br>
                            <b>Gas:</b> ${nodeData.gaz || 'N/A'} ppm<br>
                            <b>Wind speed:</b> ${nodeData.wind_speed ? nodeData.wind_speed.toFixed(2) : 'N/A'} km/h<br>
                        </div>
                    `;
            }

            function generateCameraPopupContent(camera, projectName) {
                let alertContent = '';
                if (camera.has_alert && camera.latest_alert_image) {
                    alertContent = `
                        <div style="margin-top: 10px; text-align: center;">
                            <p style="font-weight: bold; color: red; margin-bottom: 5px;">🔥 Latest Alert (${camera.latest_alert_time})</p>
                            <img src="${camera.latest_alert_image}" style="width: 100%; max-width: 200px; border-radius: 5px; border: 2px solid red;" alt="Alert Image" />
                        </div>
                    `;
                }

                return `
                        <div class="node-popup">
                            <div class="node-label" style="background-color: ${camera.has_alert ? 'red' : 'green'}; color: white; padding: 2px 6px; border-radius:3px; display:inline-block; font-weight:bold; margin-bottom:5px;">Camera</div><br>
                            <b>Project:</b> ${projectName}<br>
                            <b>Name:</b> ${camera.name}<br>
                            <b>Camera ID:</b> ${camera.camera_id || 'N/A'}<br>
                            <b>Status:</b> ${camera.is_active ? 'Active' : 'Inactive'}<br>
                            <b>Prediction Status:</b> 
                            <span style="color: ${camera.has_alert ? '#dc3545' : '#28a745'}; font-weight: bold;">
                                ${camera.has_alert ? '🔥 BAD (Fire Detected)' : '✅ GOOD (Safe)'}
                            </span><br>
                            <b>Alert State:</b> 
                            <span style="color: ${camera.has_alert ? 'red' : 'green'}; font-weight: bold;">
                                ${camera.has_alert ? '🔥 FIRE DETECTED' : 'Safe'}
                            </span><br>
                            ${alertContent}
                        </div>
                    `;
            }

            // Fetch and render all assets globally
            fetch('/dashboard_super/get_all_assets/')
                .then(r => r.json())
                .then(data => {
                    if (!data.projects) return;
                    const bounds = [];

                    data.projects.forEach(project => {
                        project.parcelles.forEach(p => {
                            if (p.coordinates && p.coordinates.length > 0) {
                                const poly = L.polygon(p.coordinates, { color: 'blue', weight: 2, fillOpacity: 0.1 });
                                poly.bindPopup(`<b>Project:</b> ${project.project_name}<br><b>Plot:</b> ${p.name}`);
                                displayLayerGroup.addLayer(poly);
                                bounds.push(...p.coordinates);
                            }

                            // Render Nodes
                            p.nodes.forEach(n => {
                                if (n.latitude && n.longitude) {
                                    const marker = L.marker([n.latitude, n.longitude]);
                                    const popupHTML = generatePopupContent(n, n.last_data || {}, project.project_name);
                                    marker.bindPopup(popupHTML);
                                    displayLayerGroup.addLayer(marker);
                                    
                                    if (!nodeMarkers[n.ref]) nodeMarkers[n.ref] = [];
                                    nodeMarkers[n.ref].push({ marker, nodeInfo: n, projectName: project.project_name });
                                }
                            });

                            // Render Cameras
                            p.cameras.forEach(c => {
                                if (c.latitude && c.longitude) {
                                    const cMarker = L.marker([c.latitude, c.longitude], { 
                                        icon: c.has_alert ? fireIcon : cameraIcon 
                                    });
                                    const popupHTML = generateCameraPopupContent(c, project.project_name);
                                    cMarker.bindPopup(popupHTML);
                                    displayLayerGroup.addLayer(cMarker);
                                }
                            });
                        });
                    });

                    // Fit to bounds if any elements exist
                    if (bounds.length > 0) {
                        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
                    }

                    // --- WebSocket Live Updates ---
                    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
                    
                    // 1. Keep TTN connection alive
                    const mqttSocket = new WebSocket(protocol + window.location.host + '/ws/mqtt/');
                    mqttSocket.onopen = () => console.log('MQTT WebSocket connected (keeping TTN ingest alive)');
                    
                    // 2. Receive live data updates for map
                    const dataSocket = new WebSocket(protocol + window.location.host + '/ws/data/');
                    dataSocket.onmessage = function (event) {
                        const wsData = JSON.parse(event.data);
                        if (wsData.message === 'MQTT data received') {
                            const nodeData = wsData.data;
                            
                            // Find markers for this node (case-insensitive)
                            let currentMarkers = nodeMarkers[nodeData.device_id];
                            if (!currentMarkers && nodeData.device_id) {
                                const lowerId = nodeData.device_id.toLowerCase();
                                const foundKey = Object.keys(nodeMarkers).find(k => k && k.toLowerCase() === lowerId);
                                if (foundKey) currentMarkers = nodeMarkers[foundKey];
                            }
                            
                            if (currentMarkers) {
                                currentMarkers.forEach(({ marker, nodeInfo, projectName }) => {
                                    // Update FWI values to ensure generatePopupContent uses the latest
                                    nodeData.fwi_predit = nodeData.fwi_predit || nodeInfo.last_data?.fwi_predit;
                                    nodeData.fwi = nodeData.fwi || nodeInfo.last_data?.fwi;
                                    
                                    const updatedContent = generatePopupContent(nodeInfo, nodeData, projectName);
                                    marker.setPopupContent(updatedContent);
                                });
                            }
                        }
                    };
                })
                .catch(err => console.error("Error loading assets for global map: ", err));

            map.on('moveend', function() {
                const mapState = {
                    center: map.getCenter(),
                    zoom: map.getZoom(),
                };
                localStorage.setItem('mapState', JSON.stringify(mapState));
            });
        };

        const savedState = localStorage.getItem('mapState');
        if (savedState) {
            try {
                const parsed = JSON.parse(savedState);
                if (parsed.center && parsed.center.lat && parsed.zoom) {
                    initializeMap(parsed.center.lat, parsed.center.lng, parsed.zoom);
                    return;
                }
            } catch (e) {}
        }
        initializeMap(defaultLat, defaultLng, defaultZoom);
    };
});
