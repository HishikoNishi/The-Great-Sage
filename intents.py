import yaml
from typing import Optional, Dict, Any
import logging
from config import INTENTS_FILE

logger = logging.getLogger("great_sage.intents")

class IntentRegistry:
    """Manages the loading and lookup of intents from intents.yaml."""

    def __init__(self):
        self.intents = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Load the YAML registry file."""
        try:
            with open(INTENTS_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load intents from {INTENTS_FILE}: {e}")
            return {}

    def get_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the configuration for a specific intent."""
        return self.intents.get(intent_id)

    def list_intents(self) -> list:
        """Return a list of all registered intent IDs."""
        return list(self.intents.keys())

# Singleton instance
registry = IntentRegistry()
