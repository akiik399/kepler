let network = null;

function getApiBase() {
  return window.location.origin;
}

async function loadGraph() {
  try {
    const resp = await fetch(`${getApiBase()}/api/graph/search?q=`);
    const data = await resp.json();
    renderGraph(data.nodes || []);
    document.getElementById("graph-stats").textContent =
      `Nodes: ${data.total || 0}`;
  } catch (err) {
    console.error("Failed to load graph:", err);
  }
}

function renderGraph(nodes) {
  const container = document.getElementById("graph-container");

  const visNodes = nodes.map((n, i) => ({
    id: n.id || i,
    label: n.name || n.title || `Node ${i}`,
    title: n.summary || n.description || "",
    group: n.type || "default",
    size: n.importance ? 20 + n.importance * 10 : 15,
  }));

  // Build a simple layout: star-shaped from first node
  const edges = [];
  for (let i = 1; i < visNodes.length; i++) {
    edges.push({ from: visNodes[0].id, to: visNodes[i].id });
  }

  const options = {
    physics: {
      solver: "forceAtlas2Based",
      stabilization: { iterations: 100 },
    },
    nodes: {
      font: { color: "#e2e8f0", size: 12 },
      borderWidth: 0,
      color: {
        background: "#0ea5e9",
        highlight: { background: "#38bdf8" },
      },
    },
    edges: {
      color: { color: "#334155", highlight: "#0ea5e9" },
      width: 1,
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
    },
    groups: {
      Technology: { color: { background: "#f59e0b" } },
      Organization: { color: { background: "#10b981" } },
      Person: { color: { background: "#8b5cf6" } },
      Paper: { color: { background: "#ef4444" } },
      Product: { color: { background: "#06b6d4" } },
      default: { color: { background: "#64748b" } },
    },
  };

  if (network) {
    network.destroy();
  }

  network = new vis.Network(container, { nodes: visNodes, edges }, options);

  network.on("click", function (params) {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      expandNode(nodeId);
    }
  });
}

async function expandNode(nodeId) {
  try {
    const resp = await fetch(
      `${getApiBase()}/api/graph/explore?center=${nodeId}&depth=2`
    );
    const data = await resp.json();
    if (data.nodes && data.nodes.length > 0) {
      renderGraph(data.nodes);
    }
  } catch (err) {
    console.error("Failed to expand node:", err);
  }
}

document.addEventListener("DOMContentLoaded", loadGraph);
