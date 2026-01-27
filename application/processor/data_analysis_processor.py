"""
DataAnalysisProcessor for CSV analysis and statistics computation.

Downloads CSV, analyzes with pandas, and computes summary statistics.
"""

import io
import logging
from typing import Any, Dict

import pandas as pd
import requests

from application.entity.data_analysis import DataAnalysis
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)


class DataAnalysisProcessor(CyodaProcessor):
    """Processor for analyzing CSV data and computing statistics."""

    def __init__(self) -> None:
        super().__init__(
            name="DataAnalysisProcessor",
            description="Downloads and analyzes CSV data with pandas",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process DataAnalysis entity by downloading and analyzing CSV.

        Args:
            entity: The DataAnalysis entity to process
            **kwargs: Additional processing parameters

        Returns:
            Updated DataAnalysis entity with analysis results
        """
        try:
            data_analysis = cast_entity(entity, DataAnalysis)
            logger.info(f"Processing DataAnalysis {data_analysis.technical_id}")

            # Download CSV
            response = requests.get(data_analysis.csv_url, timeout=30)
            response.raise_for_status()

            # Parse CSV with pandas
            df = pd.read_csv(io.StringIO(response.text))

            # Extract basic info
            data_analysis.row_count = len(df)
            data_analysis.column_count = len(df.columns)
            data_analysis.columns = df.columns.tolist()

            # Compute summary statistics
            summary_stats: Dict[str, Any] = {}
            for col in df.select_dtypes(include=["number"]).columns:
                summary_stats[col] = {
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                }

            data_analysis.summary_stats = summary_stats
            data_analysis.analysis_result = {
                "row_count": data_analysis.row_count,
                "column_count": data_analysis.column_count,
                "columns": data_analysis.columns,
                "summary_stats": summary_stats,
            }
            data_analysis.status = "completed"
            data_analysis.update_timestamp()

            logger.info(
                f"Completed analysis for {data_analysis.technical_id}: "
                f"{data_analysis.row_count} rows, {data_analysis.column_count} cols"
            )

            return data_analysis

        except requests.RequestException as e:
            logger.error(f"Failed to download CSV: {str(e)}")
            data_analysis.status = "failed"
            data_analysis.update_timestamp()
            return data_analysis
        except Exception as e:
            logger.exception(f"Error processing DataAnalysis: {str(e)}")
            data_analysis.status = "failed"
            data_analysis.update_timestamp()
            return data_analysis

