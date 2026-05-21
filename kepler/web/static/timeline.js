function getApiBase() {
  return window.location.origin;
}

async function loadTimeline(entity) {
  const container = document.getElementById("timeline-events");
  container.innerHTML = '<p style="color:#64748b">Loading...</p>';

  try {
    const resp = await fetch(
      `${getApiBase()}/api/graph/timeline?entity=${encodeURIComponent(entity)}`
    );
    const data = await resp.json();
    renderTimeline(data.events || []);
  } catch (err) {
    container.innerHTML =
      '<p style="color:#ef4444">Failed to load timeline.</p>';
  }
}

function renderTimeline(events) {
  const container = document.getElementById("timeline-events");
  if (events.length === 0) {
    container.innerHTML =
      '<p style="color:#64748b">No timeline data found for this entity.</p>';
    return;
  }

  events.sort((a, b) => new Date(b.date) - new Date(a.date));

  container.innerHTML = events
    .map(
      (e) => `
    <div class="timeline-event">
      <div class="date">${new Date(e.date).toLocaleDateString()}</div>
      <div class="change">${e.change_type || "Update"}: ${e.evidence || ""}</div>
    </div>
  `
    )
    .join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("timeline-entity");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && input.value.trim()) {
        loadTimeline(input.value.trim());
      }
    });
  }
});
