import importlib
import warnings


def _protected_namespace_warnings(caught):
    return [
        warning
        for warning in caught
        if issubclass(warning.category, UserWarning)
        and "protected namespace" in str(warning.message)
    ]


def test_cross_benchmark_schema_import_has_no_protected_namespace_warnings():
    import app.schemas.cross_benchmark as cross_benchmark_module

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(cross_benchmark_module)

    assert _protected_namespace_warnings(caught) == []


def test_report_schema_import_has_no_protected_namespace_warnings():
    import app.schemas.report as report_module

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(report_module)

    assert _protected_namespace_warnings(caught) == []


def test_sessions_router_import_has_no_protected_namespace_warnings():
    import app.api.v1.routers.sessions as sessions_module

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(sessions_module)

    assert _protected_namespace_warnings(caught) == []
