"""
RDF TTL to Fabric Ontology Converter

This module provides functionality to parse RDF TTL files and convert them
to Microsoft Fabric Ontology API format.
"""

import json
import base64
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, URIRef, Literal
from tqdm import tqdm

logger = logging.getLogger(__name__)


# XSD type to Fabric value type mapping
XSD_TO_FABRIC_TYPE = {
    str(XSD.string): "String",
    str(XSD.boolean): "Boolean",
    str(XSD.dateTime): "DateTime",
    str(XSD.date): "DateTime",
    str(XSD.integer): "BigInt",
    str(XSD.int): "BigInt",
    str(XSD.long): "BigInt",
    str(XSD.double): "Double",
    str(XSD.float): "Double",
    str(XSD.decimal): "Double",
}


@dataclass
class EntityTypeProperty:
    """Represents a property of an entity type."""
    id: str
    name: str
    valueType: str
    redefines: Optional[str] = None
    baseTypeNamespaceType: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "valueType": self.valueType,
        }
        if self.redefines:
            result["redefines"] = self.redefines
        if self.baseTypeNamespaceType:
            result["baseTypeNamespaceType"] = self.baseTypeNamespaceType
        return result


@dataclass
class EntityType:
    """Represents an entity type in the ontology."""
    id: str
    name: str
    namespace: str = "usertypes"
    namespaceType: str = "Custom"
    visibility: str = "Visible"
    baseEntityTypeId: Optional[str] = None
    entityIdParts: List[str] = field(default_factory=list)
    displayNamePropertyId: Optional[str] = None
    properties: List[EntityTypeProperty] = field(default_factory=list)
    timeseriesProperties: List[EntityTypeProperty] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "namespace": self.namespace,
            "name": self.name,
            "namespaceType": self.namespaceType,
            "visibility": self.visibility,
            "baseEntityTypeId": self.baseEntityTypeId,
        }
        if self.entityIdParts:
            result["entityIdParts"] = self.entityIdParts
        if self.displayNamePropertyId:
            result["displayNamePropertyId"] = self.displayNamePropertyId
        if self.properties:
            result["properties"] = [p.to_dict() for p in self.properties]
        if self.timeseriesProperties:
            result["timeseriesProperties"] = [p.to_dict() for p in self.timeseriesProperties]
        return result


@dataclass
class RelationshipEnd:
    """Represents one end of a relationship."""
    entityTypeId: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"entityTypeId": self.entityTypeId}


@dataclass
class RelationshipType:
    """Represents a relationship type in the ontology."""
    id: str
    name: str
    source: RelationshipEnd
    target: RelationshipEnd
    namespace: str = "usertypes"
    namespaceType: str = "Custom"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "namespace": self.namespace,
            "name": self.name,
            "namespaceType": self.namespaceType,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
        }


