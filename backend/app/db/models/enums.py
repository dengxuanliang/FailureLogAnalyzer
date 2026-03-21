import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class AnalysisType(str, enum.Enum):
    rule = "rule"
    llm = "llm"
    manual = "manual"


class SeverityLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TagSource(str, enum.Enum):
    rule = "rule"
    llm = "llm"


class StrategyType(str, enum.Enum):
    full = "full"
    fallback = "fallback"
    sample = "sample"
    manual = "manual"


class ReportType(str, enum.Enum):
    summary = "summary"
    comparison = "comparison"
    cross_benchmark = "cross_benchmark"
    custom = "custom"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    done = "done"
    failed = "failed"
