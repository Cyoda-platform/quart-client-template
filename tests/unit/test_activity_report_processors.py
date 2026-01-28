"""
Unit tests for Activity Report processors.

Tests ingestion, processing, and publishing logic.
"""

import pytest

from application.entity.activity_report.version_1.activity_report import (
    ActivityReport,
)
from application.processor.activity_report_ingestion_processor import (
    ActivityReportIngestionProcessor,
)
from application.processor.activity_report_processing_processor import (
    ActivityReportProcessingProcessor,
)


class TestActivityReportIngestionProcessor:
    """Tests for ActivityReportIngestionProcessor."""

    @pytest.fixture
    def processor(self) -> ActivityReportIngestionProcessor:
        """Create processor instance."""
        return ActivityReportIngestionProcessor()

    @pytest.fixture
    def sample_report(self) -> ActivityReport:
        """Create sample ActivityReport."""
        return ActivityReport(report_date="2026-01-28")

    @pytest.mark.asyncio
    async def test_processor_initialization(
        self, processor: ActivityReportIngestionProcessor
    ) -> None:
        """Test processor initializes correctly."""
        assert processor.name == "ActivityReportIngestionProcessor"
        assert processor.logger is not None

    @pytest.mark.asyncio
    async def test_process_returns_activity_report(
        self, processor: ActivityReportIngestionProcessor, sample_report: ActivityReport
    ) -> None:
        """Test process method returns ActivityReport."""
        result = await processor.process(sample_report)
        assert isinstance(result, ActivityReport)
        assert result.report_date == "2026-01-28"

    @pytest.mark.asyncio
    async def test_process_sets_total_activities(
        self, processor: ActivityReportIngestionProcessor, sample_report: ActivityReport
    ) -> None:
        """Test process sets total_activities."""
        result = await processor.process(sample_report)
        assert result.total_activities >= 0

    @pytest.mark.asyncio
    async def test_process_sets_raw_data_location(
        self, processor: ActivityReportIngestionProcessor, sample_report: ActivityReport
    ) -> None:
        """Test process sets raw_data_location."""
        result = await processor.process(sample_report)
        assert result.raw_data_location is not None

    @pytest.mark.asyncio
    async def test_process_sets_processing_metadata(
        self, processor: ActivityReportIngestionProcessor, sample_report: ActivityReport
    ) -> None:
        """Test process sets processing_metadata."""
        result = await processor.process(sample_report)
        assert result.processing_metadata is not None
        assert "apiCallsAttempted" in result.processing_metadata
        assert "apiCallsSuccessful" in result.processing_metadata


class TestActivityReportProcessingProcessor:
    """Tests for ActivityReportProcessingProcessor."""

    @pytest.fixture
    def processor(self) -> ActivityReportProcessingProcessor:
        """Create processor instance."""
        return ActivityReportProcessingProcessor()

    @pytest.fixture
    def sample_report(self) -> ActivityReport:
        """Create sample ActivityReport with data."""
        return ActivityReport(
            report_date="2026-01-28",
            total_activities=1250,
        )

    @pytest.mark.asyncio
    async def test_processor_initialization(
        self, processor: ActivityReportProcessingProcessor
    ) -> None:
        """Test processor initializes correctly."""
        assert processor.name == "ActivityReportProcessingProcessor"
        assert processor.logger is not None

    @pytest.mark.asyncio
    async def test_process_returns_activity_report(
        self,
        processor: ActivityReportProcessingProcessor,
        sample_report: ActivityReport,
    ) -> None:
        """Test process method returns ActivityReport."""
        result = await processor.process(sample_report)
        assert isinstance(result, ActivityReport)

    @pytest.mark.asyncio
    async def test_process_generates_top_activity_types(
        self,
        processor: ActivityReportProcessingProcessor,
        sample_report: ActivityReport,
    ) -> None:
        """Test process generates top activity types."""
        result = await processor.process(sample_report)
        assert len(result.top_activity_types) == 5
        assert all("type" in activity for activity in result.top_activity_types)
        assert all("count" in activity for activity in result.top_activity_types)

    @pytest.mark.asyncio
    async def test_process_generates_trend_highlights(
        self,
        processor: ActivityReportProcessingProcessor,
        sample_report: ActivityReport,
    ) -> None:
        """Test process generates trend highlights."""
        result = await processor.process(sample_report)
        assert len(result.trend_highlights) > 0
        assert all(isinstance(trend, str) for trend in result.trend_highlights)

    @pytest.mark.asyncio
    async def test_process_detects_anomalies(
        self,
        processor: ActivityReportProcessingProcessor,
        sample_report: ActivityReport,
    ) -> None:
        """Test process detects anomalies."""
        result = await processor.process(sample_report)
        assert isinstance(result.flagged_anomalies, list)
        if result.flagged_anomalies:
            for anomaly in result.flagged_anomalies:
                assert "type" in anomaly
                assert "id" in anomaly
                assert "zScore" in anomaly

    @pytest.mark.asyncio
    async def test_top_activity_types_sum_to_total(
        self,
        processor: ActivityReportProcessingProcessor,
        sample_report: ActivityReport,
    ) -> None:
        """Test top activity types sum to approximately total."""
        result = await processor.process(sample_report)
        total_from_types = sum(
            activity["count"] for activity in result.top_activity_types
        )
        assert total_from_types <= result.total_activities

    @pytest.mark.asyncio
    async def test_anomaly_z_scores_above_threshold(
        self,
        processor: ActivityReportProcessingProcessor,
        sample_report: ActivityReport,
    ) -> None:
        """Test anomalies have z-scores above threshold."""
        result = await processor.process(sample_report)
        for anomaly in result.flagged_anomalies:
            assert anomaly["zScore"] > 3.0

    @pytest.mark.asyncio
    async def test_process_with_zero_activities(
        self, processor: ActivityReportProcessingProcessor
    ) -> None:
        """Test process handles zero activities gracefully."""
        report = ActivityReport(report_date="2026-01-28", total_activities=0)
        result = await processor.process(report)
        assert result.total_activities == 0
        assert isinstance(result.top_activity_types, list)
        assert isinstance(result.flagged_anomalies, list)

    @pytest.mark.asyncio
    async def test_process_with_large_activity_count(
        self, processor: ActivityReportProcessingProcessor
    ) -> None:
        """Test process handles large activity counts."""
        report = ActivityReport(report_date="2026-01-28", total_activities=100000)
        result = await processor.process(report)
        assert result.total_activities == 100000
        total_from_types = sum(
            activity["count"] for activity in result.top_activity_types
        )
        assert total_from_types <= result.total_activities
