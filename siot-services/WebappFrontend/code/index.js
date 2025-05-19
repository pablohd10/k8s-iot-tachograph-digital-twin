let map;
const server_address = "http://${BACKEND_ADDRESS}:5001/";

window.initMap = initMap;
setInterval(initMap, 60000); // Refresh del mapa cada 60 segundos

async function initMap() {
  const position = { lat: 40.33256, lng: -3.76516 };

  const { Map } = await google.maps.importLibrary("maps");
  const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

  map = new Map(document.getElementById("map"), {
    center: position,
    zoom: 12,
    mapId: "${GOOGLE_MAP_ID}",
  });

  const infoWindow = new google.maps.InfoWindow();
  const url = server_address + "tachographs/active/";

  $.getJSON(url, function(result) {
    result.forEach(item => {
      const m_position = { lat: item.Latitude, lng: item.Longitude };
      const pinTextGlyph = new PinElement({
        glyph: "T",
        glyphColor: "white"
      });

      const marker = new AdvancedMarkerElement({
        map: map,
        position: m_position,
        content: pinTextGlyph.element,
        title: item.Tachograph_id,
        gmpClickable: true
      });

      const contentString =
        `<div id="content">
          <h3 class="firstHeading">${marker.title}</h3>
          <div id="bodyContent">
            <p><a href="./telemetry.html?tachograph=${marker.title}">Telemetría</a></p>
            <p><a href="./events.html?tachograph=${marker.title}">Eventos</a></p>
          </div>
        </div>`;

      marker.addListener("click", ({ domEvent }) => {
        infoWindow.close();
        infoWindow.setContent(contentString);
        infoWindow.open(marker.map, marker);
      });
    });
  });
}
