"""
Fabric Serializer - Converts parsed RDF data to Microsoft Fabric API format.

This module handles the serialization of entity types and relationship types
to the JSON format required by the Microsoft Fabric Ontology API.

Extracted from rdf_converter.py for Single Responsibility Principle.
"""

import base64
import json
import logging
from typing import Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..rdf_converter import EntityType, RelationshipType

logger = logging.getLogger(__name__)


class FabricSerializer:
    """
    Serializes parsed ontology data to Microsoft Fabric Ontology API format.
    
    Responsible for:
    - Creating the "parts" array structure
    - Base64 encoding payloads
    - Generating .platform metadata
    - Topological sorting of entities (parents before children)
    """
    
    @staticmethod
    def create_definition(
        entity_types: List['EntityType'],
        relationship_types: List['RelationshipType'],
        ontology_name: str = "ImportedOntology"
    ) -> Dict[str, Any]:
        """
        Create the complete Fabric Ontology definition.
        
        Args:
            entity_types: List of entity types to include
            relationship_types: List of relationship types to include
            ontology_name: Display name for the ontology
            
        Returns:
            Dictionary with "parts" array for Fabric API
        """
        parts = []
        
        # Add .platform file
        parts.append(FabricSerializer._create_platform_part(ontology_name))
        
        # Add definition.json (empty for Fabric)
        parts.append(FabricSerializer._create_definition_part())
        
        # Sort entity types so parents come before children (required by Fabric)
        sorted_entity_types = FabricSerializer._topological_sort_entities(entity_types)
        
        # Add entity type definitions
        for entity_type in sorted_entity_types:
            parts.append(FabricSerializer._create_entity_part(entity_type))
        
        # Add relationship type definitions
        for rel_type in relationship_types:
            parts.append(FabricSerializer._create_relationship_part(rel_type))
        
        return {"parts": parts}
    
    @staticmethod
    def _create_platform_part(ontology_name: str) -> Dict[str, str]:
        """Create the .platform metadata part."""
        platform_content = {
            "metadata": {
                "type": "Ontology",
                "displayName": ontology_name
            }
        }
        return {
            "path": ".platform",
            "payload": base64.b64encode(
                json.dumps(platform_content, indent=2).encode()
            ).decode(),
            "payloadType": "InlineBase64"
        }
    
    @staticmethod
    def _create_definition_part() -> Dict[str, str]:
        """Create the definition.json part (empty for Fabric)."""
        return {
            "path": "definition.json",
            "payload": base64.b64encode(b"{}").decode(),
            "payloadType": "InlineBase64"
        }
    
    @staticmethod
    def _create_entity_part(entity_type: 'EntityType') -> Dict[str, str]:
        """Create an entity type definition part."""
        entity_content = entity_type.to_dict()
        return {
            "path": f"EntityTypes/{entity_type.id}/definition.json",
            "payload": base64.b64encode(
                json.dumps(entity_content, indent=2).encode()
            ).decode(),
            "payloadType": "InlineBase64"
        }
    
    @staticmethod
    def _create_relationship_part(rel_type: 'RelationshipType') -> Dict[str, str]:
        """Create a relationship type definition part."""
        rel_content = rel_type.to_dict()
        return {
            "path": f"RelationshipTypes/{rel_type.id}/definition.json",
            "payload": base64.b64encode(
                json.dumps(rel_content, indent=2).encode()
            ).decode(),
            "payloadType": "InlineBase64"
        }
    
    @staticmethod
    def _topological_sort_entities(
        entity_types: List['EntityType']
    ) -> List['EntityType']:
        """
        Sort entity types so parents come before children.
        
        Microsoft Fabric requires parent entity types to be defined before
        their children when creating an ontology.
        
        Args:
            entity_types: Unsorted list of entity types
            
        Returns:
            Sorted list with parents before children
        """
        # Build adjacency map (child -> parent)
        id_to_entity = {e.id: e for e in entity_types}
        
        # Kahn's algorithm for topological sort
        in_degree: Dict[str, int] = {e.id: 0 for e in entity_types}
        children: Dict[str, List[str]] = {e.id: [] for e in entity_types}
        
        for entity in entity_types:
            if entity.baseEntityTypeId and entity.baseEntityTypeId in id_to_entity:
                in_degree[entity.id] += 1
                children[entity.baseEntityTypeId].append(entity.id)
        
        # Start with root entities (no parent)
        queue = [e.id for e in entity_types if in_degree[e.id] == 0]
        sorted_entities: List['EntityType'] = []
        visited: set = set()
        
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            sorted_entities.append(id_to_entity[current_id])
            
            for child_id in children.get(current_id, []):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)
        
        # Add any remaining entities (shouldn't happen if graph is well-formed)
        for entity in entity_types:
            if entity.id not in visited:
                logger.warning(f"Entity {entity.id} not reached in topological sort")
                sorted_entities.append(entity)
        
        return sorted_entities
    
    @staticmethod
    def encode_payload(data: Any) -> str:
        """
        Encode data as base64 JSON for Fabric API.
        
        Args:
            data: Data to encode (will be JSON serialized first)
            
        Returns:
            Base64-encoded string
        """
        json_str = json.dumps(data, indent=2)
        return base64.b64encode(json_str.encode()).decode()
    
    @staticmethod
    def decode_payload(encoded: str) -> Any:
        """
        Decode base64 JSON payload from Fabric API.
        
        Args:
            encoded: Base64-encoded string
            
        Returns:
            Decoded JSON data
        """
        json_bytes = base64.b64decode(encoded)
        return json.loads(json_bytes.decode())
