"""Mock PLoT client for testing TAE orchestration endpoint.

Simulates PLoT Engine calling TAE's /api/v1/plot/alignment-session endpoint.
Used for integration testing without requiring actual PLoT Engine deployment.
"""

import httpx
from typing import Dict, List, Any, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class MockPLoTClient:
    """
    Mock PLoT client that simulates PLoT Engine calling TAE.

    This is a test utility that makes requests to TAE's orchestration endpoint
    as if coming from the PLoT Engine. Used for integration testing.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "test-plot-api-key-1234567890abcdef",
    ):
        """
        Initialize mock PLoT client.

        Args:
            base_url: TAE server base URL
            api_key: PLoT internal API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        self.request_history: List[Dict[str, Any]] = []

    async def get_alignment_session(
        self,
        session_id: Optional[str] = None,
        organization_id: str = "test-org-123",
        capabilities: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request alignment session data from TAE.

        Simulates PLoT calling TAE's /api/v1/plot/alignment-session endpoint.

        Args:
            session_id: Session ID for session-specific data (None for portfolio)
            organization_id: Organization ID for context
            capabilities: Requested capabilities list
            context: Additional request context
            request_id: X-Request-ID header for tracing

        Returns:
            TAE alignment session response

        Raises:
            httpx.HTTPError: If request fails
        """
        if capabilities is None:
            capabilities = ["core_alignment"]

        if context is None:
            context = {}

        if request_id is None:
            request_id = f"plot-test-{uuid4()}"

        payload = {
            "session_id": session_id,
            "organization_id": organization_id,
            "capabilities": capabilities,
            "context": context,
        }

        headers = {
            "X-API-Key": self.api_key,
            "X-Request-ID": request_id,
            "Content-Type": "application/json",
        }

        logger.info(
            "Mock PLoT requesting alignment session",
            extra={
                "session_id": session_id,
                "organization_id": organization_id,
                "capabilities": capabilities,
                "request_id": request_id,
            },
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/plot/alignment-session",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            # Store in history
            self.request_history.append({
                "endpoint": "/api/v1/plot/alignment-session",
                "request_id": request_id,
                "payload": payload,
                "status_code": response.status_code,
                "response": result,
            })

            logger.info(
                "Mock PLoT received alignment session data",
                extra={
                    "request_id": request_id,
                    "status": "success",
                    "capabilities_returned": list(result.get("capabilities", {}).keys()),
                },
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "Mock PLoT request failed",
                extra={
                    "request_id": request_id,
                    "status_code": e.response.status_code,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        except httpx.HTTPError as e:
            logger.error(
                "Mock PLoT connection error",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True,
            )
            raise

    async def request_core_alignment(
        self,
        session_id: str,
        organization_id: str = "test-org-123",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request core alignment data only.

        Convenience method for requesting just core alignment capability.

        Args:
            session_id: Session ID
            organization_id: Organization ID
            request_id: Request ID for tracing

        Returns:
            Core alignment data
        """
        return await self.get_alignment_session(
            session_id=session_id,
            organization_id=organization_id,
            capabilities=["core_alignment"],
            request_id=request_id,
        )

    async def request_with_dependencies(
        self,
        session_id: str,
        organization_id: str = "test-org-123",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request alignment with decision dependencies (D3).

        Args:
            session_id: Session ID
            organization_id: Organization ID
            request_id: Request ID for tracing

        Returns:
            Alignment data with dependencies
        """
        return await self.get_alignment_session(
            session_id=session_id,
            organization_id=organization_id,
            capabilities=["core_alignment", "d3_dependencies"],
            request_id=request_id,
        )

    async def request_with_patterns(
        self,
        session_id: str,
        organization_id: str = "test-org-123",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request alignment with pattern analysis (D4).

        Args:
            session_id: Session ID
            organization_id: Organization ID
            request_id: Request ID for tracing

        Returns:
            Alignment data with patterns
        """
        return await self.get_alignment_session(
            session_id=session_id,
            organization_id=organization_id,
            capabilities=["core_alignment", "d4_patterns"],
            request_id=request_id,
        )

    async def request_portfolio_analytics(
        self,
        organization_id: str = "test-org-123",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request portfolio analytics (D1) - no specific session.

        Args:
            organization_id: Organization ID
            request_id: Request ID for tracing

        Returns:
            Portfolio analytics data
        """
        return await self.get_alignment_session(
            session_id=None,  # Portfolio query
            organization_id=organization_id,
            capabilities=["d1_portfolio"],
            request_id=request_id,
        )

    async def request_all_capabilities(
        self,
        session_id: str,
        organization_id: str = "test-org-123",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request all available capabilities.

        Args:
            session_id: Session ID
            organization_id: Organization ID
            request_id: Request ID for tracing

        Returns:
            Complete alignment data with all capabilities
        """
        return await self.get_alignment_session(
            session_id=session_id,
            organization_id=organization_id,
            capabilities=[
                "core_alignment",
                "d1_portfolio",
                "d3_dependencies",
                "d4_patterns",
            ],
            request_id=request_id,
        )

    def get_request_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all requests made by this mock client.

        Returns:
            List of request/response pairs
        """
        return self.request_history

    def clear_history(self) -> None:
        """Clear request history."""
        self.request_history.clear()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory function for easy test usage
def create_mock_plot_client(
    base_url: str = "http://localhost:8000",
    api_key: str = "test-plot-api-key-1234567890abcdef",
) -> MockPLoTClient:
    """
    Create a configured MockPLoTClient instance.

    Args:
        base_url: TAE server base URL
        api_key: PLoT internal API key

    Returns:
        Configured MockPLoTClient instance

    Example:
        >>> async with create_mock_plot_client() as plot_client:
        ...     response = await plot_client.get_alignment_session(
        ...         session_id="test-session-123",
        ...         capabilities=["core_alignment", "d3_dependencies"]
        ...     )
    """
    return MockPLoTClient(base_url=base_url, api_key=api_key)
