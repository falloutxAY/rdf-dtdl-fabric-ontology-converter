"""
Type Mapper - XSD to Microsoft Fabric type mapping.

This module handles the conversion of XSD (XML Schema Definition) datatypes
to their equivalent Microsoft Fabric Ontology types.

Extracted from RDFToFabricConverter for Single Responsibility Principle.
"""

import logging
from typing import Dict, Optional, Set, Tuple, cast
from rdflib import Graph, XSD, OWL, RDF, BNode

logger = logging.getLogger(__name__)

# Fabric type literals
FabricType = str  # One of: "String", "Boolean", "DateTime", "BigInt", "Double"

# XSD type to Fabric value type mapping
XSD_TO_FABRIC_TYPE: Dict[str, FabricType] = {
    str(XSD.string): "String",
    str(XSD.boolean): "Boolean",
    str(XSD.dateTime): "DateTime",
    str(XSD.date): "DateTime",
    str(XSD.dateTimeStamp): "DateTime",
    str(XSD.integer): "BigInt",
    str(XSD.int): "BigInt",
    str(XSD.long): "BigInt",
    str(XSD.double): "Double",
    str(XSD.float): "Double",
    str(XSD.decimal): "Double",
    str(XSD.anyURI): "String",
    # Time-only is not directly supported by Fabric; preserve as String
    str(XSD.time): "String",
}

# Type hierarchy for union resolution (most to least restrictive)
TYPE_HIERARCHY = [
    ([str(XSD.boolean)], "Boolean"),
    ([str(XSD.integer), str(XSD.int), str(XSD.long), str(XSD.short), str(XSD.byte), 
      str(XSD.nonNegativeInteger), str(XSD.positiveInteger), str(XSD.unsignedInt),
      str(XSD.unsignedLong), str(XSD.unsignedShort), str(XSD.unsignedByte)], "BigInt"),
    ([str(XSD.double), str(XSD.float), str(XSD.decimal)], "Double"),
    ([str(XSD.dateTime), str(XSD.date), str(XSD.dateTimeStamp)], "DateTime"),
    ([str(XSD.string), str(XSD.anyURI), str(XSD.normalizedString), str(XSD.token),
      str(XSD.language), str(XSD.Name), str(XSD.NCName), str(XSD.NMTOKEN)], "String"),
]


class TypeMapper:
    """
    Maps XSD datatypes to Microsoft Fabric Ontology types.
    
    Provides static methods for:
    - Simple XSD to Fabric type mapping
    - Union/intersection datatype resolution
    - Type hierarchy-based selection
    
    Example:
        >>> mapper = TypeMapper()
        >>> mapper.get_fabric_type(XSD.string)
        'String'
        >>> mapper.get_fabric_type(XSD.integer)
        'BigInt'
    """
    
    @staticmethod
    def get_fabric_type(xsd_uri: Optional[str]) -> FabricType:
        """
        Map an XSD type URI to a Fabric type.
        
        Args:
            xsd_uri: The XSD type URI string, or None
            
        Returns:
            The corresponding Fabric type string (defaults to "String")
        """
        if xsd_uri is None:
            return "String"
        return cast(FabricType, XSD_TO_FABRIC_TYPE.get(str(xsd_uri), "String"))
    
    @staticmethod
    def is_known_type(xsd_uri: str) -> bool:
        """
        Check if an XSD type is known/supported.
        
        Args:
            xsd_uri: The XSD type URI string
            
        Returns:
            True if the type is in our mapping
        """
        return str(xsd_uri) in XSD_TO_FABRIC_TYPE
    
    @classmethod
    def resolve_type_union(
        cls,
        types_found: Set[str]
    ) -> Tuple[FabricType, str]:
        """
        Resolve a set of XSD types to the most restrictive compatible Fabric type.
        
        Type preference order (most to least restrictive):
        Boolean > BigInt > Double > DateTime > String
        
        Args:
            types_found: Set of XSD type URI strings
            
        Returns:
            Tuple of (fabric_type, notes) where:
                - fabric_type: The resolved Fabric type
                - notes: Description of the resolution for logging
        """
        if not types_found:
            return "String", "union: no types found, defaulted to String"
        
        # Find the most restrictive type that covers all union members
        for xsd_types, fabric_type in TYPE_HIERARCHY:
            if any(t in types_found for t in xsd_types):
                type_str = str(types_found) if len(types_found) > 1 else next(iter(types_found))
                logger.info(f"Resolved datatype union to {fabric_type} from types: {type_str}")
                return cast(FabricType, fabric_type), f"union: selected {fabric_type} from {type_str}"
        
        # Fallback to String for unknown XSD types
        logger.warning(f"Datatype union contains unsupported XSD types: {types_found}, defaulting to String")
        return "String", f"union: unsupported types {types_found}, defaulted to String"
    
    @classmethod
    def resolve_datatype_union(
        cls,
        graph: Graph,
        union_node: BNode,
        list_resolver_func
    ) -> Tuple[FabricType, str]:
        """
        Resolve a datatype union blank node to the most restrictive compatible Fabric type.
        
        Analyzes a blank node representing a datatype union and selects
        the most restrictive type that can safely represent all union members.
        
        Args:
            graph: The RDF graph to query
            union_node: Blank node containing the datatype union
            list_resolver_func: Function to resolve RDF lists (from ClassResolver)
            
        Returns:
            Tuple of (fabric_type, notes)
        """
        types_found: Set[str] = set()
        
        # Traverse union to find all XSD types
        for union in graph.objects(union_node, OWL.unionOf):
            targets, _ = list_resolver_func(graph, union, set(), max_depth=10)
            for target in targets:
                if target in XSD_TO_FABRIC_TYPE:
                    types_found.add(target)
                elif str(target).startswith(str(XSD)):
                    # Handle other XSD types not in our mapping
                    types_found.add(target)
        
        # Also check for direct type references (non-union case)
        if not types_found:
            for rdf_type in graph.objects(union_node, RDF.type):
                type_str = str(rdf_type)
                if type_str in XSD_TO_FABRIC_TYPE:
                    types_found.add(type_str)
        
        if not types_found:
            logger.warning(f"Could not resolve any XSD types in datatype union: {union_node}")
            return "String", "union: no types found, defaulted to String"
        
        return cls.resolve_type_union(types_found)
