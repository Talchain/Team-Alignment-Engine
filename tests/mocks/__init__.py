"""Mock services for testing TAE without external dependencies."""

from tests.mocks.plot_mock import MockPLoTClient, create_mock_plot_client
from tests.mocks.isl_mock import MockISLServer, create_mock_isl_server

__all__ = [
    "MockPLoTClient",
    "create_mock_plot_client",
    "MockISLServer",
    "create_mock_isl_server",
]
