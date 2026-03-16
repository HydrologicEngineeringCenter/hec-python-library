"""
Lazy loaders for optional dependencies that may not be present in all
environments, or that have version constraints incompatible with other
packages. Each function raises a clear, actionable error at call time
rather than at import time.

Results are cached after the first call — the version check and import
overhead are incurred only once per process lifetime.
"""

import functools
from types import ModuleType


@functools.cache
def require_lxml() -> ModuleType:
    """
    Lazily import lxml.etree, requiring version >= 6.0.0.

    Result is cached after the first call — subsequent calls return
    the cached module directly with no version check or import overhead.

    Note: redshift-connector pins lxml<6.0.0, making it incompatible
    with routines that use this function. The error is deferred to
    call time so the rest of the library remains usable.

    Returns:
        The lxml.etree module.

    Raises:
        ImportError: If lxml is not installed.
        RuntimeError: If lxml < 6.0.0 is installed.
    """
    try:
        import importlib.metadata

        from lxml import etree

        version = importlib.metadata.version("lxml")
        major = int(version.split(".")[0])
        if major < 6:
            raise RuntimeError(
                f"lxml>=6.0.0 is required for this operation, but {version} is installed. "
                "Note: redshift-connector pins lxml<6.0.0 — these are mutually incompatible. "
                "Either remove redshift-connector or avoid calling XML-dependent routines "
                "in the same environment."
            )
        return etree
    except ImportError as e:
        raise ImportError(
            "lxml is required for this operation but is not installed. "
            "Install it with: pip install 'lxml>=6.0.0'"
        ) from e
