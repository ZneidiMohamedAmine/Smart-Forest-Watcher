document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 Forest Monitoring Map System Loaded (REPAIR V1.5)");
    window.onload = function() {
        const selectedMap = document.getElementById('selected-map');
        const mapContainer = document.getElementById('mapContainer');
        const url = mapContainer ? mapContainer.getAttribute('data-url') : null;

        if (!selectedMap || !mapContainer || !url) {
            console.error("Required elements are missing from the DOM.");
            return;
        }
        
        const latitude = parseFloat(selectedMap.getAttribute('map-latitude'));
        const longitude = parseFloat(selectedMap.getAttribute('map-longitude'));

        let map;
        if (!isNaN(latitude) && !isNaN(longitude)) {
            localStorage.setItem('latitude', latitude);
            localStorage.setItem('longitude', longitude);
            map = L.map("map", { center: [latitude, longitude], zoom: 15 });
        } else {
            const storedLatitude = parseFloat(localStorage.getItem('latitude'));
            const storedLongitude = parseFloat(localStorage.getItem('longitude'));
            map = L.map("map", { center: [storedLatitude || 0, storedLongitude || 0], zoom: isNaN(storedLatitude) ? 2 : 15 });
        }

        L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {}).addTo(map);

        const projectSelect = document.getElementById('id_project');
        const modalTitle = document.getElementById('displayParcelsModalLabel');
        const modalTitle1 = document.getElementById('projectFormModalLabel');
        const modalTitle2 = document.getElementById('customDisplayParcelsModalLabel');

        function updateModalTitles(projectName, clientName) {
            const projectNameSpan = `<span style="color: black;">${projectName}</span>`;
            const clientNameSpan = `<span style="color: black;">${clientName}</span>`;
            if (modalTitle) modalTitle.innerHTML = `ADD ASSETS TO YOUR PROJECT: ${projectNameSpan}`;
            if (modalTitle1) modalTitle1.innerHTML = `Draw plots project: ${projectNameSpan} of client: ${clientNameSpan}`;
            if (modalTitle2) modalTitle2.innerHTML = `LAST ASSET ADDED OF PROJECT: ${projectNameSpan}`;
        }

        if (projectSelect) {
            projectSelect.addEventListener('change', function() {
                const projectId = projectSelect.value;
                if (!projectId) return;
                fetch(`/dashboard_super/get_project_details/${projectId}/`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.error) updateModalTitles(data.project_name, data.client_name);
                    });
                const selectedOption = projectSelect.options[projectSelect.selectedIndex];
                const lat = parseFloat(selectedOption?.getAttribute('data-latitude'));
                const lng = parseFloat(selectedOption?.getAttribute('data-longitude'));
                if (!isNaN(lat) && !isNaN(lng)) map.setView([lat, lng], 15);
                fetchParcellesForProject(projectId);
            });
        }

        let drawnItemsPolygon = new L.FeatureGroup();
        map.addLayer(drawnItemsPolygon);

        const nodeIcon = new L.Icon.Default();
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

        new L.Control.Draw({
            edit: { featureGroup: drawnItemsPolygon },
            draw: { polygon: true, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false }
        }).addTo(map);

        map.on(L.Draw.Event.CREATED, (e) => drawnItemsPolygon.addLayer(e.layer));

        // --- GLOBAL ASSET ADDITION STATE ---
        let displayMap;
        let drawnItemsMarker = new L.FeatureGroup();
        let currentMode = 'NODE';
        let allParcelleLayers = []; 

        const displayMapElement = document.getElementById('displayMap');
        if (displayMapElement) {
            displayMap = L.map("displayMap", { center: [latitude || 0, longitude || 0], zoom: 15 });
            L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {}).addTo(displayMap);
            displayMap.addLayer(drawnItemsMarker);
            new L.Control.Draw({
                edit: { featureGroup: drawnItemsMarker },
                draw: { marker: true, polygon: false, polyline: false, rectangle: false, circle: false, circlemarker: false }
            }).addTo(displayMap);

            displayMap.on(L.Draw.Event.CREATED, (e) => {
                const latlng = e.layer.getLatLng();
                const parcelle = findParcelleForPoint(latlng);
                if (parcelle) {
                    drawnItemsMarker.clearLayers(); // Only one active marker at a time
                    e.layer.setIcon(currentMode === 'CAMERA' ? cameraIcon : nodeIcon);
                    drawnItemsMarker.addLayer(e.layer);
                    updatePositionFields(latlng, parcelle.id);
                } else {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Invalid Placement',
                        text: 'The marker must be placed inside a parcel.',
                        confirmButtonColor: '#3085d6'
                    });
                }
            });
        }

        // --- HELPERS ---
        function findParcelleForPoint(latlng) {
            let foundId = null;
            drawnItemsPolygon.getLayers().forEach(p => {
                if (p.getBounds().contains(latlng)) {
                    if (p.feature && p.feature.properties && p.feature.properties.id) {
                        foundId = p.feature.properties.id;
                    }
                }
            });
            if (!foundId) {
                allParcelleLayers.forEach(p => {
                    if (p.getBounds().contains(latlng)) foundId = p.id;
                });
            }
            return foundId ? { id: foundId } : null;
        }

        function updatePositionFields(latlng, parcelleId) {
            const fields = {
                pos: document.getElementById('nodePosition'),
                lat: document.getElementById('id_latitude'),
                lng: document.getElementById('id_longitude'),
                par: document.getElementById('id_parcelle'),
                cLat: document.getElementById('cam_latitude'),
                cLng: document.getElementById('cam_longitude'),
                cPos: document.getElementById('cameraPosition'),
                cPar: document.getElementById('cam_parcelle'),
                cPrj: document.getElementById('cam_project')
            };
            const latStr = latlng.lat.toFixed(5);
            const lngStr = latlng.lng.toFixed(5);
            const pVal = `POINT(${lngStr} ${latStr})`;

            if (fields.pos) fields.pos.value = pVal;
            if (fields.lat) fields.lat.value = latStr;
            if (fields.lng) fields.lng.value = lngStr;
            if (fields.par) fields.par.value = parcelleId;
            
            if (fields.cLat) fields.cLat.value = latStr;
            if (fields.cLng) fields.cLng.value = lngStr;
            if (fields.cPos) fields.cPos.value = pVal;
            if (fields.cPar) fields.cPar.value = parcelleId;
            if (fields.cPrj) fields.cPrj.value = projectSelect?.value || '';
        }

        function fetchParcellesForProject(projectId) {
            fetch(`/dashboard_super/get_parcelles_for_project/?project_id=${projectId}`)
                .then(r => r.json()).then(data => {
                    drawnItemsPolygon.clearLayers();
                    const bounds = [];
                    data.parcelles.forEach(p => {
                        const poly = L.polygon(p.coordinates);
                        poly.feature = { properties: { id: p.id } };
                        drawnItemsPolygon.addLayer(poly);
                        bounds.push(...p.coordinates);
                    });
                    if (bounds.length) map.fitBounds(bounds);
                });
        }

        function loadParcelsOnDisplayMap(projectId) {
            if (!displayMap) return;
            drawnItemsMarker.clearLayers();
            allParcelleLayers = []; 
            displayMap.eachLayer(l => { if (l instanceof L.Polygon && !(l instanceof L.Rectangle)) displayMap.removeLayer(l); });

            fetch(`/dashboard_super/get_parcelles_with_nodes_for_project/?project_id=${projectId}`)
                .then(r => r.json()).then(data => {
                    const bounds = [];
                    data.parcelles.forEach(p => {
                        const poly = L.polygon(p.coordinates, { color: 'blue', weight: 2, fillOpacity: 0.3 }).addTo(displayMap);
                        allParcelleLayers.push({ id: p.id, getBounds: () => poly.getBounds() });
                        bounds.push(...p.coordinates);
                        p.nodes.forEach(n => {
                            const popupHTML = `
                                <div class="node-popup">
                                    <b>Node:</b> ${n.name}<br>
                                    <b>Ref:</b> ${n.ref}<br>
                                </div>
                            `;
                            L.marker([n.latitude, n.longitude]).bindPopup(popupHTML).addTo(displayMap);
                        });
                    });
                    
                    // Fetch and display Cameras
                    fetch(`/camera_management/list/?project_id=${projectId}`)
                        .then(r => r.json()).then(d => {
                            if (d.cameras) {
                                d.cameras.forEach(c => {
                                    let alertContent = '';
                                    if (c.has_alert && c.image_url) {
                                        alertContent = `
                                            <div style="margin-top: 10px; text-align: center;">
                                                <p style="font-weight: bold; color: red; margin-bottom: 5px;">🔥 Latest Alert (${c.detected_at})</p>
                                                <img src="${c.image_url}" style="width: 100%; max-width: 200px; border-radius: 5px; border: 2px solid red;" alt="Alert Image" />
                                            </div>
                                        `;
                                    }
                                    const popupHTML = `
                                        <div class="node-popup">
                                            <div class="node-label" style="background-color: ${c.has_alert ? 'red' : 'green'}; color: white; padding: 2px 6px; border-radius:3px; display:inline-block; font-weight:bold; margin-bottom:5px;">Camera</div><br>
                                            <b>Name:</b> ${c.name}<br>
                                            <b>Status:</b> ${c.is_active ? 'Active' : 'Inactive'}<br>
                                            ${alertContent}
                                        </div>
                                    `;
                                    L.marker([c.latitude, c.longitude], { icon: c.has_alert ? fireIcon : cameraIcon })
                                     .bindPopup(popupHTML).addTo(displayMap);
                                });
                            }
                        });

                    // FOCUS LOGIC: Fit to parcels or fallback to project city
                    if (bounds.length) {
                        displayMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 18 });
                    } else {
                        const selectedOption = projectSelect.options[projectSelect.selectedIndex];
                        const lat = parseFloat(selectedOption?.getAttribute('data-latitude'));
                        const lng = parseFloat(selectedOption?.getAttribute('data-longitude'));
                        if (!isNaN(lat) && !isNaN(lng)) displayMap.setView([lat, lng], 15);
                    }
                });
        }

        function resetAssetModal() {
            // Clear inputs
            ['nodeName', 'nodeReference', 'nodeSensors', 'nodeOrder', 'cameraName', 'cameraId', 'cameraApiKey'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            // Clear position fields
            ['nodePosition', 'id_latitude', 'id_longitude', 'cam_latitude', 'cam_longitude', 'cameraPosition'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            
            drawnItemsMarker.clearLayers();
            console.log("Modal form reset for next entry.");
        }

        // --- SUBMISSION HANDLERS ---
        document.getElementById('nextButtonPolygon')?.addEventListener('click', () => {
            const name = document.getElementById('id_name_polygon')?.value?.trim();
            const projectId = projectSelect?.value;

            // Validate name
            if (!name) {
                Swal.fire({ icon: 'warning', title: 'Missing Name', text: 'Please enter a name for the parcel before adding it.', confirmButtonColor: '#3085d6' });
                return;
            }

            // Validate project
            if (!projectId) {
                Swal.fire({ icon: 'warning', title: 'No Project', text: 'No project is selected.', confirmButtonColor: '#3085d6' });
                return;
            }

            const layers = drawnItemsPolygon.getLayers();
            if (!layers.length) {
                Swal.fire({ icon: 'warning', title: 'Missing Polygon', text: 'Please draw a polygon first.', confirmButtonColor: '#3085d6' });
                return;
            }
            
            // Find the unsaved polygon layer (layers that were just drawn, not loaded from db)
            const newLayers = layers.filter(layer => !layer.feature || !layer.feature.properties || !layer.feature.properties.id);
            if (!newLayers.length) {
                Swal.fire({ icon: 'warning', title: 'No New Polygon', text: 'Please draw a new polygon on the map first.', confirmButtonColor: '#3085d6' });
                return;
            }
            const coords = newLayers[newLayers.length - 1].getLatLngs()[0].map(l => [l.lat, l.lng]);
            coords.push(coords[0]); // Close the polygon ring

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (!csrfToken) {
                Swal.fire({ icon: 'error', title: 'Security Error', text: 'CSRF token not found. Please refresh the page.', confirmButtonColor: '#d33' });
                return;
            }

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrfToken.value },
                body: `name=${encodeURIComponent(name)}&coordinates=${JSON.stringify(coords)}&project=${projectId}`
            })
            .then(r => r.json())
            .then(data => {
                if (data.message) {
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: `Polygon "${name}" Added!`,
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });
                    
                    // Clear name input for next polygon
                    const nameInput = document.getElementById('id_name_polygon');
                    if (nameInput) nameInput.value = '';

                    // Reload all parcels on the map to show saved state
                    fetchParcellesForProject(projectId);
                } else if (data.error) {
                    let errMsg = 'Failed to add polygon.';
                    if (data.error.name && data.error.name[0]) {
                        errMsg = data.error.name[0].message;
                    } else if (data.error.coordinates && data.error.coordinates[0]) {
                        errMsg = data.error.coordinates[0].message;
                    }
                    Swal.fire({ icon: 'error', title: 'Could Not Save Polygon', text: errMsg, confirmButtonColor: '#d33' });
                }
            })
            .catch(err => {
                console.error('Add Polygon network/server error:', err);
                Swal.fire({ icon: 'error', title: 'Server Error', text: `An error occurred: ${err.message}. Check the server console for details.`, confirmButtonColor: '#d33' });
            });
        });

        document.getElementById('finishButtonPolygon')?.addEventListener('click', () => {
            const projectId = projectSelect?.value;
            if (!projectId) {
                Swal.fire({ icon: 'warning', title: 'No Project', text: 'No active project selected.', confirmButtonColor: '#3085d6' });
                return;
            }

            const layers = drawnItemsPolygon.getLayers();
            const unsavedLayers = layers.filter(layer => !layer.feature || !layer.feature.properties || !layer.feature.properties.id);
            if (unsavedLayers.length > 0) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Unsaved Polygon',
                    text: 'You have a drawn polygon that has not been added. Please click "Add Polygon" to save it, or delete it before finishing.',
                    confirmButtonColor: '#3085d6'
                });
                return;
            }

            // Check if there are any parcels saved in the database
            fetch(`/dashboard_super/get_parcelles_for_project/?project_id=${projectId}`)
                .then(r => r.json()).then(data => {
                    if (!data.parcelles || data.parcelles.length === 0) {
                        Swal.fire({ icon: 'warning', title: 'No Polygons', text: 'Please add at least one polygon before finishing.', confirmButtonColor: '#3085d6' });
                        return;
                    }
                    
                    // Transition to the Add Assets modal
                    bootstrap.Modal.getInstance(document.getElementById('projectMapModal'))?.hide();
                    resetAssetModal();
                    new bootstrap.Modal(document.getElementById('displayParcelsModal')).show();
                    loadParcelsOnDisplayMap(projectId);
                });
        });

        document.getElementById('nextButtonMarker')?.addEventListener('click', () => {
            const name = document.getElementById('nodeName').value;
            const ref = document.getElementById('nodeReference').value;
            const sensors = document.getElementById('nodeSensors').value;
            const order = document.getElementById('nodeOrder').value;
            const layers = drawnItemsMarker.getLayers();
            if (!layers.length) {
                Swal.fire({ icon: 'warning', title: 'Missing Marker', text: 'Please place a marker on the map.', confirmButtonColor: '#3085d6' });
                return;
            }
            
            const coordinates = layers[layers.length - 1].getLatLng();
            const parcelleId = document.getElementById('id_parcelle').value;

            if (!name || !ref || !parcelleId) {
                Swal.fire({ icon: 'warning', title: 'Incomplete Form', text: 'Please enter Name and ensure a marker is placed inside a plot.', confirmButtonColor: '#3085d6' });
                return;
            }

            const body = new URLSearchParams({
                name, reference: ref, sensors: sensors || '', node_range: order || '',
                position: `POINT(${coordinates.lng.toFixed(5)} ${coordinates.lat.toFixed(5)})`,
                latitude: coordinates.lat.toFixed(5),
                longitude: coordinates.lng.toFixed(5),
                parcelle: parcelleId
            });

            fetch('/dashboard_super/add_node/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
                body: body.toString()
            }).then(r => r.json()).then(data => {
                if (data.message) {
                    // SUCCESS - MULTI ADD
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: `Node "${name}" Added!`,
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });
                    
                    // Add permanent marker to displayMap
                    L.marker([coordinates.lat, coordinates.lng]).bindPopup(`<b>Node:</b> ${name}`).addTo(displayMap);
                    
                    // Reset for next node
                    resetAssetModal();
                } else {
                    Swal.fire({ icon: 'error', title: 'Submission Error', text: JSON.stringify(data.error), confirmButtonColor: '#d33' });
                }
            });
        });

        document.getElementById('nextButtonCamera')?.addEventListener('click', () => {
            const name = document.getElementById('cameraName').value;
            const camId = document.getElementById('cameraId').value;
            const apiKey = document.getElementById('cameraApiKey').value;
            const layers = drawnItemsMarker.getLayers();
            if (!layers.length) {
                Swal.fire({ icon: 'warning', title: 'Missing Marker', text: 'Please place a marker on the map.', confirmButtonColor: '#3085d6' });
                return;
            }
            
            const coordinates = layers[layers.length - 1].getLatLng();
            const parcelleId = document.getElementById('cam_parcelle').value;

            if (!name || !camId || !parcelleId) {
                Swal.fire({ icon: 'warning', title: 'Incomplete Form', text: 'Please enter Name/ID and ensure a marker is placed inside a plot.', confirmButtonColor: '#3085d6' });
                return;
            }

            const body = new URLSearchParams({
                name, camera_id: camId, api_key: apiKey,
                position: `POINT(${coordinates.lng.toFixed(5)} ${coordinates.lat.toFixed(5)})`,
                latitude: coordinates.lat.toFixed(5),
                longitude: coordinates.lng.toFixed(5),
                parcelle: parcelleId, project: projectSelect.value
            });

            fetch('/camera_management/add/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
                body: body.toString()
            }).then(r => r.json()).then(data => {
                if (data.message) {
                    // SUCCESS - MULTI ADD
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: `Camera "${name}" Added!`,
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });

                    // Add permanent marker to displayMap
                    L.marker([coordinates.lat, coordinates.lng], { icon: cameraIcon })
                     .bindPopup(`<b>Camera:</b> ${name}`).addTo(displayMap);

                    // Reset for next camera
                    resetAssetModal();
                } else {
                    Swal.fire({ icon: 'error', title: 'Submission Error', text: JSON.stringify(data.error), confirmButtonColor: '#d33' });
                }
            });
        });

        document.getElementById('btnFinishReview')?.addEventListener('click', () => {
            const summaryModal = document.getElementById('customDisplayParcelsModal');
            if (summaryModal && projectSelect) {
                bootstrap.Modal.getInstance(document.getElementById('displayParcelsModal'))?.hide();
                summaryModal.setAttribute('data-project-id', projectSelect.value);
                new bootstrap.Modal(summaryModal).show();
            }
        });

        // --- UI TRIGGERS ---
        document.querySelectorAll('.showAddAssetsBtn').forEach(btn => {
            btn.addEventListener('click', function() {
                const pid = this.getAttribute('data-project-id');
                if (projectSelect) {
                    projectSelect.value = pid;
                    projectSelect.dispatchEvent(new Event('change'));
                }
                resetAssetModal();
                new bootstrap.Modal(document.getElementById('displayParcelsModal')).show();
                loadParcelsOnDisplayMap(pid);
            });
        });

        document.querySelectorAll('.showProjectDetail').forEach(btn => {
            btn.addEventListener('click', function() {
                const name = this.getAttribute('data-project-name');
                const desc = this.getAttribute('data-project-desc');
                document.getElementById('detailProjectName').innerText = name;
                document.getElementById('detailProjectDesc').innerText = desc;
                new bootstrap.Modal(document.getElementById('projectDetailModal')).show();
            });
        });

        document.getElementById('btnToggleNode')?.addEventListener('click', () => {
            currentMode = 'NODE';
            document.getElementById('btnToggleNode').classList.add('active');
            document.getElementById('btnToggleCamera').classList.remove('active');
            document.getElementById('nodeForm').classList.remove('d-none');
            document.getElementById('cameraForm').classList.add('d-none');
            document.getElementById('nextButtonMarker').classList.remove('d-none');
            document.getElementById('nextButtonCamera').classList.add('d-none');
        });

        document.getElementById('btnToggleCamera')?.addEventListener('click', () => {
            currentMode = 'CAMERA';
            document.getElementById('btnToggleCamera').classList.add('active');
            document.getElementById('btnToggleNode').classList.remove('active');
            document.getElementById('cameraForm').classList.remove('d-none');
            document.getElementById('nodeForm').classList.add('d-none');
            document.getElementById('nextButtonCamera').classList.remove('d-none');
            document.getElementById('nextButtonMarker').classList.add('d-none');
        });

        // --- UNIVERSAL SIZE FIXES ---
        [ 'displayParcelsModal', 'customDisplayParcelsModal', 'projectMapModal', 'customParcelsNodesModal' ].forEach(id => {
            document.getElementById(id)?.addEventListener('shown.bs.modal', function() {
                setTimeout(() => {
                    if (id === 'displayParcelsModal') displayMap?.invalidateSize();
                    if (id === 'customDisplayParcelsModal') {
                        const pid = document.getElementById(id).getAttribute('data-project-id');
                        if (pid) loadParcelsOnCustomDisplayMap(pid);
                        else if (window.customSummaryMapInstance) window.customSummaryMapInstance.invalidateSize();
                    }
                    if (id === 'projectMapModal') map?.invalidateSize();
                    if (id === 'customParcelsNodesModal') window.customMap?.invalidateSize();
                }, 400); // Increased delay for stability during transitions
            });
        });

        let customDisplayLayerGroup = new L.LayerGroup();
        function loadParcelsOnCustomDisplayMap(projectId) {
            // Renamed to avoid ID collision with the div "customDisplayMap"
            if (!window.customSummaryMapInstance || typeof window.customSummaryMapInstance.invalidateSize !== 'function') {
                const centerLat = isNaN(latitude) ? 0 : latitude;
                const centerLng = isNaN(longitude) ? 0 : longitude;
                window.customSummaryMapInstance = L.map("customDisplayMap", { center: [centerLat, centerLng], zoom: 15 });
                L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {}).addTo(window.customSummaryMapInstance);
                customDisplayLayerGroup.addTo(window.customSummaryMapInstance);
            }
            
            customDisplayLayerGroup.clearLayers();
            window.customSummaryMapInstance.invalidateSize();
            
            fetch(`/dashboard_super/get_parcelles_with_nodes_for_project/?project_id=${projectId}`)
                .then(r => r.json()).then(data => {
                    const bounds = [];
                    data.parcelles.forEach(p => {
                        const poly = L.polygon(p.coordinates, { color: 'blue', weight: 2, fillOpacity: 0.1 });
                        customDisplayLayerGroup.addLayer(poly);
                        bounds.push(...p.coordinates);
                        p.nodes.forEach(n => {
                            const popupHTML = `
                                <div class="node-popup">
                                    <b>Node:</b> ${n.name}<br>
                                    <b>Ref:</b> ${n.ref}<br>
                                </div>
                            `;
                            const marker = L.marker([n.latitude, n.longitude]).bindPopup(popupHTML);
                            customDisplayLayerGroup.addLayer(marker);
                        });
                    });

                    fetch(`/camera_management/list/?project_id=${projectId}`)
                        .then(r => r.json()).then(d => {
                            if (d.cameras) {
                                d.cameras.forEach(c => {
                                    let alertContent = '';
                                    if (c.has_alert && c.image_url) {
                                        alertContent = `
                                            <div style="margin-top: 10px; text-align: center;">
                                                <p style="font-weight: bold; color: red; margin-bottom: 5px;">🔥 Latest Alert (${c.detected_at})</p>
                                                <img src="${c.image_url}" style="width: 100%; max-width: 200px; border-radius: 5px; border: 2px solid red;" alt="Alert Image" />
                                            </div>
                                        `;
                                    }
                                    const popupHTML = `
                                        <div class="node-popup">
                                            <div class="node-label" style="background-color: ${c.has_alert ? 'red' : 'green'}; color: white; padding: 2px 6px; border-radius:3px; display:inline-block; font-weight:bold; margin-bottom:5px;">Camera</div><br>
                                            <b>Name:</b> ${c.name}<br>
                                            <b>Status:</b> ${c.is_active ? 'Active' : 'Inactive'}<br>
                                            ${alertContent}
                                            <hr class="my-2">
                                            <button class="btn btn-sm btn-outline-danger w-100 delete-asset-btn" data-type="camera" data-id="${c.id}" data-name="${c.name}">
                                                <i class="fas fa-trash-alt me-1"></i> Delete Camera
                                            </button>
                                        </div>
                                    `;
                                    const cMarker = L.marker([c.latitude, c.longitude], { icon: c.has_alert ? fireIcon : cameraIcon })
                                                     .bindPopup(popupHTML);
                                    customDisplayLayerGroup.addLayer(cMarker);
                                });
                            }
                        });

                    if (bounds.length) window.customSummaryMapInstance.fitBounds(bounds);
                });
        }

        // --- MANAGE NODES LOGIC (Incorporated from project.html) ---
        window.loadParcelsNodesMap = function(projectId) {
            const mapElement = document.getElementById('customParcelsNodesMap');
            if (!mapElement) return;
            if (window.customMap) window.customMap.remove();
            fetch(`/dashboard_super/get_project_details/${projectId}/`)
                .then(r => r.json()).then(pData => {
                    const map = window.customMap = L.map(mapElement).setView([pData.latitude, pData.longitude], 15);
                    L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {}).addTo(map);
                    fetch(`/dashboard_super/get_parcelles_with_nodes_for_project/?project_id=${projectId}`)
                        .then(r => r.json()).then(data => {
                            const bounds = [];
                            data.parcelles.forEach(p => {
                                L.polygon(p.coordinates, { color: 'blue', weight: 2, fillOpacity: 0.5 }).addTo(map);
                                bounds.push(...p.coordinates);
                            p.nodes.forEach(n => {
                                const popupHTML = `
                                    <div class="node-popup">
                                        <b>Node:</b> ${n.name}<br>
                                        <b>Ref:</b> ${n.ref}<br>
                                    </div>
                                `;
                                L.marker([n.latitude, n.longitude]).bindPopup(popupHTML).addTo(map);
                            });
                            });
                            // Fixed URL to /camera_management/list/
                            fetch(`/camera_management/list/?project_id=${projectId}`).then(res => res.json()).then(cData => {
                                if (cData.cameras) {
                                    cData.cameras.forEach(c => {
                                        let alertContent = '';
                                        if (c.has_alert && c.image_url) {
                                            alertContent = `
                                                <div style="margin-top: 10px; text-align: center;">
                                                    <p style="font-weight: bold; color: red; margin-bottom: 5px;">🔥 Latest Alert (${c.detected_at})</p>
                                                    <img src="${c.image_url}" style="width: 100%; max-width: 200px; border-radius: 5px; border: 2px solid red;" alt="Alert Image" />
                                                </div>
                                            `;
                                        }
                                        const popupHTML = `
                                            <div class="node-popup">
                                                <div class="node-label" style="background-color: ${c.has_alert ? 'red' : 'green'}; color: white; padding: 2px 6px; border-radius:3px; display:inline-block; font-weight:bold; margin-bottom:5px;">Camera</div><br>
                                                <b>Name:</b> ${c.name}<br>
                                                <b>Status:</b> ${c.is_active ? 'Active' : 'Inactive'}<br>
                                                ${alertContent}
                                            </div>
                                        `;
                                        L.marker([c.latitude, c.longitude], { icon: c.has_alert ? fireIcon : cameraIcon })
                                         .bindPopup(popupHTML).addTo(map);
                                    });
                                }
                            });
                            if (bounds.length) map.fitBounds(bounds);
                        });
                });
        };

        document.querySelectorAll('.showCustomParcelsNodesBtn').forEach(btn => {
            btn.addEventListener('click', function() {
                const pid = this.getAttribute('data-project-id');
                const pName = this.getAttribute('data-project-name');
                const title = document.getElementById('customParcelsNodesModalLabel');
                if (title) title.innerHTML = `NODES & PLOTS: <span style="color: black;">${pName}</span>`;
                window.loadParcelsNodesMap(pid);
                new bootstrap.Modal(document.getElementById('customParcelsNodesModal')).show();
            });
        });

    };
});
