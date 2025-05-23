// Extrae el ID del tacógrafo desde la URL
const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const tachograph = urlParams.get('tachograph');

// Construye la URL del endpoint de la API con el ID como parámetro
const url_api = `/tachographs/telemetry?tachograph_id=${tachograph}`;

// Selecciona el contenedor donde se mostrará la tabla
let container = document.getElementById("telemetry_list");

// Crea la estructura de la tabla y define las cabeceras
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

// Solicita los datos de telemetría al backend y los agrega a la tabla
$.getJSON(url_api, function(result) {
  console.log(result)
  result.forEach(item => {
    let tr = document.createElement("tr");

    // Celdas con los valores de cada campo
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

  // Inserta la tabla completa en el contenedor de la página
  table.appendChild(tbody);
  container.appendChild(table);
});