class RDFToFabricConverter:
    """
    Converts RDF TTL ontologies to Microsoft Fabric Ontology format.
    """
    
    def __init__(self, id_prefix: int = 1000000000000):
        """
        Initialize the converter.
        
        Args:
            id_prefix: Base prefix for generating unique IDs
        """
        self.id_prefix = id_prefix
        self.id_counter = 0
        self.entity_types: Dict[str, EntityType] = {}
        self.relationship_types: Dict[str, RelationshipType] = {}
        self.uri_to_id: Dict[str, str] = {}
        self.property_to_domain: Dict[str, str] = {}
        
    def _generate_id(self) -> str:
        """Generate a unique ID for entities and properties."""
        self.id_counter += 1
        return str(self.id_prefix + self.id_counter)
    
    def _uri_to_name(self, uri: URIRef) -> str:
        """Extract a clean name from a URI."""
        if uri is None:
            logger.warning("Received None URI, using default name")
            return f'Unknown_{self.id_counter}'
        
        uri_str = str(uri).strip()
        
        if not uri_str:
            logger.warning("Empty URI string, using default name")
            return f'Unknown_{self.id_counter}'
        
        # Try to get the fragment
        if '#' in uri_str:
            name = uri_str.split('#')[-1]
        elif '/' in uri_str:
            name = uri_str.split('/')[-1]
        else:
            name = uri_str
        
        # Handle empty extraction
        if not name:
            logger.warning(f"Could not extract name from URI: {uri_str}")
            return f'Entity_{self.id_counter}'
        
        # Clean up the name to match Fabric requirements
        # Fabric requires identifiers to start with a letter and contain only letters, numbers, and underscores
        # Must match: ^[a-zA-Z][a-zA-Z0-9_]{0,127}$
        cleaned = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        if not cleaned:
            logger.warning(f"URI produced empty cleaned name: {uri_str}")
            return f'Entity_{self.id_counter}'
        
        if not cleaned[0].isalpha():
            cleaned = 'E_' + cleaned
        
        return cleaned[:128]
    
    def _get_xsd_type(self, range_uri: Optional[URIRef]) -> str:
        """Map XSD type to Fabric value type."""
        if range_uri is None:
            return "String"
        range_str = str(range_uri)
        return XSD_TO_FABRIC_TYPE.get(range_str, "String")
    
    def parse_ttl(self, ttl_content: str) -> Tuple[List[EntityType], List[RelationshipType]]:
        """
        Parse RDF TTL content and extract entity and relationship types.
        
        Args:
            ttl_content: The TTL content as a string
            
        Returns:
            Tuple of (entity_types, relationship_types)
        """
        logger.info("Parsing TTL content...")
        
        if not ttl_content or not ttl_content.strip():
            raise ValueError("Empty TTL content provided")
        
        # Check size before parsing
        content_size_mb = len(ttl_content.encode('utf-8')) / (1024 * 1024)
        if content_size_mb > 100:
            logger.warning(
                f"Large TTL content detected ({content_size_mb:.1f} MB). "
                "This may consume significant memory."
            )
        
        # Parse the TTL
        graph = Graph()
        try:
            graph.parse(data=ttl_content, format='turtle')
        except MemoryError:
            raise MemoryError(
                f"Insufficient memory to parse TTL content ({content_size_mb:.1f} MB). "
                "Try splitting the ontology into smaller files."
            )
        except Exception as e:
            logger.error(f"Failed to parse TTL content: {e}")
            raise ValueError(f"Invalid RDF/TTL syntax: {e}")
        
        triple_count = len(graph)
        if triple_count == 0:
            logger.warning("Parsed graph is empty - no triples found")
            raise ValueError("No RDF triples found in the provided TTL content")
        
        logger.info(f"Successfully parsed {triple_count} triples ({content_size_mb:.1f} MB)")
        
        if triple_count > 100000:
            logger.warning(
                f"Large ontology detected ({triple_count} triples). "
                "Processing may take several minutes."
            )
        
        # Reset state
        self.entity_types = {}
        self.relationship_types = {}
        self.uri_to_id = {}
        self.property_to_domain = {}
        self.id_counter = 0
        
        # Step 1: Extract all classes (entity types)
        self._extract_classes(graph)
        
        # Step 2: Extract data properties and assign to entity types
        self._extract_data_properties(graph)
        
        # Step 3: Extract object properties (relationship types)
        self._extract_object_properties(graph)
        
        # Step 4: Set entity ID parts and display name properties
        self._set_entity_identifiers()
        
        logger.info(f"Parsed {len(self.entity_types)} entity types and {len(self.relationship_types)} relationship types")
        
        return list(self.entity_types.values()), list(self.relationship_types.values())
    
    def _extract_classes(self, graph: Graph) -> None:
        """Extract OWL/RDFS classes as entity types."""
        # Find all classes
        classes = set()
        
        # OWL classes
        for s in graph.subjects(RDF.type, OWL.Class):
            if isinstance(s, URIRef):
                classes.add(s)
        
        # RDFS classes
        for s in graph.subjects(RDF.type, RDFS.Class):
            if isinstance(s, URIRef):
                classes.add(s)
        
        # Classes with subclass relationships
        for s in graph.subjects(RDFS.subClassOf, None):
            if isinstance(s, URIRef):
                classes.add(s)
        
        logger.info(f"Found {len(classes)} classes")
        
        if len(classes) == 0:
            logger.warning("No OWL/RDFS classes found in ontology")
        
        # First pass: create all entity types without parent relationships
        for class_uri in tqdm(classes, desc="Creating entity types", unit="class", disable=len(classes) < 10):
            entity_id = self._generate_id()
            name = self._uri_to_name(class_uri)
            
            entity_type = EntityType(
                id=entity_id,
                name=name,
                baseEntityTypeId=None,  # Set in second pass
            )
            
            self.entity_types[str(class_uri)] = entity_type
            self.uri_to_id[str(class_uri)] = entity_id
            logger.debug(f"Created entity type: {name} (ID: {entity_id})")
        
        # Second pass: set parent relationships with cycle detection
        def has_cycle(class_uri: URIRef, path: set) -> bool:
            """Check if following parent chain creates a cycle."""
            if class_uri in path:
                return True
            new_path = path | {class_uri}
            for parent in graph.objects(class_uri, RDFS.subClassOf):
                if isinstance(parent, URIRef) and parent in classes:
                    if has_cycle(parent, new_path):
                        return True
            return False
        
        for class_uri in classes:
            for parent in graph.objects(class_uri, RDFS.subClassOf):
                if isinstance(parent, URIRef) and str(parent) in self.uri_to_id:
                    # Check for cycles
                    if has_cycle(parent, {class_uri}):
                        logger.warning(
                            f"Circular inheritance detected for {self._uri_to_name(class_uri)}, "
                            f"skipping parent {self._uri_to_name(parent)}"
                        )
                        continue
                    
                    self.entity_types[str(class_uri)].baseEntityTypeId = self.uri_to_id[str(parent)]
                    break  # Only take first non-circular parent
    
    def _extract_data_properties(self, graph: Graph) -> None:
        """Extract data properties and add them to entity types."""
        # Find all data properties
        # Include both OWL.DatatypeProperty and rdf:Property with XSD ranges
        data_properties = set()
        owl_datatype_props = set()
        rdf_props_with_xsd_range = set()

        for s in graph.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(s, URIRef):
                owl_datatype_props.add(s)

        # Any rdf:Property whose rdfs:range is an XSD type should be treated as a data property
        for s in graph.subjects(RDF.type, RDF.Property):
            if not isinstance(s, URIRef):
                continue
            ranges = list(graph.objects(s, RDFS.range))
            if not ranges:
                continue
            range_uri = ranges[0] if isinstance(ranges[0], URIRef) else None
            if range_uri is None:
                continue
            range_str = str(range_uri)
            if range_str in XSD_TO_FABRIC_TYPE or range_str.startswith(str(XSD)):
                rdf_props_with_xsd_range.add(s)

        data_properties = owl_datatype_props | rdf_props_with_xsd_range

        logger.info(f"Found {len(data_properties)} data properties")

        for prop_uri in data_properties:
            prop_id = self._generate_id()
            name = self._uri_to_name(prop_uri)
            
            # Get domain (which entity type this property belongs to)
            domains = list(graph.objects(prop_uri, RDFS.domain))
            
            # Get range (value type)
            ranges = list(graph.objects(prop_uri, RDFS.range))
            range_uri = ranges[0] if ranges and isinstance(ranges[0], URIRef) else None
            value_type = self._get_xsd_type(range_uri)
            
            prop = EntityTypeProperty(
                id=prop_id,
                name=name,
                valueType=value_type,
            )
            
            # Add property to all domain classes
            for domain in domains:
                domain_uri = str(domain)
                if domain_uri in self.entity_types:
                    # Check if this is a timeseries property (DateTime is often used for timestamps)
                    if value_type == "DateTime" and "timestamp" in name.lower():
                        self.entity_types[domain_uri].timeseriesProperties.append(prop)
                    else:
                        self.entity_types[domain_uri].properties.append(prop)
                    self.property_to_domain[str(prop_uri)] = domain_uri
                    logger.debug(f"Added property {name} to entity type {self.entity_types[domain_uri].name}")
            
            self.uri_to_id[str(prop_uri)] = prop_id
    
    def _extract_object_properties(self, graph: Graph) -> None:
        """Extract object properties as relationship types with domain/range inference."""
        object_properties = set()
        owl_object_props = set()
        rdf_props_with_entity_range = set()

        for s in graph.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(s, URIRef):
                owl_object_props.add(s)

        # Consider rdf:Property whose range refers to a known entity type (non-XSD) as object properties
        for s in graph.subjects(RDF.type, RDF.Property):
            if not isinstance(s, URIRef):
                continue
            ranges = list(graph.objects(s, RDFS.range))
            if not ranges:
                continue
            range_candidate = ranges[0]
            if isinstance(range_candidate, URIRef):
                range_str = str(range_candidate)
                if (range_str not in XSD_TO_FABRIC_TYPE) and not range_str.startswith(str(XSD)):
                    # We'll add it; we'll verify existence later when creating the relationship
                    rdf_props_with_entity_range.add(s)

        object_properties = owl_object_props | (rdf_props_with_entity_range - set(self.property_to_domain.keys()))

        logger.info(f"Found {len(object_properties)} object properties")
        
        # Build usage map for inference
        property_usage = {}  # prop_uri -> {subjects: set, objects: set}
        for prop_uri in object_properties:
            property_usage[str(prop_uri)] = {'subjects': set(), 'objects': set()}
        
        # Scan for actual usage patterns in the graph
        for s, p, o in graph:
            if str(p) in property_usage:
                # Get types of subject and object
                for subj_type in graph.objects(s, RDF.type):
                    if str(subj_type) in self.entity_types:
                        property_usage[str(p)]['subjects'].add(str(subj_type))
                
                if isinstance(o, URIRef):
                    for obj_type in graph.objects(o, RDF.type):
                        if str(obj_type) in self.entity_types:
                            property_usage[str(p)]['objects'].add(str(obj_type))
        
        for prop_uri in tqdm(object_properties, desc="Processing relationships", unit="property", disable=len(object_properties) < 10):
            name = self._uri_to_name(prop_uri)
            
            # Get explicit domain and range
            domains = list(graph.objects(prop_uri, RDFS.domain))
            ranges = list(graph.objects(prop_uri, RDFS.range))
            
            domain_uri = None
            range_uri = None
            
            # Try explicit declarations first
            if domains:
                domain_uri = str(domains[0]) if str(domains[0]) in self.entity_types else None
            
            if ranges:
                range_uri = str(ranges[0]) if str(ranges[0]) in self.entity_types else None
            
            # Fall back to inference from usage
            if not domain_uri:
                usage = property_usage.get(str(prop_uri), {})
                if usage.get('subjects'):
                    # Use most common subject type
                    domain_uri = next(iter(usage['subjects']))
                    logger.debug(f"Inferred domain for {name}: {self._uri_to_name(URIRef(domain_uri))}")
            
            if not range_uri:
                usage = property_usage.get(str(prop_uri), {})
                if usage.get('objects'):
                    # Use most common object type
                    range_uri = next(iter(usage['objects']))
                    logger.debug(f"Inferred range for {name}: {self._uri_to_name(URIRef(range_uri))}")
            
            if not domain_uri or not range_uri:
                logger.warning(f"Skipping object property {name}: missing domain or range (no inference possible)")
                continue
            
            if domain_uri not in self.entity_types or range_uri not in self.entity_types:
                logger.warning(f"Skipping object property {name}: domain or range entity type not found")
                continue
            
            rel_id = self._generate_id()
            
            relationship = RelationshipType(
                id=rel_id,
                name=name,
                source=RelationshipEnd(entityTypeId=self.entity_types[domain_uri].id),
                target=RelationshipEnd(entityTypeId=self.entity_types[range_uri].id),
            )
            
            self.relationship_types[str(prop_uri)] = relationship
            self.uri_to_id[str(prop_uri)] = rel_id
            
            logger.debug(f"Created relationship type: {name}")
    
    def _set_entity_identifiers(self) -> None:
        """Set entity ID parts and display name properties for all entity types."""
        for entity_uri, entity_type in self.entity_types.items():
            if entity_type.properties:
                # Find an ID property or use the first property
                id_prop = None
                name_prop = None
                
                for prop in entity_type.properties:
                    prop_name_lower = prop.name.lower()
                    # Only String and BigInt are valid for entity keys
                    if 'id' in prop_name_lower and prop.valueType in ("String", "BigInt"):
                        id_prop = prop
                    if 'name' in prop_name_lower and prop.valueType == "String":
                        name_prop = prop
                
                # Find first valid key property (String or BigInt only)
                first_valid_key_prop = next(
                    (p for p in entity_type.properties if p.valueType in ("String", "BigInt")), 
                    None
                )
                
                # Only set entityIdParts if we have a valid property
                if id_prop:
                    entity_type.entityIdParts = [id_prop.id]
                    entity_type.displayNamePropertyId = (name_prop or id_prop).id
                elif first_valid_key_prop:
                    entity_type.entityIdParts = [first_valid_key_prop.id]
                    entity_type.displayNamePropertyId = first_valid_key_prop.id
                # If no valid key property, leave entityIdParts empty (Fabric will handle it)


