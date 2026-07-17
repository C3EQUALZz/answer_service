import traceback


def render_exception(exc: BaseException) -> str:
    """Render an exception, including ExceptionGroup leaves, to text.

    ``str(exc)`` on a ``DatureConfigError`` only shows the group header; the
    per-field messages live in nested leaves. Rendering the full traceback lets
    tests assert on those messages.
    """
    return "".join(traceback.format_exception(exc))
