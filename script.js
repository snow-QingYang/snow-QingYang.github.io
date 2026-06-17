const lastUpdated = document.querySelector("#lastUpdated");

function redirectLegacyHashRoutes() {
  const target = window.location.hash.replace("#", "");
  if (target === "research" || target === "blog") {
    window.location.replace(`${target}/`);
  }
}

function renderLastUpdated() {
  if (!lastUpdated) return;
  const modified = new Date(document.lastModified);
  if (Number.isNaN(modified.getTime())) return;

  const date = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(modified);

  lastUpdated.textContent = `Last updated: ${date.replaceAll("-", "/")}`;
}

redirectLegacyHashRoutes();
renderLastUpdated();
