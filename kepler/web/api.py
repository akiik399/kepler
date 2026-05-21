import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from graphiti_core import Graphiti
from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER as BASE_SEARCH

SEARCH_CONFIG = BASE_SEARCH.model_copy(update={"limit": 50})
_EMPTY_CONFIG = BASE_SEARCH.model_copy(update={"limit": 100})

logger = logging.getLogger(__name__)

router = APIRouter()
graphiti: Graphiti | None = None


def init_routes(g: Graphiti):
    global graphiti
    graphiti = g


@router.get("/graph/search")
async def search(q: str = ""):
    if graphiti is None:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")
    try:
        if q:
            results = await graphiti.search_(q, config=SEARCH_CONFIG)
        else:
            return {"nodes": [], "edges": [], "total": 0}

        nodes = [
            {
                "id": n.uuid,
                "name": n.name,
                "type": n.labels[0] if n.labels else "unknown",
                "summary": n.summary,
            }
            for n in results.nodes
        ]
        edges = [
            {
                "id": e.uuid,
                "source": e.source_node_uuid,
                "target": e.target_node_uuid,
                "name": e.name,
                "fact": e.fact,
            }
            for e in results.edges
        ]
        return {"nodes": nodes, "edges": edges, "total": len(nodes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/explore")
async def explore(center: str = "", depth: int = 2):
    if graphiti is None:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")
    try:
        query = center if center else "agent"
        results = await graphiti.search_(
            query, center_node_uuid=center or None, config=SEARCH_CONFIG
        )
        nodes = [
            {
                "id": n.uuid,
                "name": n.name,
                "type": n.labels[0] if n.labels else "unknown",
                "summary": n.summary,
            }
            for n in results.nodes
        ]
        edges = [
            {
                "id": e.uuid,
                "source": e.source_node_uuid,
                "target": e.target_node_uuid,
                "name": e.name,
                "fact": e.fact,
            }
            for e in results.edges
        ]
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/timeline")
async def get_timeline(entity: str = ""):
    if graphiti is None:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")
    try:
        if not entity:
            return {"events": []}

        results = await graphiti.search_(entity, config=SEARCH_CONFIG)
        episodes = results.episodes if results.episodes else []

        events = [
            {
                "date": e.valid_at.isoformat() if e.valid_at else e.created_at.isoformat(),
                "change_type": "discovery",
                "evidence": e.content[:200] if e.content else "",
                "source": str(e.source),
            }
            for e in episodes[:50]
        ]
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/node/{node_id}")
async def get_node(node_id: str):
    if graphiti is None:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")
    try:
        results = await graphiti.search_(
            node_id, center_node_uuid=node_id, config=SEARCH_CONFIG
        )

        node_data = None
        for n in results.nodes:
            if n.uuid == node_id:
                node_data = {
                    "id": n.uuid,
                    "name": n.name,
                    "type": n.labels[0] if n.labels else "unknown",
                    "summary": n.summary,
                    "attributes": n.attributes,
                }
                break

        if node_data is None and results.edges:
            node_data = {"id": node_id, "name": node_id, "type": "unknown", "summary": ""}

        edges = [
            {
                "id": e.uuid,
                "source": e.source_node_uuid,
                "target": e.target_node_uuid,
                "name": e.name,
                "fact": e.fact,
            }
            for e in results.edges
        ]

        return {"node": node_data or {"id": node_id, "name": node_id}, "edges": edges, "timeline": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def stats():
    if graphiti is None:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")
    try:
        # Use a broad search to get counts
        results = await graphiti.search_("agent", config=_EMPTY_CONFIG)
        return {
            "node_count": len(results.nodes) if results.nodes else 0,
            "edge_count": len(results.edges) if results.edges else 0,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "node_count": 0,
            "edge_count": 0,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/health")
async def health():
    return {"status": "ok"}
