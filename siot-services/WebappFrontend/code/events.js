const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const tachograph = urlParams.get("tachograph");

const body = { tachograph_id: tachograph };
const container = document.getElementById("events_list");

// Crear la tabla
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

// Endpoint del backend
const address = "http://${BACKEND_ADDRESS}:5001/tachographs/events";

// Petición a la API 
$.getJSON(address, body, function (result) {
  result.forEach((item) => {
    const tr = document.createElement("tr");

    const tdFecha = document.createElement("td");
    tdFecha.innerText = item.time_stamp || "-";
    tr.appendChild(tdFecha);

    const tdWarning = document.createElement("td");
    tdWarning.innerText = item.warning || "-";
    tr.appendChild(tdWarning);

    const tdPosition = document.createElement("td");
    tdPosition.innerText = `(${item.latitude.toFixed(5)}, ${item.longitude.toFixed(5)})`;
    tr.appendChild(tdPosition);

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
});
