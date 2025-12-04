import os
from llama_stack_client import LlamaStackClient
from typing import Optional, List, Dict, Any

class F5SecurityAPI:
    """F5 API Security client with unified LlamaStack architecture."""
    
    def __init__(self):
        # Default LlamaStack endpoint for document operations
        self.default_llamastack_endpoint = "http://llamastack:8321"
        self.default_llamastack_client = LlamaStackClient(base_url=self.default_llamastack_endpoint)
    
    def get_llamastack_client(self, endpoint: Optional[str] = None) -> LlamaStackClient:
        """Get LlamaStack client for specified endpoint or default."""
        if endpoint and endpoint != self.default_llamastack_endpoint:
            return LlamaStackClient(base_url=endpoint)
        return self.default_llamastack_client
    
    def get_default_llamastack_client(self):
        """Get the default LlamaStack client for document operations."""
        return self.default_llamastack_client
    
    def get_current_endpoint(self):
        """Get the default LlamaStack endpoint (for compatibility with upload.py)."""
        return self.default_llamastack_endpoint
    
    def fetch_models_from_endpoint(self, endpoint: str) -> List[Dict[str, Any]]:
        """Fetch available models from a LlamaStack endpoint."""
        try:
            client = self.get_llamastack_client(endpoint)
            models = client.models.list()
            return models if models else []
        except Exception as e:
            raise Exception(f"Failed to fetch models from {endpoint}: {str(e)}")
    
    def test_llamastack_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Test LlamaStack endpoint connectivity and return status info."""
        try:
            client = self.get_llamastack_client(endpoint)
            models = client.models.list()
            model_count = len(models) if models else 0
            
            return {
                "success": True,
                "endpoint": endpoint,
                "models_available": model_count,
                "models": models,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "endpoint": endpoint,
                "models_available": 0,
                "models": [],
                "error": str(e)
            }

# Global API instance
f5_security_api = F5SecurityAPI()

# Alias for compatibility with chat.py imports
llama_stack_api = f5_security_api
