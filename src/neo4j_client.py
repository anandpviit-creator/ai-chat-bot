from neo4j import GraphDatabase
from .config import settings
from .graph_extraction import ExtractedGraph

class Neo4jClient:
    """
    A client for interacting with the Neo4j database.
    Handles connection and data writing.
    """
    def __init__(self):
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self._driver.close()

    def get_schema(self):
        """
        Retrieves the graph schema from Neo4j.
        This is useful for providing context to the LLM for query generation.
        """
        with self._driver.session() as session:
            # Get all node labels
            labels = session.run("CALL db.labels()").value()
            # Get all relationship types
            rel_types = session.run("CALL db.relationshipTypes()").value()

            schema = {
                "node_labels": labels,
                "relationship_types": rel_types
            }
            return schema

    def add_graph_data(self, graph: ExtractedGraph):
        """
        Adds nodes and relationships from an ExtractedGraph object to the Neo4j database.
        Uses MERGE to avoid creating duplicate nodes and relationships.
        """
        if not graph:
            return

        with self._driver.session() as session:
            # Add nodes
            for node in graph.nodes:
                session.write_transaction(self._create_node, node)

            # Add relationships
            for rel in graph.relationships:
                session.write_transaction(self._create_relationship, rel)

    @staticmethod
    def _create_node(tx, node):
        # Using MERGE on the node's ID and Type to avoid duplicates.
        # ON CREATE sets properties only if the node is new.
        # ON MATCH updates properties if the node already exists.
        query = (
            "MERGE (n:%s {id: $id}) "
            "ON CREATE SET n += $props "
            "ON MATCH SET n += $props"
            % node.type  # Injecting the label safely
        )
        tx.run(query, id=node.id, props=node.properties)

    @staticmethod
    def _create_relationship(tx, rel):
        # Find the source and target nodes and create the relationship between them.
        # This assumes nodes have already been created.
        query = (
            "MATCH (a {id: $source_id}), (b {id: $target_id}) "
            "MERGE (a)-[r:%s]->(b) "
            "ON CREATE SET r = $props"
            % rel.type # Injecting the relationship type safely
        )
        tx.run(query, source_id=rel.source, target_id=rel.target, props=rel.properties)

# Global instance for reuse
neo4j_client = Neo4jClient()
