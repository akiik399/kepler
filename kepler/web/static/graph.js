let network = null;

function getApiBase() {
  return window.location.origin;
}

async function loadGraph() {
  try {
    const resp = await fetch(`${getApiBase()}/api/graph/search?q=agent`);
    const data = await resp.json();
    console.log("API response:", data);
    const allNodes = data.nodes || [];
    const allEdges = data.edges || [];
    document.getElementById("graph-stats").textContent =
      `Nodes: ${allNodes.length}  Edges: ${allEdges.length} (loading...)`;
    renderGraph(allNodes, allEdges);
    document.getElementById("graph-stats").textContent =
      `Nodes: ${allNodes.length}  Edges: ${allEdges.length}`;
  } catch (err) {
    console.error("Failed to load graph:", err);
  }
}

function renderGraph(nodes, edgesData) {
  const container = document.getElementById("graph-container");
  console.log("renderGraph called:", nodes.length, "nodes,", edgesData ? edgesData.length : 0, "edges, vis available:", typeof vis !== "undefined");
  if (!container) { console.error("graph-container not found"); return; }

  const visNodes = nodes.map((n, i) => ({
    id: n.id || i,
    label: n.name || n.title || `Node ${i}`,
    title: n.summary || n.description || "",
    group: n.type || "default",
    size: n.importance ? 20 + n.importance * 10 : 15,
  }));

  // Use real edges from API, fall back to star layout
  const visEdges = (edgesData && edgesData.length > 0)
    ? edgesData.map(e => ({ from: e.source, to: e.target, title: e.name }))
    : visNodes.slice(1).map(n => ({ from: visNodes[0].id, to: n.id }));

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

  console.log("Creating vis network with", visNodes.length, "nodes,", visEdges.length, "edges");
  network = new vis.Network(container, { nodes: visNodes, edges: visEdges }, options);
  // Force redraw after a short delay to ensure container is visible
  setTimeout(() => { network.redraw(); network.fit(); }, 100);

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
      renderGraph(data.nodes, data.edges);
    }
  } catch (err) {
    console.error("Failed to expand node:", err);
  }
}

document.addEventListener("DOMContentLoaded", loadGraph);
