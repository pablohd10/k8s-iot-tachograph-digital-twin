let map;

// Google Maps requiere que initMap esté en window
window.initMap = initMap;

// Recarga el mapa cada 30 segundos
setInterval(initMap, 30000);

async function initMap() {
  const position = { lat: 40.33256, lng: -3.76516 }; // Centro inicial del mapa

  // Carga librerías necesarias de Google Maps
  const { Map } = await google.maps.importLibrary("maps");
  const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

  // Crea el mapa centrado en la posición indicada
  map = new Map(document.getElementById("map"), {
    center: position,
    zoom: 12,
    mapId: "e827784f378bcb64bc7551a6",
  });

  const infoWindow = new google.maps.InfoWindow();
  const url_api = "/tachographs/active";

  // Obtiene los tacógrafos activos desde el backend
  $.getJSON(url_api, function(result) {
    result.forEach(item => {
      const m_position = { lat: item.latitude, lng: item.longitude };

      // Crea marcador con símbolo "T"
      const pinTextGlyph = new PinElement({
        glyph: "T",
        glyphColor: "white"
      });

      const marker = new AdvancedMarkerElement({
        map: map,
        position: m_position,
        content: pinTextGlyph.element,
        title: item.tachograph_id,
        gmpClickable: true
      });

      // Contenido mostrado al hacer clic en el marcador
      const contentString =
        `<div id="content">
          <h3 class="firstHeading">${marker.title}</h3>
          <div id="bodyContent">
            <p><a href="./telemetry.html?tachograph=${marker.title}">Telemetría</a></p>
            <p><a href="./events.html?tachograph=${marker.title}">Eventos</a></p>
          </div>
        </div>`;

      // Muestra ventana de información al hacer clic en el marcador
      marker.addListener("click", ({ domEvent }) => {
        infoWindow.close();
        infoWindow.setContent(contentString);
        infoWindow.open(marker.map, marker);
      });
    });
  });
}
