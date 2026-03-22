import pytest
from app.rules.taxonomy import TaxonomyTree, TaxonomyNode


def test_builtin_taxonomy_loads():
    tree = TaxonomyTree.load_default()
    assert tree.get_node("格式与规范错误") is not None


def test_l1_nodes_present():
    tree = TaxonomyTree.load_default()
    l1_names = {n.name for n in tree.root_nodes()}
    assert "格式与规范错误" in l1_names
    assert "解析类错误" in l1_names
    assert "知识性错误" in l1_names
    assert "推理性错误" in l1_names
    assert "理解性错误" in l1_names
    assert "生成质量问题" in l1_names


def test_tag_path_resolution():
    tree = TaxonomyTree.load_default()
    node = tree.resolve_path("格式与规范错误.空回答/拒绝回答")
    assert node is not None
    assert node.level == 2


def test_path_not_found_returns_none():
    tree = TaxonomyTree.load_default()
    assert tree.resolve_path("不存在.啥也没有") is None


def test_custom_yaml_extends_tree(tmp_path):
    yaml_content = """
nodes:
  - path: "格式与规范错误.自定义L2节点"
    level: 2
"""
    f = tmp_path / "custom.yaml"
    f.write_text(yaml_content)
    tree = TaxonomyTree.load_default()
    tree.extend_from_yaml(str(f))
    assert tree.resolve_path("格式与规范错误.自定义L2节点") is not None
