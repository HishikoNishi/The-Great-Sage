import json
import logging
import os
import time
from typing import List, Optional, Tuple, Union
from rapidfuzz import process, fuzz

logger = logging.getLogger("great_sage.resolution")

class ClarificationRequired:
    def __init__(self, candidates: List[str]):
        self.candidates = candidates

class AppResolver:
    """
    Simplified App Resolution:
    Fuzzy match query against names AND categories in the app registry.
    """
    def __init__(self, registry_path="app_registry.json"):
        self.registry_path = registry_path
        self.registry = {}

        # Wire in app discovery
        from app_discovery import discovery
        discovery.build_if_needed()

        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        try:
            if not os.path.exists(self.registry_path):
                logger.warning(f"Registry file {self.registry_path} missing after discovery attempt.")
                return {}

            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}

    def resolve(self, query: str) -> Union[str, ClarificationRequired, None]:
        """
        Main resolution pipeline.
        Returns:
            - The resolved app name (key in registry)
            - ClarificationRequired object if ambiguous or category-based
            - None if not found
        """
        # Normalize query to lowercase for consistent matching
        query_lower = query.lower()

        # 1. Match against names and categories
        # We match against lowercase versions of the registry keys to ensure case-insensitivity
        all_apps_lower = {name.lower(): name for name in self.registry.keys()}
        all_apps_keys_lower = list(all_apps_lower.keys())

        name_matches = process.extract(query_lower, all_apps_keys_lower, scorer=fuzz.WRatio, limit=5)

        # Convert the matched lowercase keys back to original registry keys and scores
        # name_matches format: [(matched_lower_key, score, index)]
        resolved_name_matches = []
        for matched_lower, score, _ in name_matches:
            original_name = all_apps_lower[matched_lower]
            resolved_name_matches.append((original_name, score))

        category_matches = []
        for name, data in self.registry.items():
            cat = data.get("category", "")
            # Match lowercase query against lowercase category
            score = fuzz.WRatio(query_lower, cat.lower())
            if score >= 80:
                category_matches.append((name, score))

        # Sort category matches by score
        category_matches.sort(key=lambda x: x[1], reverse=True)

        # Handle generic category requests first
        best_name_score = resolved_name_matches[0][1] if resolved_name_matches else 0
        best_cat_score = category_matches[0][1] if category_matches else 0

        if best_cat_score > best_name_score and best_cat_score >= 80:
            # User probably said "open a browser" or "open a game"
            matched_app_name = category_matches[0][0]
            matched_cat = self.registry[matched_app_name].get("category", "")

            # Collect ALL apps in this category
            category_apps = [name for name, data in self.registry.items() if data.get("category") == matched_cat]

            # If only one app exists in this category, resolve it directly
            if len(category_apps) == 1:
                return category_apps[0]

            return ClarificationRequired(category_apps)

        # Handle specific app matches
        if not resolved_name_matches:
            return None

        # SAFETY NET: Harden against short/generic queries (e.g. "game", "app")
        # If query is short (< 6 chars) or category matching failed,
        # require much higher confidence (95+) to avoid nonsensical matches.
        confidence_threshold = 60
        if len(query_lower) < 6 or best_cat_score < 80:
            confidence_threshold = 95

        if best_name_score < confidence_threshold:
            return None

        best_match, score = resolved_name_matches[0]

        # Ambiguity check: Top 2 within 10 points
        if len(resolved_name_matches) > 1:
            score_diff = resolved_name_matches[0][1] - resolved_name_matches[1][1]
            if score_diff <= 10:
                return ClarificationRequired([m[0] for m in resolved_name_matches[:4]])

        # Single clear match
        if score >= 80:
            return best_match

        # If score is between threshold-80 and no clear ambiguity, we still ask for clarification
        return ClarificationRequired([m[0] for m in resolved_name_matches[:3]])

# Singleton instance
resolver = AppResolver()
