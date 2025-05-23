// Obtener el ID del tacógrafo desde los parámetros de la URL
const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const tachograph = urlParams.get("tachograph");

// Cambiar el título visible en la interfaz
document.getElementById("page_title").innerText = `Eventos del Tacógrafo ${tachograph}`;
// Cambiar también el título de la pestaña
document.title = `Eventos del Tacógrafo ${tachograph}`;

// Contenedor donde se insertará la tabla de eventos
const container = document.getElementById("events_list");

// Crear la estructura básica de la tabla con encabezados
const table = document.createElement("table");
const thead = document.createElement("thead");
const headerRow = document.createElement("tr");

["Fecha", "Aviso", "Posición"].forEach((title) => {
  const th = document.createElement("th");
  th.innerText = title;
  headerRow.appendChild(th);
});

thead.appendChild(headerRow);
table.appendChild(thead);

const tbody = document.createElement("tbody");

// URL de la API con el parámetro del tacógrafo
const url_api = `/tachographs/events?tachograph_id=${tachograph}`;

// Obtener los eventos del tacógrafo y construir la tabla
$.getJSON(url_api, function (result) {
  console.log(result); // Para depuración

  result.forEach((item) => {
    const tr = document.createElement("tr");

    // Celda: Fecha del evento
    const tdFecha = document.createElement("td");
    tdFecha.innerText = item.time_stamp || "-";
    tr.appendChild(tdFecha);

    // Celda: Aviso o tipo de evento
    const tdWarning = document.createElement("td");
    tdWarning.innerText = item.warning || "-";
    tr.appendChild(tdWarning);

    // Celda: Posición (latitud, longitud) con formato
    const tdPosition = document.createElement("td");
    tdPosition.innerText = `(${item.latitude.toFixed(5)}, ${item.longitude.toFixed(5)})`;
    tr.appendChild(tdPosition);

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
});