def _topological_sort_entities(entity_types: List[EntityType]) -> List[EntityType]:
    """
    Sort entity types so that parent types come before child types.
    This ensures Fabric can resolve baseEntityTypeId references.
    
    Args:
        entity_types: List of entity types to sort
        
    Returns:
        Sorted list with parents before children
    """
    # Build a map of id -> entity
    id_to_entity = {e.id: e for e in entity_types}
    
    # Build adjacency list (child -> parent)
    # and in-degree count (how many parents reference this as base)
    children = {e.id: [] for e in entity_types}  # parent_id -> list of child_ids
    
    for entity in entity_types:
        if entity.baseEntityTypeId and entity.baseEntityTypeId in id_to_entity:
            children[entity.baseEntityTypeId].append(entity.id)
    
    # Find root entities (no parent or parent not in our set)
    roots = [e for e in entity_types if not e.baseEntityTypeId or e.baseEntityTypeId not in id_to_entity]
    
    # BFS to build sorted order
    sorted_entities = []
    visited = set()
    queue = [e.id for e in roots]
    
    while queue:
        entity_id = queue.pop(0)
        if entity_id in visited:
            continue
        visited.add(entity_id)
        sorted_entities.append(id_to_entity[entity_id])
        
        # Add children to queue
        for child_id in children[entity_id]:
            if child_id not in visited:
                queue.append(child_id)
    
    # Add any remaining entities (shouldn't happen if graph is well-formed)
    for entity in entity_types:
        if entity.id not in visited:
            sorted_entities.append(entity)
    
    return sorted_entities


