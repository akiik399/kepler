import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from graphiti_core import Graphiti
from graphiti_core.search.search_config import SearchConfig

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
            results = await graphiti.search_(q, config=SearchConfig(limit=50))
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
        results = await graphiti.search_(
            "", center_node_uuid=center or None, config=SearchConfig(limit=50)
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

        results = await graphiti.search_(entity, config=SearchConfig(limit=20))
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
            "", center_node_uuid=node_id, config=SearchConfig(limit=50)
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
    return {
        "node_count": 0,
        "edge_count": 0,
        "last_update": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
async def health():
    return {"status": "ok"}
