"""Neo4j graph integration for LightRAG knowledge bases."""

import os
import networkx as nx
from pathlib import Path
from typing import Optional
from neo4j import GraphDatabase


class GraphService:
    """Manages Neo4j connection and graph operations."""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None

    def connect(self):
        """Connect to Neo4j database."""
        if not self._driver:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self):
        """Close the connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def import_graphml(self, graphml_path: str, bucket_name: str) -> dict:
        """Import a GraphML file into Neo4j with bucket label."""
        # Parse GraphML with networkx
        G = nx.read_graphml(graphml_path)

        driver = self.connect()
        stats = {"nodes": 0, "edges": 0}

        with driver.session() as session:
            # Clear existing data for this bucket
            session.run(f"MATCH (n:{bucket_name}) DETACH DELETE n")

            # Import nodes
            for node_id, attrs in G.nodes(data=True):
                entity_type = attrs.get("entity_type", "unknown")
                description = attrs.get("description", "")
                source_id = attrs.get("source_id", "")

                # Create node with bucket label and entity_type label
                session.run(
                    f"""
                    CREATE (n:{bucket_name}:{entity_type.upper()} {{
                        id: $node_id,
                        name: $node_id,
                        entity_type: $entity_type,
                        description: $description,
                        source_id: $source_id
                    }})
                    """,
                    node_id=node_id,
                    entity_type=entity_type,
                    description=description[:5000] if description else "",
                    source_id=source_id[:1000] if source_id else ""
                )
                stats["nodes"] += 1

            # Import edges
            for source, target, attrs in G.edges(data=True):
                weight = attrs.get("weight", 1.0)
                description = attrs.get("description", "")
                keywords = attrs.get("keywords", "")

                session.run(
                    f"""
                    MATCH (a:{bucket_name} {{id: $source}})
                    MATCH (b:{bucket_name} {{id: $target}})
                    CREATE (a)-[r:RELATED_TO {{
                        weight: $weight,
                        description: $description,
                        keywords: $keywords
                    }}]->(b)
                    """,
                    source=source,
                    target=target,
                    weight=float(weight) if weight else 1.0,
                    description=description[:2000] if description else "",
                    keywords=keywords[:500] if keywords else ""
                )
                stats["edges"] += 1

        return stats

    def query_entity(self, entity_name: str, bucket: str = None) -> dict:
        """Get entity info and relationships."""
        driver = self.connect()

        bucket_filter = f":{bucket}" if bucket else ""

        with driver.session() as session:
            # Get entity
            result = session.run(
                f"""
                MATCH (n{bucket_filter})
                WHERE n.name =~ $pattern
                RETURN n.name as name, n.entity_type as type, n.description as description
                LIMIT 1
                """,
                pattern=f"(?i).*{entity_name}.*"
            )
            entity = result.single()

            if not entity:
                return None

            # Get relationships
            rel_result = session.run(
                f"""
                MATCH (n{bucket_filter})-[r]-(m)
                WHERE n.name =~ $pattern
                RETURN m.name as related, m.entity_type as type, r.description as relation
                LIMIT 20
                """,
                pattern=f"(?i).*{entity_name}.*"
            )
            relationships = [dict(r) for r in rel_result]

            return {
                "name": entity["name"],
                "type": entity["type"],
                "description": entity["description"],
                "relationships": relationships
            }

    def query_path(self, entity1: str, entity2: str, bucket: str = None) -> list:
        """Find shortest path between two entities."""
        driver = self.connect()
        bucket_filter = f":{bucket}" if bucket else ""

        with driver.session() as session:
            result = session.run(
                f"""
                MATCH (a{bucket_filter}), (b{bucket_filter}),
                      path = shortestPath((a)-[*..6]-(b))
                WHERE a.name =~ $pattern1 AND b.name =~ $pattern2
                RETURN [n in nodes(path) | n.name] as path
                LIMIT 1
                """,
                pattern1=f"(?i).*{entity1}.*",
                pattern2=f"(?i).*{entity2}.*"
            )
            record = result.single()
            return record["path"] if record else []

    def query_neighbors(self, entity_name: str, depth: int = 1, bucket: str = None) -> dict:
        """Get neighborhood subgraph around an entity."""
        driver = self.connect()
        bucket_filter = f":{bucket}" if bucket else ""

        with driver.session() as session:
            result = session.run(
                f"""
                MATCH path = (n{bucket_filter})-[*1..{depth}]-(m)
                WHERE n.name =~ $pattern
                WITH collect(path) as paths
                CALL apoc.convert.toTree(paths) YIELD value
                RETURN value
                """,
                pattern=f"(?i).*{entity_name}.*"
            )
            # Fallback to simpler query if APOC not available
            result = session.run(
                f"""
                MATCH (n{bucket_filter})-[r*1..{depth}]-(m)
                WHERE n.name =~ $pattern
                RETURN DISTINCT m.name as name, m.entity_type as type
                LIMIT 50
                """,
                pattern=f"(?i).*{entity_name}.*"
            )
            return [dict(r) for r in result]

    def search_by_type(self, entity_type: str, bucket: str = None, limit: int = 50) -> list:
        """Get all entities of a specific type."""
        driver = self.connect()
        bucket_filter = f":{bucket}" if bucket else ""

        with driver.session() as session:
            result = session.run(
                f"""
                MATCH (n{bucket_filter})
                WHERE n.entity_type = $entity_type
                RETURN n.name as name, n.description as description
                ORDER BY n.name
                LIMIT $limit
                """,
                entity_type=entity_type.lower(),
                limit=limit
            )
            return [dict(r) for r in result]

    def get_graph_stats(self, bucket: str = None) -> dict:
        """Get statistics about the graph."""
        driver = self.connect()
        bucket_filter = f":{bucket}" if bucket else ""

        with driver.session() as session:
            # Node count
            node_result = session.run(f"MATCH (n{bucket_filter}) RETURN count(n) as count")
            node_count = node_result.single()["count"]

            # Edge count
            edge_result = session.run(f"MATCH (n{bucket_filter})-[r]-() RETURN count(r)/2 as count")
            edge_count = edge_result.single()["count"]

            # Entity types
            type_result = session.run(
                f"""
                MATCH (n{bucket_filter})
                RETURN n.entity_type as type, count(*) as count
                ORDER BY count DESC
                """
            )
            types = {r["type"]: r["count"] for r in type_result}

            return {
                "nodes": node_count,
                "edges": edge_count,
                "entity_types": types
            }

    def cypher_query(self, query: str, params: dict = None) -> list:
        """Execute a raw Cypher query."""
        driver = self.connect()

        with driver.session() as session:
            result = session.run(query, params or {})
            return [dict(r) for r in result]


# Convenience function to sync all buckets
async def sync_buckets_to_neo4j(buckets_dir: str, graph_service: GraphService) -> dict:
    """Sync all LightRAG buckets to Neo4j."""
    buckets_path = Path(buckets_dir)
    results = {}

    for bucket_path in buckets_path.iterdir():
        if not bucket_path.is_dir():
            continue

        graphml_file = bucket_path / "graph_chunk_entity_relation.graphml"
        if graphml_file.exists():
            bucket_name = bucket_path.name.replace("-", "_")  # Neo4j label safe
            try:
                stats = graph_service.import_graphml(str(graphml_file), bucket_name)
                results[bucket_path.name] = stats
            except Exception as e:
                results[bucket_path.name] = {"error": str(e)}

    return results
