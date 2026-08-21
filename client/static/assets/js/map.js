document.addEventListener('DOMContentLoaded', function () {
  console.log("🚀 Client Forest Map System Loaded (V1.5)");
  const mapContainer = document.getElementById('mapContainer')
  const url = mapContainer ? mapContainer.getAttribute('data-url') : null

  // --- Fonctions FWI prédits avec échelle EFFIS ---
  function getColorFromPrediction(fwi_predit) {
    if (fwi_predit < 11.2)
      return 'green' // Faible
    else if (fwi_predit < 21.3)
      return 'yellow' // Modéré
    else if (fwi_predit < 38.0)
      return 'orange' // Élevé
    else if (fwi_predit < 50.0)
      return 'red' // Très élevé
    else return 'purple' // Extrême
  }

  function getPredictionMessageFromPrediction(fwi_predit) {
    const t = window.MAP_TRANSLATIONS || {};
    if (fwi_predit < 11.2) return t.low_risk || 'Low risk'
    else if (fwi_predit < 21.3) return t.moderate_risk || 'Moderate risk'
    else if (fwi_predit < 38.0) return t.high_risk || 'High risk'
    else if (fwi_predit < 50.0) return t.very_high_risk || 'Very high risk'
    else return t.extreme_risk || 'Extreme risk'
  }

  // --- Fonctions de notification ---
  function showNotification(data) {
    const notification = createNotificationElement(data)
    document.body.appendChild(notification)

    setTimeout(() => {
      notification.classList.remove('show')
      notification.addEventListener('transitionend', () =>
        notification.remove(),
      )
    }, 15000) // disparaît après 15 secondes
  }

  function createNotificationElement(data) {
    const container = document.createElement('div')
    container.className = 'notification-container show'

    const header = document.createElement('div')
    header.className = 'notification-header'

    const title = document.createElement('div')
    title.className = 'notification-title'
    title.innerHTML = `<img src="/static/assets/images/icons/danger.png" style="width:24px; height:24px; margin-right:10px;"> Fire Alert Notification!`

    const closeBtn = document.createElement('span')
    closeBtn.className = 'close'
    closeBtn.innerHTML = '&times;'
    closeBtn.onclick = function () {
      container.classList.remove('show')
      container.addEventListener('transitionend', () => container.remove())
    }

    const body = document.createElement('div')
    body.className = 'notification-body'
    const t = window.MAP_TRANSLATIONS || {};
    body.innerHTML = `
            <p>${t.node_id || 'Node ID'}: <strong>${data.device_id}</strong> ${t.detected_fire || 'detected a potential fire!'}</p>
            <p><b>${t.fwi_predicted || 'FWI prédit'}:</b> ${data.fwi_predit || 'N/A'}</p>
            <p><b>${t.prediction || 'Prediction'}:</b> 
                <span style="color:${getColorFromPrediction(data.fwi_predit)}; font-weight:bold;">
                    ${getPredictionMessageFromPrediction(data.fwi_predit)}
                </span>
            </p>
            <p><b>${t.temperature || 'Temperature'}:</b> ${data.temperature || 'N/A'} °C | <b>${t.humidity || 'Humidity'}:</b> ${data.humidity || 'N/A'} %</p>
        `

    header.appendChild(title)
    header.appendChild(closeBtn)
    container.appendChild(header)
    container.appendChild(body)

    return container
  }

  if (!mapContainer || !url) {
    console.error('Required elements are missing from the DOM.')
    return
  }

  // --- Initialisation map ---
  fetch(url)
    .then((response) => response.json())
    .then((data) => {
      let defaultLat = 0
      let defaultLng = 0

      if (data.city) {
        defaultLat = parseFloat(data.city.latitude)
        defaultLng = parseFloat(data.city.longitude)
      }

      window.customClientMap = L.map('map').setView([defaultLat, defaultLng], 15)
      const map = window.customClientMap;

      L.tileLayer(
        'http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 17,
        },
      ).addTo(map)

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

      const markers = {}
      const polygons = {}
      window.markers = markers; // Expose for locate logic
      const storedNodeData = loadNodeDataFromLocalStorage()

      // --- Création initiale des parcelles et marqueurs ---
      if (data.parcelles && data.parcelles.length > 0) {
        const bounds = []

        data.parcelles.forEach((parcelle) => {
          let maxFwiPred = 0
          parcelle.nodes.forEach((node) => {
            const nodeData = storedNodeData[node.ref] || node.last_data || {}
            const fwi_predit = nodeData.fwi_predit || 0
            if (fwi_predit > maxFwiPred) maxFwiPred = fwi_predit
          })

          const polygon = L.polygon(parcelle.coordinates, {
            color: getColorFromPrediction(maxFwiPred),
            weight: 3.5,
            opacity: 1,
            fillOpacity: 0.1,
            fillColor: getColorFromPrediction(maxFwiPred),
          }).addTo(map)

          polygons[parcelle.id] = polygon
          bounds.push(...parcelle.coordinates)

          parcelle.nodes.forEach((node) => {
            const marker = L.marker([node.latitude, node.longitude])
            const nodeData = storedNodeData[node.ref] || node.last_data || {}
            const popupContent = generatePopupContent(node, nodeData)
            marker.bindPopup(popupContent).addTo(map)

            if (!markers[node.ref]) markers[node.ref] = []
            markers[node.ref].push(marker)
          })
        })

        // --- ADDED: Creation of Camera markers ---
        if (data.cameras && data.cameras.length > 0) {
          data.cameras.forEach(camera => {
            const marker = L.marker([camera.latitude, camera.longitude], {
              icon: camera.has_alert ? fireIcon : cameraIcon
            });
            const popupContent = generateCameraPopupContent(camera);
            marker.bindPopup(popupContent).addTo(map);
            bounds.push([camera.latitude, camera.longitude]);

            // Index camera for locate logic
            if (!markers[camera.name]) markers[camera.name] = [];
            markers[camera.name].push(marker);
          });
        }

        map.fitBounds(bounds)
      }

      // --- WebSocket temps réel ---
      const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
      const socket = new WebSocket(protocol + window.location.host + '/ws/data/')

      socket.onmessage = function (event) {
        const wsData = JSON.parse(event.data)
        if (wsData.message === 'MQTT data received') {
          const nodeData = wsData.data

          // Mise à jour cache
          saveNodeDataToLocalStorage(nodeData.device_id, nodeData)

          // Mise à jour marqueurs
          // Try exact match first, then case-insensitive
          let nodeMarkers = markers[nodeData.device_id]
          if (!nodeMarkers && nodeData.device_id) {
            const lowerId = nodeData.device_id.toLowerCase();
            const foundKey = Object.keys(markers).find(k => k.toLowerCase() === lowerId);
            if (foundKey) nodeMarkers = markers[foundKey];
          }

          if (nodeMarkers) {
            nodeMarkers.forEach((marker) => {
              const updatedContent = generatePopupContent(
                { ref: nodeData.device_id, name: nodeData.device_id },
                nodeData,
              )
              marker.setPopupContent(updatedContent)
            })
          }

          // Mise à jour parcelle
          const parcelle = data.parcelles.find((p) =>
            p.nodes.some((node) => node.ref && nodeData.device_id && node.ref.toLowerCase() === nodeData.device_id.toLowerCase()),
          )

          if (parcelle) {
            let maxFwiPred = 0
            parcelle.nodes.forEach((node) => {
              const nData =
                loadNodeDataFromLocalStorage()[node.ref] || node.last_data || {}
              if ((nData.fwi_predit || 0) > maxFwiPred)
                maxFwiPred = nData.fwi_predit
            })

            const color = getColorFromPrediction(maxFwiPred)
            polygons[parcelle.id].setStyle({ color, fillColor: color })
          }

          // Afficher notification si FWI élevé
          if (nodeData.fwi_predit >= 38) {
            showNotification(nodeData)
          }
        }
      }

      socket.onopen = () => console.log('WebSocket connection established')
      socket.onclose = () => console.log('WebSocket connection closed')
      socket.onerror = (error) => console.error('WebSocket error: ', error)
    })
    .catch((error) => console.error('Error fetching parcels:', error))

  // --- LocalStorage ---
  function saveNodeDataToLocalStorage(ref, data) {
    const nodeDataCache = loadNodeDataFromLocalStorage()
    nodeDataCache[ref] = data
    localStorage.setItem('nodeDataCache', JSON.stringify(nodeDataCache))
  }

  function loadNodeDataFromLocalStorage() {
    const nodeDataCache = localStorage.getItem('nodeDataCache')
    return nodeDataCache ? JSON.parse(nodeDataCache) : {}
  }

  // --- Génération du contenu popup ---
  function generatePopupContent(node, nodeData) {
    const t = window.MAP_TRANSLATIONS || {};
    return `
            <div class="node-popup">
                <div class="node-label" style="background-color: ${getColorFromPrediction(nodeData.fwi_predit || 0)};">${t.node || 'Node'}</div>
                <span class="badge ${node.is_online ? 'bg-success' : 'bg-danger'}" style="float:right; color:white; font-size:9px; padding:2px 5px; border-radius:4px;">${node.is_online ? (t.online || 'Online') : (t.offline || 'Offline')}</span><br>
                <b>${t.name || 'Name'}:</b> ${node.name}<br>
                <b>${t.status || 'Status'}:</b> <span style="color: ${node.is_online ? 'green' : 'red'}; font-weight: bold;">${node.is_online ? (t.online || 'Online') : (t.offline || 'Offline')}</span><br>
                <b>${t.parcel_id || 'ID Parcelle'}:</b> ${node.ref}<br>
                <b>RSSI:</b> ${nodeData.rssi || 'N/A'}<br>
                // 
                <b>${t.fwi_predicted || 'FWI prédit'}:</b> ${nodeData.fwi_predit || 'N/A'}<br>
                <b>${t.prediction_result || 'Prediction result'}:</b>
                <span style="color: ${getColorFromPrediction(nodeData.fwi_predit || 0)}; font-weight: bold;">
                    ${getPredictionMessageFromPrediction(nodeData.fwi_predit || 0)}
                </span><br><br>
                <b>${t.temperature || 'Temperature'}:</b> ${nodeData.temperature || 'N/A'} °C<br>
                <b>${t.humidity || 'Humidity'}:</b> ${nodeData.humidity || 'N/A'} %<br>
                <b>${t.pressure || 'Pressure'}:</b> ${nodeData.pressure || 'N/A'} hPa<br>
                <b>${t.gas || 'Gaz'}:</b> ${nodeData.gaz || 'N/A'} ppm<br>
                <b>${t.wind_speed || 'Wind speed'}:</b> ${nodeData.wind_speed ? nodeData.wind_speed.toFixed(2) : 'N/A'} km/h<br>
            </div>
        `
  }

  function generateCameraPopupContent(camera) {
    const t = window.MAP_TRANSLATIONS || {};
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
                <div class="node-label" style="background-color: ${camera.has_alert ? 'red' : 'green'}; color: white;">${t.camera || 'Camera'}</div>
                <span class="badge ${camera.is_online ? 'bg-success' : 'bg-danger'}" style="float:right; color:white; font-size:9px; padding:2px 5px; border-radius:4px;">${camera.is_online ? (t.online || 'Online') : (t.offline || 'Offline')}</span><br>
                <b>${t.name || 'Name'}:</b> ${camera.name}<br>
                <b>${t.camera_id || 'Camera ID'}:</b> ${camera.camera_id}<br>
                <b>${t.status || 'Status'}:</b> <span style="color: ${camera.is_online ? 'green' : 'red'}; font-weight: bold;">${camera.is_online ? (t.online || 'Online') : (t.offline || 'Offline')}</span><br>
                <b>${t.prediction_status || 'Prediction Status'}:</b> 
                <span style="color: ${camera.has_alert ? '#dc3545' : '#28a745'}; font-weight: bold;">
                    ${camera.has_alert ? (t.bad_fire || '🔥 BAD (Fire Detected)') : (t.good_safe || '✅ GOOD (Safe)')}
                </span><br>
                <b>${t.alert_state || 'Alert State'}:</b> 
                <span style="color: ${camera.has_alert ? 'red' : 'green'}; font-weight: bold;">
                    ${camera.has_alert ? (t.fire_detected_label || '🔥 FIRE DETECTED') : (t.safe_label || 'Safe')}
                </span><br>
                ${alertContent}
                ${camera.has_alert && !camera.latest_alert_image ? `<br><div class="alert alert-danger p-1 text-center" style="font-size:10px;">${t.check_logs || 'Check detection logs for images.'}</div>` : ''}
            </div>
        `
  }

  // --- ADDED: Locate Asset Logic ---
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.locate-btn');
    if (btn) {
      const lat = parseFloat(btn.getAttribute('data-lat'));
      const lng = parseFloat(btn.getAttribute('data-lng'));
      const name = btn.getAttribute('data-name');
      const ref = btn.getAttribute('data-ref') || name;

      if (window.customClientMap && !isNaN(lat) && !isNaN(lng)) {
        window.customClientMap.setView([lat, lng], 17, { animate: true });

        // Find marker and open popup
        if (window.markers) {
          let targetMarkers = window.markers[ref];

          // Robustness: Fallback to case-insensitive search if not found
          if (!targetMarkers && ref) {
            const lowerRef = ref.toLowerCase();
            const foundKey = Object.keys(window.markers).find(k => k.toLowerCase() === lowerRef);
            if (foundKey) targetMarkers = window.markers[foundKey];
          }

          if (targetMarkers) {
            targetMarkers.forEach(m => m.openPopup());
          }
        }
      }
    }
  });

  // Make map instance global for the locate logic
  window.customClientMap = null;
})
