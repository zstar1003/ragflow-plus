def normalize_sort_order(sort_order):
    """Return a literal SQL direction; invalid input uses the default DESC.

    SQL keywords cannot be bound as query parameters, so never interpolate
    the supplied value, even after changing its case.
    """
    if isinstance(sort_order, str) and sort_order.strip().lower() == "asc":
        return "ASC"
    return "DESC"