def convert_to_fabric_definition(
    entity_types: List[EntityType],
    relationship_types: List[RelationshipType],
    ontology_name: str = "ImportedOntology"
) -> Dict[str, Any]:
    """
    Convert parsed entity and relationship types to Fabric Ontology definition format.
    
    Args:
        entity_types: List of entity types
        relationship_types: List of relationship types
        ontology_name: Name for the ontology
        
    Returns:
        Dictionary representing the Fabric Ontology definition
    """
    parts = []
    
    # Add .platform file
    platform_content = {
        "metadata": {
            "type": "Ontology",
            "displayName": ontology_name
        }
    }
    parts.append({
        "path": ".platform",
        "payload": base64.b64encode(json.dumps(platform_content, indent=2).encode()).decode(),
        "payloadType": "InlineBase64"
    })
    
    # Add definition.json (empty for Fabric)
    parts.append({
        "path": "definition.json",
        "payload": base64.b64encode(b"{}").decode(),
        "payloadType": "InlineBase64"
    })
    
    # Sort entity types so parents come before children (required by Fabric)
    sorted_entity_types = _topological_sort_entities(entity_types)
    
    # Add entity type definitions
    for entity_type in sorted_entity_types:
        entity_content = entity_type.to_dict()
        parts.append({
            "path": f"EntityTypes/{entity_type.id}/definition.json",
            "payload": base64.b64encode(json.dumps(entity_content, indent=2).encode()).decode(),
            "payloadType": "InlineBase64"
        })
    
    # Add relationship type definitions
    for rel_type in relationship_types:
        rel_content = rel_type.to_dict()
        parts.append({
            "path": f"RelationshipTypes/{rel_type.id}/definition.json",
            "payload": base64.b64encode(json.dumps(rel_content, indent=2).encode()).decode(),
            "payloadType": "InlineBase64"
        })
    
    return {"parts": parts}


