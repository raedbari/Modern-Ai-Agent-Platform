"""Provider-independent reranking contracts.

DEPRECATED: Import from backend.app.ai.ports instead.
This module is kept for backward compatibility only.
"""

from backend.app.ai.ports import (
    RerankProvider,
    RerankRequest,
    RerankResult,
)

__all__ = ["RerankProvider", "RerankRequest", "RerankResult"]
