"""
Confidence Tracking for Automated Brainstorm

Calculates and tracks confidence scores based on expert agreement across buckets.
"""

from typing import Dict, List
from rich.console import Console
from rich.table import Table

console = Console()


class ConfidenceTracker:
    """Tracks and displays confidence scores for brainstorm sessions."""

    def __init__(self):
        """Initialize confidence tracker."""
        self.scene_confidence_scores = {}

    def calculate_expert_agreement(self, bucket_results: List[Dict]) -> Dict[str, float]:
        """
        Calculate confidence scores based on expert agreement.

        Args:
            bucket_results: List of results from different buckets

        Returns:
            Dict with agreement, diversity, and overall confidence scores
        """
        if len(bucket_results) < 2:
            return {
                'agreement': 0.0,
                'diversity': 0.0,
                'overall_confidence': 0.0
            }

        # Simple heuristic: higher confidence when experts align
        # Check for keyword overlap in responses
        all_keywords = []
        for result in bucket_results:
            response = result.get('response', '')
            # Extract key terms (simplified)
            words = response.lower().split()
            keywords = [w for w in words if len(w) > 5]  # Words longer than 5 chars
            all_keywords.append(set(keywords[:50]))  # Top 50 keywords per expert

        # Calculate pairwise agreement
        agreements = []
        for i in range(len(all_keywords)):
            for j in range(i + 1, len(all_keywords)):
                intersection = len(all_keywords[i] & all_keywords[j])
                union = len(all_keywords[i] | all_keywords[j])
                if union > 0:
                    agreements.append(intersection / union)

        avg_agreement = sum(agreements) / len(agreements) if agreements else 0.0

        # Diversity is inverse of agreement (want some diversity)
        diversity = 1.0 - avg_agreement

        # Overall confidence: balanced between agreement and diversity
        overall = (avg_agreement * 0.6 + (1.0 - abs(diversity - 0.5) * 2) * 0.4)

        return {
            'agreement': round(avg_agreement, 2),
            'diversity': round(diversity, 2),
            'overall_confidence': round(overall, 2)
        }

    def store_confidence_score(self, scene_num: int, scores: Dict[str, float]) -> None:
        """
        Store confidence scores for a scene.

        Args:
            scene_num: Scene number
            scores: Dictionary of confidence scores
        """
        self.scene_confidence_scores[scene_num] = scores

    def get_confidence_score(self, scene_num: int) -> Optional[Dict[str, float]]:
        """
        Get stored confidence scores for a scene.

        Args:
            scene_num: Scene number

        Returns:
            Confidence scores dict or None
        """
        return self.scene_confidence_scores.get(scene_num)

    def display_confidence_scores(self, scene_num: int, scores: Dict[str, float]) -> None:
        """
        Display confidence scores in a formatted table.

        Args:
            scene_num: Scene number
            scores: Dictionary of confidence scores
        """
        table = Table(title=f"Scene {scene_num} Confidence Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Interpretation", style="dim")

        # Agreement score
        agreement = scores.get('agreement', 0.0)
        agreement_text = (
            "High alignment" if agreement > 0.7
            else "Moderate alignment" if agreement > 0.4
            else "Low alignment"
        )
        table.add_row("Expert Agreement", f"{agreement:.2f}", agreement_text)

        # Diversity score
        diversity = scores.get('diversity', 0.0)
        diversity_text = (
            "High diversity" if diversity > 0.7
            else "Moderate diversity" if diversity > 0.4
            else "Low diversity"
        )
        table.add_row("Perspective Diversity", f"{diversity:.2f}", diversity_text)

        # Overall confidence
        overall = scores.get('overall_confidence', 0.0)
        overall_text = (
            "Very confident" if overall > 0.8
            else "Confident" if overall > 0.6
            else "Moderate" if overall > 0.4
            else "Low confidence"
        )
        table.add_row("Overall Confidence", f"{overall:.2f}", overall_text)

        console.print(table)

    def get_all_scores(self) -> Dict[int, Dict[str, float]]:
        """
        Get all stored confidence scores.

        Returns:
            Dictionary mapping scene numbers to their confidence scores
        """
        return self.scene_confidence_scores.copy()

    def get_average_confidence(self) -> float:
        """
        Calculate average confidence across all scenes.

        Returns:
            Average overall confidence score
        """
        if not self.scene_confidence_scores:
            return 0.0

        total = sum(
            scores.get('overall_confidence', 0.0)
            for scores in self.scene_confidence_scores.values()
        )
        return total / len(self.scene_confidence_scores)


# Import Optional at module level
from typing import Optional
