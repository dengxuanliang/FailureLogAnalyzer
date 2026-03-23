from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete, select

from app.db.models.analysis_result import AnalysisResult
from app.db.models.enums import AnalysisType, ReportStatus, ReportType, SeverityLevel, TagSource
from app.db.models.error_tag import ErrorTag
from app.db.models.eval_record import EvalRecord
from app.db.models.eval_session import EvalSession
from app.db.models.report import Report
from app.db.session import get_async_session

DEMO_MODEL = "demo-model"
DEMO_DATASET = "demo-set"
DEMO_SOURCE = "demo-seed"


def _demo_session_exists_stmt():
    return (
        select(EvalSession.id)
        .where(
            EvalSession.model == DEMO_MODEL,
            EvalSession.dataset_name == DEMO_DATASET,
        )
        .limit(1)
    )


async def _demo_session_exists(db):
    stmt = _demo_session_exists_stmt()
    return (await db.execute(stmt)).scalar_one_or_none()


async def _purge_demo_data(db):
    await db.execute(
        delete(EvalSession)
        .where(
            EvalSession.model == DEMO_MODEL,
            EvalSession.dataset_name == DEMO_DATASET,
        )
    )
    await db.execute(
        delete(Report).where(Report.created_by == DEMO_SOURCE)
    )


