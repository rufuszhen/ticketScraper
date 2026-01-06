const routeForm = document.getElementById("route-form");
const routeIdInput = document.getElementById("route-id");
const resetRouteButton = document.getElementById("reset-route");
const routesTableBody = document.querySelector("#routes-table tbody");

const settingsForm = document.getElementById("settings-form");
const emailForm = document.getElementById("email-form");
const runCheckButton = document.getElementById("run-check");
const checkOutput = document.getElementById("check-output");

function getRoutePayload() {
  return {
    id: routeIdInput.value || null,
    origin: document.getElementById("origin").value.trim(),
    destination: document.getElementById("destination").value.trim(),
    start_date: document.getElementById("start-date").value,
    end_date: document.getElementById("end-date").value,
    cabin_class: document.getElementById("cabin-class").value.trim(),
  };
}

function resetRouteForm() {
  routeIdInput.value = "";
  routeForm.reset();
}

async function loadConfig() {
  const response = await fetch("/api/config");
  const config = await response.json();
  renderRoutes(config.routes || []);
  populateSettings(config);
}

function renderRoutes(routes) {
  routesTableBody.innerHTML = "";
  routes.forEach((route) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${route.origin}</td>
      <td>${route.destination}</td>
      <td>${route.start_date} → ${route.end_date}</td>
      <td>${route.cabin_class}</td>
      <td>
        <button data-edit="${route.id}">Edit</button>
        <button class="secondary" data-delete="${route.id}">Delete</button>
      </td>
    `;
    routesTableBody.appendChild(row);
  });
}

function populateSettings(config) {
  document.getElementById("poll-interval").value =
    config.scrape?.poll_interval_minutes ?? 5;
  document.getElementById("url-template").value =
    config.scrape?.ba_search_url_template ?? "";
  document.getElementById("availability-regex").value =
    config.scrape?.availability_regex ?? "";
  document.getElementById("availability-json-keys").value = (
    config.scrape?.availability_json_keys ?? []
  ).join(", ");
  document.getElementById("request-headers").value = JSON.stringify(
    config.scrape?.request_headers ?? {},
    null,
    2
  );
  document.getElementById("request-cookies").value = JSON.stringify(
    config.scrape?.request_cookies ?? {},
    null,
    2
  );

  document.getElementById("smtp-host").value = config.email?.smtp_host ?? "";
  document.getElementById("smtp-port").value =
    config.email?.smtp_port ?? 587;
  document.getElementById("smtp-user").value = config.email?.smtp_user ?? "";
  document.getElementById("smtp-password").value =
    config.email?.smtp_password ?? "";
  document.getElementById("smtp-from").value = config.email?.smtp_from ?? "";
  document.getElementById("smtp-to").value = config.email?.smtp_to ?? "";
  document.getElementById("smtp-tls").checked =
    config.email?.use_tls ?? true;
}

routesTableBody.addEventListener("click", async (event) => {
  const editId = event.target.getAttribute("data-edit");
  const deleteId = event.target.getAttribute("data-delete");
  if (editId) {
    const response = await fetch("/api/config");
    const config = await response.json();
    const route = config.routes.find((item) => item.id === editId);
    if (!route) return;
    routeIdInput.value = route.id;
    document.getElementById("origin").value = route.origin;
    document.getElementById("destination").value = route.destination;
    document.getElementById("start-date").value = route.start_date;
    document.getElementById("end-date").value = route.end_date;
    document.getElementById("cabin-class").value = route.cabin_class;
  }
  if (deleteId) {
    await fetch(`/api/routes/${deleteId}`, { method: "DELETE" });
    loadConfig();
  }
});

routeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = getRoutePayload();
  const isEdit = Boolean(payload.id);
  const url = isEdit ? `/api/routes/${payload.id}` : "/api/routes";
  const method = isEdit ? "PUT" : "POST";
  await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  resetRouteForm();
  loadConfig();
});

resetRouteButton.addEventListener("click", () => {
  resetRouteForm();
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    email: {
      smtp_host: document.getElementById("smtp-host").value.trim(),
      smtp_port: Number(document.getElementById("smtp-port").value),
      smtp_user: document.getElementById("smtp-user").value.trim(),
      smtp_password: document.getElementById("smtp-password").value,
      smtp_from: document.getElementById("smtp-from").value.trim(),
      smtp_to: document.getElementById("smtp-to").value.trim(),
      use_tls: document.getElementById("smtp-tls").checked,
    },
    scrape: {
      poll_interval_minutes: Number(
        document.getElementById("poll-interval").value
      ),
      ba_search_url_template: document
        .getElementById("url-template")
        .value.trim(),
      availability_regex: document
        .getElementById("availability-regex")
        .value.trim(),
      availability_json_keys: document
        .getElementById("availability-json-keys")
        .value.split(",")
        .map((entry) => entry.trim())
        .filter(Boolean),
      request_headers: JSON.parse(
        document.getElementById("request-headers").value || "{}"
      ),
      request_cookies: JSON.parse(
        document.getElementById("request-cookies").value || "{}"
      ),
    },
  };
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  loadConfig();
});

emailForm.addEventListener("submit", (event) => {
  event.preventDefault();
  settingsForm.dispatchEvent(new Event("submit"));
});

runCheckButton.addEventListener("click", async () => {
  checkOutput.textContent = "Checking...";
  const response = await fetch("/api/run-check", { method: "POST" });
  const data = await response.json();
  checkOutput.textContent = JSON.stringify(data.results, null, 2);
});

loadConfig();
