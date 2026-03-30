"""
StartAnalysisProcessor for Cyoda Client Application

Handles the initialization and execution of comment analysis.
Performs sentiment analysis, keyword extraction, and toxicity detection as specified in functional requirements.
"""

import logging
from typing import Any, Dict, List

from application.entity.analysis.version_1.analysis import Analysis
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class StartAnalysisProcessor(CyodaProcessor):
    """
    Processor for Analysis that initializes and performs comment analysis.
    Analyzes sentiment, extracts keywords, detects language, and assesses toxicity.
    """

    def __init__(self) -> None:
        super().__init__(
            name="StartAnalysisProcessor",
            description="Initializes and performs comment analysis including sentiment, keywords, and toxicity",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Analysis entity to perform comment analysis.

        Args:
            entity: The Analysis entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed entity with analysis results
        """
        try:
            self.logger.info(
                f"Starting analysis for Analysis {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Analysis for type-safe operations
            analysis = cast_entity(entity, Analysis)

            # Get the comment to analyze
            comment = await self._get_comment_by_id(analysis.comment_id)
            if not comment:
                raise ValueError(f"Comment with ID {analysis.comment_id} not found")

            # Perform analysis
            sentiment_score = self._analyze_sentiment(comment["content"])
            sentiment_label = self._get_sentiment_label(sentiment_score)
            keywords = self._extract_keywords(comment["content"])
            language = self._detect_language(comment["content"])
            toxicity_score = self._analyze_toxicity(comment["content"])

            # Set analysis results
            analysis.set_analysis_results(
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                keywords=keywords,
                language=language,
                toxicity_score=toxicity_score,
            )

            self.logger.info(f"Analysis {analysis.technical_id} completed successfully")

            return analysis

        except Exception as e:
            self.logger.error(
                f"Error starting analysis for entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _get_comment_by_id(self, comment_id: str) -> Dict[str, Any]:
        """
        Retrieve comment data by ID.

        Args:
            comment_id: The comment ID to retrieve

        Returns:
            Dictionary containing comment data
        """
        entity_service = get_entity_service()

        try:
            # Get the comment entity
            response = await entity_service.get_by_id(
                entity_id=comment_id, entity_class="Comment", entity_version="1"
            )
            if response:
                # Convert the response data to dict format
                if hasattr(response.data, "model_dump"):
                    return response.data.model_dump()
                else:
                    return dict(response.data) if response.data else {}
            else:
                raise ValueError(f"Comment {comment_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to retrieve comment {comment_id}: {str(e)}")
            raise

    def _analyze_sentiment(self, content: str) -> float:
        """
        Analyze sentiment of the comment content.

        In a real implementation, this would use ML models or external APIs.

        Args:
            content: The comment content to analyze

        Returns:
            Sentiment score between -1 and 1
        """
        # Simple sentiment analysis based on keywords
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "love",
            "like",
            "awesome",
            "fantastic",
            "wonderful",
        ]
        negative_words = [
            "bad",
            "terrible",
            "awful",
            "hate",
            "dislike",
            "horrible",
            "worst",
            "disgusting",
            "annoying",
        ]

        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        # Calculate sentiment score
        total_words = len(content.split())
        if total_words == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / max(total_words, 1)
        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, sentiment * 10))

    def _get_sentiment_label(self, sentiment_score: float) -> str:
        """
        Get sentiment label based on score.

        Args:
            sentiment_score: The sentiment score

        Returns:
            Sentiment label: positive, negative, or neutral
        """
        if sentiment_score > 0.1:
            return "positive"
        elif sentiment_score < -0.1:
            return "negative"
        else:
            return "neutral"

    def _extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from comment content.

        In a real implementation, this would use NLP libraries like spaCy or NLTK.

        Args:
            content: The comment content to analyze

        Returns:
            List of extracted keywords
        """
        # Simple keyword extraction - remove common words and get significant terms
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        # Clean and split content
        words = (
            content.lower()
            .replace(".", "")
            .replace(",", "")
            .replace("!", "")
            .replace("?", "")
            .split()
        )

        # Filter out stop words and short words
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]

        # Remove duplicates and limit to top 10
        unique_keywords = list(dict.fromkeys(keywords))[:10]

        return unique_keywords

    def _detect_language(self, content: str) -> str:
        """
        Detect language of the comment content.

        In a real implementation, this would use language detection libraries.

        Args:
            content: The comment content to analyze

        Returns:
            Detected language code
        """
        # Simple language detection based on common words
        english_indicators = [
            "the",
            "and",
            "is",
            "are",
            "was",
            "were",
            "have",
            "has",
            "will",
            "would",
            "this",
            "that",
        ]
        spanish_indicators = [
            "el",
            "la",
            "es",
            "son",
            "fue",
            "fueron",
            "tiene",
            "tengo",
            "este",
            "esta",
        ]
        french_indicators = [
            "le",
            "la",
            "est",
            "sont",
            "était",
            "étaient",
            "avoir",
            "ce",
            "cette",
        ]

        content_lower = content.lower()

        english_count = sum(1 for word in english_indicators if word in content_lower)
        spanish_count = sum(1 for word in spanish_indicators if word in content_lower)
        french_count = sum(1 for word in french_indicators if word in content_lower)

        if english_count >= spanish_count and english_count >= french_count:
            return "en"
        elif spanish_count >= french_count:
            return "es"
        elif french_count > 0:
            return "fr"
        else:
            return "en"  # Default to English

    def _analyze_toxicity(self, content: str) -> float:
        """
        Analyze toxicity of the comment content.

        In a real implementation, this would use ML models like Perspective API.

        Args:
            content: The comment content to analyze

        Returns:
            Toxicity score between 0 and 1
        """
        # Simple toxicity detection based on keywords
        toxic_words = [
            "hate",
            "stupid",
            "idiot",
            "moron",
            "kill",
            "die",
            "murder",
            "attack",
            "destroy",
            "awful",
            "terrible",
            "disgusting",
        ]

        content_lower = content.lower()
        toxic_count = sum(1 for word in toxic_words if word in content_lower)

        # Check for excessive caps (shouting)
        caps_ratio = sum(1 for c in content if c.isupper()) / max(len(content), 1)

        # Calculate toxicity score
        total_words = len(content.split())
        word_toxicity = toxic_count / max(total_words, 1)
        caps_toxicity = caps_ratio if caps_ratio > 0.5 else 0

        toxicity = min(1.0, (word_toxicity * 0.7) + (caps_toxicity * 0.3))

        return toxicity