async def _seed(force: bool) -> None:
    async with get_async_session() as db:
        async with db.begin():
            existing = await _demo_session_exists(db)
            if existing is not None and not force:
                print("Demo data already exists. Use --force to seed again.")
                return

            if force:
                await _purge_demo_data(db)

            session_v1 = EvalSession(
                model=DEMO_MODEL,
                model_version="v1",
                benchmark="demo-benchmark",
                dataset_name=DEMO_DATASET,
                total_count=5,
                error_count=3,
                accuracy=0.4,
                config={"source": DEMO_SOURCE, "version": "v1"},
                tags=["demo", "v1"],
            )
            session_v2 = EvalSession(
                model=DEMO_MODEL,
                model_version="v2",
                benchmark="demo-benchmark",
                dataset_name=DEMO_DATASET,
                total_count=5,
                error_count=2,
                accuracy=0.6,
                config={"source": DEMO_SOURCE, "version": "v2"},
                tags=["demo", "v2"],
            )
            db.add_all([session_v1, session_v2])
            await db.flush()

            records_v1 = [
                EvalRecord(
                    session_id=session_v1.id,
                    benchmark=session_v1.benchmark,
                    model_version=session_v1.model_version,
                    task_category="math",
                    question_id="math-1",
                    question="2 + 2 = ?",
                    expected_answer="4",
                    model_answer="5",
                    is_correct=False,
                    score=0.0,
                ),
                EvalRecord(
                    session_id=session_v1.id,
                    benchmark=session_v1.benchmark,
                    model_version=session_v1.model_version,
                    task_category="geography",
                    question_id="geo-1",
                    question="Capital of France?",
                    expected_answer="Paris",
                    model_answer="Lyon",
                    is_correct=False,
                    score=0.0,
                ),
                EvalRecord(
                    session_id=session_v1.id,
                    benchmark=session_v1.benchmark,
                    model_version=session_v1.model_version,
                    task_category="code",
                    question_id="code-1",
                    question="Sort [3, 1, 2].",
                    expected_answer="[1, 2, 3]",
                    model_answer="[3, 2, 1]",
                    is_correct=False,
                    score=0.0,
                ),
                EvalRecord(
                    session_id=session_v1.id,
                    benchmark=session_v1.benchmark,
                    model_version=session_v1.model_version,
                    task_category="math",
                    question_id="math-2",
                    question="2 + 3 = ?",
                    expected_answer="5",
                    model_answer="5",
                    is_correct=True,
                    score=1.0,
                ),
                EvalRecord(
                    session_id=session_v1.id,
                    benchmark=session_v1.benchmark,
                    model_version=session_v1.model_version,
                    task_category="vocab",
                    question_id="vocab-1",
                    question="Opposite of hot?",
                    expected_answer="cold",
                    model_answer="cold",
                    is_correct=True,
                    score=1.0,
                ),
            ]

            records_v2 = [
                EvalRecord(
                    session_id=session_v2.id,
                    benchmark=session_v2.benchmark,
                    model_version=session_v2.model_version,
                    task_category="math",
                    question_id="math-3",
                    question="5 + 4 = ?",
                    expected_answer="9",
                    model_answer="9",
                    is_correct=True,
                    score=1.0,
                ),
                EvalRecord(
                    session_id=session_v2.id,
                    benchmark=session_v2.benchmark,
                    model_version=session_v2.model_version,
                    task_category="geography",
                    question_id="geo-2",
                    question="Capital of Japan?",
                    expected_answer="Tokyo",
                    model_answer="Kyoto",
                    is_correct=False,
                    score=0.0,
                ),
                EvalRecord(
                    session_id=session_v2.id,
                    benchmark=session_v2.benchmark,
                    model_version=session_v2.model_version,
                    task_category="code",
                    question_id="code-2",
                    question="Sort [4, 2, 3].",
                    expected_answer="[2, 3, 4]",
                    model_answer="[2, 3, 4]",
                    is_correct=True,
                    score=1.0,
                ),
                EvalRecord(
                    session_id=session_v2.id,
                    benchmark=session_v2.benchmark,
                    model_version=session_v2.model_version,
                    task_category="translation",
                    question_id="lang-1",
                    question="Translate 'hello' to Spanish.",
                    expected_answer="hola",
                    model_answer="halo",
                    is_correct=False,
                    score=0.0,
                ),
                EvalRecord(
                    session_id=session_v2.id,
                    benchmark=session_v2.benchmark,
                    model_version=session_v2.model_version,
                    task_category="math",
                    question_id="math-4",
                    question="Prime after 5?",
                    expected_answer="7",
                    model_answer="7",
                    is_correct=True,
                    score=1.0,
                ),
            ]
            db.add_all(records_v1 + records_v2)
            await db.flush()

            llm_result_v1 = AnalysisResult(
                record_id=records_v1[0].id,
                analysis_type=AnalysisType.llm,
                error_types=["logic"],
                root_cause="Arithmetic error on a simple addition.",
                severity=SeverityLevel.high,
                confidence=0.78,
                evidence="Answered 2+2 as 5.",
                suggestion="Verify arithmetic before responding.",
                llm_model="gpt-4o",
                llm_cost=0.002,
                unmatched_tags=["logic.arithmetic"],
            )
            rule_result_v1 = AnalysisResult(
                record_id=records_v1[1].id,
                analysis_type=AnalysisType.rule,
                error_types=["knowledge"],
                root_cause="Incorrect capital city.",
                severity=SeverityLevel.medium,
                confidence=0.62,
                evidence="Returned Lyon for France.",
                suggestion="Refresh geography facts.",
            )
            llm_result_v2 = AnalysisResult(
                record_id=records_v2[1].id,
                analysis_type=AnalysisType.llm,
                error_types=["knowledge"],
                root_cause="Confused major cities.",
                severity=SeverityLevel.low,
                confidence=0.55,
                evidence="Returned Kyoto for Japan.",
                suggestion="Double-check capital city lists.",
                llm_model="gpt-4o",
                llm_cost=0.0015,
            )
            db.add_all([llm_result_v1, rule_result_v1, llm_result_v2])
            await db.flush()

            error_tags = [
                ErrorTag(
                    record_id=records_v1[0].id,
                    analysis_result_id=llm_result_v1.id,
                    tag_path="logic.arithmetic.addition",
                    tag_level=3,
                    source=TagSource.llm,
                    confidence=0.86,
                ),
                ErrorTag(
                    record_id=records_v1[1].id,
                    analysis_result_id=rule_result_v1.id,
                    tag_path="knowledge.geography.capital",
                    tag_level=3,
                    source=TagSource.rule,
                    confidence=0.92,
                ),
                ErrorTag(
                    record_id=records_v1[2].id,
                    analysis_result_id=None,
                    tag_path="formatting.order",
                    tag_level=2,
                    source=TagSource.rule,
                    confidence=0.7,
                ),
                ErrorTag(
                    record_id=records_v2[1].id,
                    analysis_result_id=llm_result_v2.id,
                    tag_path="knowledge.geography.capital",
                    tag_level=3,
                    source=TagSource.llm,
                    confidence=0.81,
                ),
                ErrorTag(
                    record_id=records_v2[3].id,
                    analysis_result_id=None,
                    tag_path="translation.spelling",
                    tag_level=2,
                    source=TagSource.rule,
                    confidence=0.65,
                ),
            ]
            db.add_all(error_tags)

            report = Report(
                title="Demo Summary Report",
                report_type=ReportType.summary,
                session_ids=[session_v1.id, session_v2.id],
                benchmark="demo-benchmark",
                model_version="v2",
                status=ReportStatus.done,
                created_by=DEMO_SOURCE,
                content={
                    "summary": "Seeded demo data with two sessions and sample error tags.",
                    "highlights": [
                        "v2 improves accuracy over v1",
                        "Arithmetic and geography errors tagged",
                        "LLM analysis available for sample records",
                    ],
                },
            )
            db.add(report)

        print("Seeded 2 demo sessions, 10 records, 3 analysis results, 5 error tags, 1 report.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo sessions and error analysis data.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Seed even if demo sessions already exist.",
    )
    args = parser.parse_args()
    asyncio.run(_seed(args.force))


if __name__ == "__main__":
    main()
