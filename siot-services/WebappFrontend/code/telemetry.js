const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const tachograph = urlParams.get('tachograph');

const body = { tachograph_id: tachograph };

// URL API
const address = 'http://${BACKEND_ADDRESS}/tachographs/telemetry';

let container = document.getElementById("telemetry_list");

// Crear tabla
let table = document.createElement("table");
let thead = document.createElement("thead");
let tr = document.createElement("tr");

let headers = ["Fecha", "Conductor", "Velocidad (Odómetro)", "Velocidad (GPS)"];

headers.forEach(headerText => {
  let th = document.createElement("th");
  th.innerText = headerText;
  tr.appendChild(th);
});

thead.appendChild(tr);
table.appendChild(thead);

let tbody = document.createElement("tbody");

// Llamada AJAX
$.getJSON(address, body, function(result) {
  result.forEach(item => {
    let tr = document.createElement("tr");

    // Campos JSON de la respuesta
    let tdFecha = document.createElement("td");
    tdFecha.innerText = item.time_stamp;
    tr.appendChild(tdFecha);

    let tdDriver = document.createElement("td");
    tdDriver.innerText = item.current_driver_id;
    tr.appendChild(tdDriver);

    let tdSpeed = document.createElement("td");
    tdSpeed.innerText = item.current_speed;
    tr.appendChild(tdSpeed);

    let tdGPSSpeed = document.createElement("td");
    tdGPSSpeed.innerText = item.gps_speed;
    tr.appendChild(tdGPSSpeed);

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
});