def parse_ttl_file(file_path: str, id_prefix: int = 1000000000000) -> Tuple[Dict[str, Any], str]:
    """
    Parse a TTL file and return the Fabric Ontology definition.
    
    Args:
        file_path: Path to the TTL file
        id_prefix: Base prefix for generating unique IDs
        
    Returns:
        Tuple of (Fabric Ontology definition dict, extracted ontology name)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ttl_content = f.read()
    except FileNotFoundError:
        logger.error(f"TTL file not found: {file_path}")
        raise FileNotFoundError(f"TTL file not found: {file_path}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error reading {file_path}: {e}")
        # Try with different encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                ttl_content = f.read()
            logger.warning(f"Successfully read file with latin-1 encoding")
        except Exception as e2:
            raise ValueError(f"Unable to decode file {file_path}: {e2}")
    except PermissionError:
        logger.error(f"Permission denied reading {file_path}")
        raise PermissionError(f"Permission denied: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise IOError(f"Error reading file: {e}")
    
    return parse_ttl_content(ttl_content, id_prefix)


def parse_ttl_content(ttl_content: str, id_prefix: int = 1000000000000) -> Tuple[Dict[str, Any], str]:
    """
    Parse TTL content and return the Fabric Ontology definition.
    
    Args:
        ttl_content: TTL content as string
        id_prefix: Base prefix for generating unique IDs
        
    Returns:
        Tuple of (Fabric Ontology definition dict, extracted ontology name)
    """
    if ttl_content is None:
        raise ValueError("ttl_content cannot be None")
    
    if not isinstance(ttl_content, str):
        raise TypeError(f"ttl_content must be string, got {type(ttl_content)}")
    
    if not ttl_content.strip():
        raise ValueError("ttl_content cannot be empty")
    
    if id_prefix < 0:
        raise ValueError(f"id_prefix must be non-negative, got {id_prefix}")
    
    converter = RDFToFabricConverter(id_prefix=id_prefix)
    entity_types, relationship_types = converter.parse_ttl(ttl_content)
    
    # Try to extract ontology name from the TTL
    graph = Graph()
    graph.parse(data=ttl_content, format='turtle')
    
    ontology_name = "ImportedOntology"
    for s in graph.subjects(RDF.type, OWL.Ontology):
        # Try to get label
        labels = list(graph.objects(s, RDFS.label))
        if labels:
            label = str(labels[0])
            # Clean up for Fabric naming requirements
            ontology_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in label)
            ontology_name = ontology_name[:100]  # Max 100 chars
            if ontology_name and not ontology_name[0].isalpha():
                ontology_name = 'O_' + ontology_name
        break
    
    definition = convert_to_fabric_definition(entity_types, relationship_types, ontology_name)
    
    return definition, ontology_name
