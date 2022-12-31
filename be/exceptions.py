class MyValidationError(Exception):
    """Used to signify validation errors (which can't be caught by pydantic)."""

    pass
