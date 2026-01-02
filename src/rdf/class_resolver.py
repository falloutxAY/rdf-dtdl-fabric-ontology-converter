"""
Class Resolver - OWL class expression resolution for RDF to Fabric conversion.

This module handles the resolution of complex OWL class expressions including:
- Union (owl:unionOf)
- Intersection (owl:intersectionOf)  
- Complement (owl:complementOf)
- Enumeration (owl:oneOf)
- RDF list traversal

Extracted from RDFToFabricConverter for Single Responsibility Principle.
"""

import logging
from typing import List, Optional, Set, Tuple, Union
from rdflib import Graph, RDF, OWL, URIRef, BNode
from rdflib.term import Node

logger = logging.getLogger(__name__)

# Type aliases
ClassNode = Union[URIRef, BNode, Node, None]
ListNode = Union[URIRef, BNode, Node, None]


class ClassResolver:
    """
    Resolves OWL class expressions to concrete class URIs.
    
    Handles complex class expressions with:
    - Cycle detection to prevent infinite loops
    - Depth limiting for deeply nested structures
    - Support for owl:unionOf, intersectionOf, complementOf, oneOf
    - RDF list traversal
    
    Example:
        >>> resolver = ClassResolver()
        >>> uris = resolver.resolve_class_targets(graph, some_bnode)
        >>> print(uris)  # ['http://example.org/Person', 'http://example.org/Organization']
    """
    
    DEFAULT_MAX_DEPTH = 10
    
    @classmethod
    def resolve_class_targets(
        cls, 
        graph: Graph, 
        node: ClassNode, 
        visited: Optional[Set[Union[URIRef, BNode]]] = None,
        max_depth: int = DEFAULT_MAX_DEPTH
    ) -> List[str]:
        """
        Resolve domain/range targets to class URIs with cycle detection.

        Supports:
        - Direct URIRef
        - Blank node with owl:unionOf pointing to RDF list of class URIs
        - Nested blank nodes (with cycle detection)
        - owl:intersectionOf (extracts first class)
        - owl:complementOf (extracts the complemented class)
        
        Args:
            graph: The RDF graph to query
            node: The node to resolve (URIRef or BNode)
            visited: Set of already-visited nodes for cycle detection
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            List of resolved class URI strings
        """
        # Initialize visited set on first call
        if visited is None:
            visited = set()
        
        targets: List[str] = []
        
        # Cycle detection - skip if we've seen this node
        if node in visited:
            logger.debug(f"Cycle detected in class resolution, skipping node: {node}")
            return targets
        
        # Depth limit check
        if max_depth <= 0:
            logger.warning(f"Maximum recursion depth reached in class resolution for node: {node}")
            return targets
        
        # Track this node as visited (only for BNodes which can cause cycles)
        if isinstance(node, BNode):
            visited = visited | {node}  # Create new set to avoid mutation
        
        if isinstance(node, URIRef):
            targets.append(str(node))
            
        elif isinstance(node, BNode):
            unresolved_count = 0
            
            # Handle owl:unionOf
            for union in graph.objects(node, OWL.unionOf):
                union_targets, unresolved = cls.resolve_rdf_list(
                    graph, union, visited, max_depth - 1
                )
                targets.extend(union_targets)
                unresolved_count += unresolved
            
            # Handle owl:intersectionOf (extract classes from intersection)
            for intersection in graph.objects(node, OWL.intersectionOf):
                intersection_targets, unresolved = cls.resolve_rdf_list(
                    graph, intersection, visited, max_depth - 1
                )
                targets.extend(intersection_targets)
                unresolved_count += unresolved
            
            # Handle owl:complementOf
            for complement in graph.objects(node, OWL.complementOf):
                complement_targets = cls.resolve_class_targets(
                    graph, complement, visited, max_depth - 1
                )
                targets.extend(complement_targets)
                if not complement_targets and complement is not None:
                    unresolved_count += 1
            
            # Handle owl:oneOf (enumeration of individuals - extract class references)
            for oneof in graph.objects(node, OWL.oneOf):
                oneof_targets, unresolved = cls.resolve_rdf_list(
                    graph, oneof, visited, max_depth - 1
                )
                targets.extend(oneof_targets)
                unresolved_count += unresolved
            
            if unresolved_count > 0:
                logger.debug(f"BNode resolution had {unresolved_count} unresolved items")
        
        return targets
    
    @classmethod
    def resolve_rdf_list(
        cls,
        graph: Graph,
        list_node: ListNode,
        visited: Optional[Set[Union[URIRef, BNode]]] = None,
        max_depth: int = DEFAULT_MAX_DEPTH
    ) -> Tuple[List[str], int]:
        """
        Resolve an RDF list to a list of URIs with cycle detection.
        
        Traverses rdf:first/rdf:rest structure to extract all list items.
        
        Args:
            graph: The RDF graph to query
            list_node: The head of the RDF list
            visited: Set of already-visited nodes for cycle detection
            max_depth: Maximum recursion depth
            
        Returns:
            Tuple of (list of URI strings, count of unresolved items)
        """
        if visited is None:
            visited = set()
        
        targets: List[str] = []
        unresolved_count = 0
        current = list_node
        iterations = 0
        max_iterations = 1000  # Safety limit for malformed lists
        
        while current is not None and current != RDF.nil:
            iterations += 1
            if iterations > max_iterations:
                logger.warning(f"RDF list exceeded maximum iterations ({max_iterations}), stopping")
                break
            
            # Cycle detection for list nodes
            if isinstance(current, BNode) and current in visited:
                logger.debug(f"Cycle detected in RDF list at node: {current}")
                break
            
            if isinstance(current, BNode):
                visited = visited | {current}
            
            # Get the first element
            first_node = graph.value(current, RDF.first)
            
            if first_node is not None:
                if isinstance(first_node, URIRef):
                    targets.append(str(first_node))
                elif isinstance(first_node, BNode):
                    # Recursively resolve nested structures
                    nested_targets = cls.resolve_class_targets(
                        graph, first_node, visited, max_depth - 1
                    )
                    if nested_targets:
                        targets.extend(nested_targets)
                    else:
                        unresolved_count += 1
                else:
                    # Literal or unknown type
                    unresolved_count += 1
            
            # Move to next element
            rest_node = graph.value(current, RDF.rest)
            
            if rest_node is None or rest_node == RDF.nil:
                current = None
            elif isinstance(rest_node, (URIRef, BNode)):
                current = rest_node
            else:
                current = None  # Unexpected type, end iteration
        
        return targets, unresolved_count
    
    @classmethod
    def get_first_class(
        cls,
        graph: Graph,
        node: ClassNode,
        max_depth: int = DEFAULT_MAX_DEPTH
    ) -> Optional[str]:
        """
        Get the first resolved class URI from a node.
        
        Convenience method for cases where only one class is expected.
        
        Args:
            graph: The RDF graph to query
            node: The node to resolve
            max_depth: Maximum recursion depth
            
        Returns:
            First resolved URI string, or None if no classes found
        """
        targets = cls.resolve_class_targets(graph, node, None, max_depth)
        return targets[0] if targets else None
