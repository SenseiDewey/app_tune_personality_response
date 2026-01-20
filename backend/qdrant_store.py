from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, PointStruct

from backend.config import Settings


class QdrantStore:
    def _extract_points(self, response):
        if hasattr(response, "points"):
            return response.points
        if isinstance(response, tuple):
            first = response[0] if response else []
            if isinstance(first, list):
                return first
        return response

    def __init__(self, settings: Settings) -> None:
        self._client = QdrantClient(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key
        )
        self._collection = settings.qdrant_collection

    def search(
        self, query_vector: List[float], tenant_id: str, limit: int
    ):
        query_filter = Filter(
            must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        )
        # Usar query_points en lugar de search
        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return self._extract_points(response)

    def search_similar(
        self,
        query_vector: List[float],
        tenant_id: str,
        memory_type: str,
        limit: int,
    ):
        query_filter = Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(key="memory_type", match=MatchValue(value=memory_type)),
            ]
        )
        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return self._extract_points(response)

    def upsert(
        self,
        memory_id: str,
        vector: List[float],
        payload: dict,
    ) -> None:
        point = PointStruct(id=memory_id, vector=vector, payload=payload)
        self._client.upsert(collection_name=self._collection, points=[point])
