"""Decision dependency manager service for Phase D3."""

import logging
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
from datetime import datetime

import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.portfolio import (
    DecisionDependency,
    DependencyGraph,
    DecisionNode,
    GraphMetrics,
)
from src.models.session import AlignmentSession

logger = logging.getLogger(__name__)


class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected."""

    pass


class DecisionDependencyManager:
    """Manage dependencies between decisions."""

    def __init__(self, db: AsyncSession):
        """
        Initialize dependency manager.

        Args:
            db: Database session
        """
        self.db = db

    async def add_dependency(
        self,
        source_session_id: UUID,
        target_session_id: UUID,
        dependency_type: str,
        description: Optional[str],
        created_by: str,
    ) -> DecisionDependency:
        """
        Add a dependency between two decisions.

        Args:
            source_session_id: Source session (depends on target)
            target_session_id: Target session (dependency)
            dependency_type: Type of dependency
            description: Optional description
            created_by: User who created dependency

        Returns:
            Created dependency

        Raises:
            CircularDependencyError: If dependency creates a cycle
        """
        try:
            # Check if this would create a circular dependency
            graph = await self._build_dependency_graph()
            if self._would_create_cycle(
                graph, source_session_id, target_session_id
            ):
                raise CircularDependencyError(
                    f"Adding dependency from {source_session_id} to {target_session_id} would create a cycle"
                )

            # Create dependency
            dependency = DecisionDependency(
                dependency_id=uuid4(),
                source_session_id=source_session_id,
                target_session_id=target_session_id,
                dependency_type=dependency_type,
                description=description,
                created_by=created_by,
                created_at=datetime.utcnow(),
                resolved_at=None,
            )

            # TODO: Store in database when dependency table is created
            # For now, store in-memory or cache

            logger.info(
                "dependency_added",
                extra={
                    "dependency_id": str(dependency.dependency_id),
                    "source_session_id": str(source_session_id),
                    "target_session_id": str(target_session_id),
                    "dependency_type": dependency_type,
                },
            )

            return dependency

        except CircularDependencyError:
            raise
        except Exception as e:
            logger.error(
                "failed_to_add_dependency",
                extra={
                    "source_session_id": str(source_session_id),
                    "target_session_id": str(target_session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def remove_dependency(self, dependency_id: UUID) -> None:
        """
        Remove a dependency.

        Args:
            dependency_id: Dependency ID to remove
        """
        try:
            # TODO: Delete from database when dependency table exists

            logger.info(
                "dependency_removed",
                extra={"dependency_id": str(dependency_id)},
            )

        except Exception as e:
            logger.error(
                "failed_to_remove_dependency",
                extra={
                    "dependency_id": str(dependency_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def resolve_dependency(self, dependency_id: UUID) -> None:
        """
        Mark a dependency as resolved.

        Args:
            dependency_id: Dependency ID to resolve
        """
        try:
            # TODO: Update in database when dependency table exists

            logger.info(
                "dependency_resolved",
                extra={"dependency_id": str(dependency_id)},
            )

        except Exception as e:
            logger.error(
                "failed_to_resolve_dependency",
                extra={
                    "dependency_id": str(dependency_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_dependencies_for_session(
        self, session_id: UUID
    ) -> List[DecisionDependency]:
        """
        Get all dependencies for a session (both incoming and outgoing).

        Args:
            session_id: Session ID

        Returns:
            List of dependencies
        """
        try:
            # TODO: Query from database when dependency table exists
            # For now, return empty list
            return []

        except Exception as e:
            logger.error(
                "failed_to_get_dependencies",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    async def build_dependency_graph(
        self, organization_id: UUID, include_resolved: bool = False
    ) -> DependencyGraph:
        """
        Build dependency graph for organization.

        Args:
            organization_id: Organization ID
            include_resolved: Include resolved dependencies

        Returns:
            Dependency graph with nodes and metrics
        """
        try:
            # Build NetworkX graph
            nx_graph = await self._build_dependency_graph(
                organization_id, include_resolved
            )

            # Convert to decision nodes
            nodes = await self._create_decision_nodes(nx_graph, organization_id)

            # Calculate graph metrics
            metrics = self._calculate_graph_metrics(nx_graph, nodes)

            # Find critical paths
            critical_paths = self._find_critical_paths(nx_graph, nodes)

            # Detect bottlenecks
            bottleneck_nodes = self._detect_graph_bottlenecks(nx_graph)

            return DependencyGraph(
                organization_id=organization_id,
                nodes=nodes,
                metrics=metrics,
                critical_paths=critical_paths,
                bottleneck_nodes=bottleneck_nodes,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "failed_to_build_dependency_graph",
                extra={
                    "organization_id": str(organization_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def _build_dependency_graph(
        self, organization_id: Optional[UUID] = None, include_resolved: bool = False
    ) -> nx.DiGraph:
        """
        Build NetworkX directed graph from dependencies.

        Args:
            organization_id: Optional organization filter
            include_resolved: Include resolved dependencies

        Returns:
            NetworkX directed graph
        """
        graph = nx.DiGraph()

        # TODO: Query dependencies from database when table exists
        # For now, return empty graph

        return graph

    def _would_create_cycle(
        self, graph: nx.DiGraph, source: UUID, target: UUID
    ) -> bool:
        """
        Check if adding edge would create a cycle.

        Args:
            graph: NetworkX graph
            source: Source node
            target: Target node

        Returns:
            True if would create cycle, False otherwise
        """
        # Add temporary edge
        graph_copy = graph.copy()
        graph_copy.add_edge(source, target)

        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(graph_copy))
            return len(cycles) > 0
        except Exception:
            return False

    async def _create_decision_nodes(
        self, graph: nx.DiGraph, organization_id: UUID
    ) -> List[DecisionNode]:
        """
        Create decision nodes from graph.

        Args:
            graph: NetworkX graph
            organization_id: Organization ID

        Returns:
            List of decision nodes
        """
        nodes = []

        # Get sessions for nodes
        session_ids = list(graph.nodes())
        if not session_ids:
            return nodes

        # Query sessions from database
        query = select(AlignmentSession).where(
            AlignmentSession.session_id.in_(session_ids)
        )
        result = await self.db.execute(query)
        sessions = {s.session_id: s for s in result.scalars().all()}

        # Create nodes
        for session_id in session_ids:
            session = sessions.get(session_id)
            if not session:
                continue

            # Get dependencies
            incoming = list(graph.predecessors(session_id))
            outgoing = list(graph.successors(session_id))

            # Calculate depth (longest path from any root)
            try:
                depth = max(
                    nx.shortest_path_length(graph, source, session_id)
                    for source in graph.nodes()
                    if graph.in_degree(source) == 0 and nx.has_path(graph, source, session_id)
                ) if graph.in_degree(session_id) > 0 else 0
            except Exception:
                depth = 0

            nodes.append(
                DecisionNode(
                    session_id=session_id,
                    decision_topic=session.decision_topic,
                    status=session.status,
                    dependencies_incoming=[str(d) for d in incoming],
                    dependencies_outgoing=[str(d) for d in outgoing],
                    is_blocked=len(incoming) > 0
                    and session.status != "complete",
                    depth=depth,
                )
            )

        return nodes

    def _calculate_graph_metrics(
        self, graph: nx.DiGraph, nodes: List[DecisionNode]
    ) -> GraphMetrics:
        """
        Calculate metrics for dependency graph.

        Args:
            graph: NetworkX graph
            nodes: Decision nodes

        Returns:
            Graph metrics
        """
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()

        # Find root nodes (no incoming dependencies)
        root_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]

        # Find leaf nodes (no outgoing dependencies)
        leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]

        # Calculate max depth
        max_depth = max((n.depth for n in nodes), default=0)

        # Count blocked nodes
        blocked_nodes = sum(1 for n in nodes if n.is_blocked)

        # Average dependencies
        avg_dependencies_per_node = (
            total_edges / total_nodes if total_nodes > 0 else 0
        )

        return GraphMetrics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            root_nodes=len(root_nodes),
            leaf_nodes=len(leaf_nodes),
            max_depth=max_depth,
            blocked_nodes=blocked_nodes,
            avg_dependencies_per_node=avg_dependencies_per_node,
        )

    def _find_critical_paths(
        self, graph: nx.DiGraph, nodes: List[DecisionNode]
    ) -> List[List[str]]:
        """
        Find critical paths (longest paths from roots to leaves).

        Args:
            graph: NetworkX graph
            nodes: Decision nodes

        Returns:
            List of critical paths (each path is list of session IDs)
        """
        if graph.number_of_nodes() == 0:
            return []

        critical_paths = []

        # Find root nodes
        roots = [n for n in graph.nodes() if graph.in_degree(n) == 0]

        # Find leaves
        leaves = [n for n in graph.nodes() if graph.out_degree(n) == 0]

        # Find longest path from each root to each leaf
        max_length = 0
        for root in roots:
            for leaf in leaves:
                if nx.has_path(graph, root, leaf):
                    try:
                        path = nx.shortest_path(graph, root, leaf)
                        if len(path) > max_length:
                            max_length = len(path)
                            critical_paths = [[str(n) for n in path]]
                        elif len(path) == max_length:
                            critical_paths.append([str(n) for n in path])
                    except Exception:
                        continue

        return critical_paths[:5]  # Return top 5 critical paths

    def _detect_graph_bottlenecks(self, graph: nx.DiGraph) -> List[str]:
        """
        Detect bottleneck nodes (high betweenness centrality).

        Args:
            graph: NetworkX graph

        Returns:
            List of bottleneck session IDs
        """
        if graph.number_of_nodes() == 0:
            return []

        try:
            # Calculate betweenness centrality
            centrality = nx.betweenness_centrality(graph)

            # Get nodes with high centrality (top 20%)
            sorted_nodes = sorted(
                centrality.items(), key=lambda x: x[1], reverse=True
            )
            threshold = int(len(sorted_nodes) * 0.2) or 1

            bottlenecks = [str(node) for node, _ in sorted_nodes[:threshold]]

            return bottlenecks

        except Exception as e:
            logger.warning(
                "failed_to_detect_bottlenecks",
                extra={"error": str(e)},
            )
            return []

    async def get_blocking_sessions(self, session_id: UUID) -> List[UUID]:
        """
        Get sessions that are blocking this session.

        Args:
            session_id: Session ID

        Returns:
            List of blocking session IDs
        """
        try:
            graph = await self._build_dependency_graph()

            if session_id not in graph:
                return []

            # Get all predecessors (incoming dependencies)
            predecessors = list(graph.predecessors(session_id))

            # Filter to only unresolved dependencies
            # TODO: Check resolved status when dependency table exists

            return predecessors

        except Exception as e:
            logger.error(
                "failed_to_get_blocking_sessions",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    async def get_dependent_sessions(self, session_id: UUID) -> List[UUID]:
        """
        Get sessions that depend on this session.

        Args:
            session_id: Session ID

        Returns:
            List of dependent session IDs
        """
        try:
            graph = await self._build_dependency_graph()

            if session_id not in graph:
                return []

            # Get all successors (outgoing dependencies)
            successors = list(graph.successors(session_id))

            return successors

        except Exception as e:
            logger.error(
                "failed_to_get_dependent_sessions",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    async def bulk_get_blocking_sessions(
        self, session_ids: List[UUID]
    ) -> Dict[UUID, List[UUID]]:
        """
        Get blocking sessions for multiple sessions in one query (bulk operation).

        This method eliminates N+1 queries by fetching all blocking sessions
        for multiple session IDs in a single operation.

        Args:
            session_ids: List of session IDs to check

        Returns:
            Dict mapping session_id -> list of blocking session IDs
        """
        try:
            if not session_ids:
                return {}

            # Build dependency graph once
            graph = await self._build_dependency_graph()

            # Build result dict for all requested sessions
            result: Dict[UUID, List[UUID]] = {}

            for session_id in session_ids:
                if session_id not in graph:
                    result[session_id] = []
                else:
                    # Get all predecessors (incoming dependencies)
                    predecessors = list(graph.predecessors(session_id))
                    # TODO: Filter to only unresolved dependencies when dependency table exists
                    result[session_id] = predecessors

            logger.debug(
                "bulk_get_blocking_sessions_completed",
                extra={
                    "session_count": len(session_ids),
                    "total_blocking_sessions": sum(len(v) for v in result.values()),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "failed_to_bulk_get_blocking_sessions",
                extra={
                    "session_count": len(session_ids),
                    "error": str(e),
                },
                exc_info=True,
            )
            # Return empty dict for all sessions on error
            return {sid: [] for sid in session_ids}
