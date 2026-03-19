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
