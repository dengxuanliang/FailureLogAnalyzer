"""Error taxonomy tree — 3-level, configurable via YAML."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class TaxonomyNode:
    name: str
    level: int  # 1, 2, or 3
    parent: Optional["TaxonomyNode"] = field(default=None, repr=False)
    children: list["TaxonomyNode"] = field(default_factory=list)

    @property
    def path(self) -> str:
        parts = []
        node: Optional[TaxonomyNode] = self
        while node:
            parts.append(node.name)
            node = node.parent
        return ".".join(reversed(parts))


class TaxonomyTree:
    def __init__(self) -> None:
        self._nodes: dict[str, TaxonomyNode] = {}  # path -> node
        self._roots: list[TaxonomyNode] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def root_nodes(self) -> list[TaxonomyNode]:
        return list(self._roots)

    def get_node(self, name: str) -> Optional[TaxonomyNode]:
        for node in self._nodes.values():
            if node.name == name:
                return node
        return None

    def resolve_path(self, path: str) -> Optional[TaxonomyNode]:
        return self._nodes.get(path)

    def all_paths(self) -> list[str]:
        return list(self._nodes.keys())

    def extend_from_yaml(self, yaml_path: str) -> None:
        with open(yaml_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        for entry in data.get("nodes", []):
            self._add_path(entry["path"], entry.get("level"))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_path(self, path: str, level: Optional[int] = None) -> TaxonomyNode:
        if path in self._nodes:
            return self._nodes[path]
        parts = path.split(".")
        parent: Optional[TaxonomyNode] = None
        for i, part in enumerate(parts):
            partial = ".".join(parts[: i + 1])
            if partial not in self._nodes:
                node = TaxonomyNode(
                    name=part,
                    level=i + 1,
                    parent=parent,
                )
                self._nodes[partial] = node
                if parent is None:
                    self._roots.append(node)
                else:
                    parent.children.append(node)
            parent = self._nodes[partial]
        return self._nodes[path]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load_default(cls) -> "TaxonomyTree":
        tree = cls()
        for path in _DEFAULT_PATHS:
            tree._add_path(path)
        return tree


# Full default taxonomy from spec Section 5.1
_DEFAULT_PATHS = [
    # L1 — Format Errors
    "格式与规范错误",
    "格式与规范错误.输出格式不符",
    "格式与规范错误.JSON/代码块解析失败",
    "格式与规范错误.空回答/拒绝回答",
    "格式与规范错误.语言不匹配",
    "格式与规范错误.超长/截断回答",
    # L1 — Extraction Errors
    "解析类错误",
    "解析类错误.代码提取为空",
    "解析类错误.代码提取不完整",
    "解析类错误.答案提取错误",
    "解析类错误.提取字段类型错误",
    # L1 — Knowledge Errors
    "知识性错误",
    "知识性错误.事实性错误",
    "知识性错误.事实性错误.核心知识点错误",
    "知识性错误.事实性错误.边界/细节知识缺失",
    "知识性错误.事实性错误.过时知识",
    "知识性错误.概念混淆",
    "知识性错误.领域知识盲区",
    # L1 — Reasoning Errors
    "推理性错误",
    "推理性错误.逻辑推理错误",
    "推理性错误.逻辑推理错误.前提正确但推理链断裂",
    "推理性错误.逻辑推理错误.错误的因果推断",
    "推理性错误.逻辑推理错误.遗漏关键条件",
    "推理性错误.数学/计算错误",
    "推理性错误.数学/计算错误.算术错误",
    "推理性错误.数学/计算错误.公式应用错误",
    "推理性错误.数学/计算错误.单位/量级错误",
    "推理性错误.多步推理退化",
    # L1 — Comprehension Errors
    "理解性错误",
    "理解性错误.题意理解错误",
    "理解性错误.指令遵循失败",
    "理解性错误.上下文遗漏",
    "理解性错误.歧义理解偏差",
    # L1 — Generation Quality
    "生成质量问题",
    "生成质量问题.幻觉",
    "生成质量问题.重复生成",
    "生成质量问题.不完整回答",
    "生成质量问题.过度对齐",
]
