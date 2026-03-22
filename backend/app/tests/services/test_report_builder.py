from unittest.mock import AsyncMock, patch

import pytest

from app.db.models.enums import ReportType


@pytest.mark.asyncio
async def test_build_summary_report():
    from app.services.report_builder import build_report

    db = AsyncMock()
    with patch("app.services.report_builder.get_analysis_summary", autospec=True) as mock_summary, \
         patch("app.services.report_builder.get_error_distribution", autospec=True) as mock_distribution, \
         patch("app.services.report_builder.get_error_trends", autospec=True) as mock_trends:
        mock_summary.return_value = {
            "total_sessions": 1,
            "total_records": 10,
            "total_errors": 2,
            "accuracy": 0.8,
            "llm_analysed_count": 2,
            "llm_total_cost": 0.05,
        }
        mock_distribution.return_value = [{"label": "推理性错误", "count": 2, "percentage": 100.0}]
        mock_trends.return_value = {"data_points": []}

        report = await build_report(db=db, report_type=ReportType.summary, config={"title": "x"})

    assert report["report_type"] == ReportType.summary.value
    assert "summary" in report
    assert "error_distribution" in report
    assert "trends" in report


@pytest.mark.asyncio
async def test_build_comparison_report():
    from app.services.report_builder import build_report

    db = AsyncMock()
    with patch("app.services.report_builder.compare_versions", autospec=True) as mock_compare, \
         patch("app.services.report_builder.get_version_diff", autospec=True) as mock_diff, \
         patch("app.services.report_builder.get_radar_data", autospec=True) as mock_radar:
        mock_compare.return_value = {
            "version_a": "v1",
            "version_b": "v2",
            "benchmark": None,
            "sessions_a": 1,
            "sessions_b": 1,
            "accuracy_a": 0.7,
            "accuracy_b": 0.8,
            "accuracy_delta": 0.1,
            "error_rate_a": 0.3,
            "error_rate_b": 0.2,
            "error_rate_delta": -0.1,
        }
        mock_diff.return_value = {
            "version_a": "v1",
            "version_b": "v2",
            "regressed": [],
            "improved": [],
            "new_errors": [],
            "fixed_errors": [],
        }
        mock_radar.return_value = {
            "version_a": "v1",
            "version_b": "v2",
            "dimensions": [],
            "scores_a": [],
            "scores_b": [],
        }

        report = await build_report(
            db=db,
            report_type=ReportType.comparison,
            config={"title": "cmp", "version_a": "v1", "version_b": "v2"},
        )

    assert report["report_type"] == ReportType.comparison.value
    assert "comparison" in report
    assert "diff" in report
    assert "radar" in report
