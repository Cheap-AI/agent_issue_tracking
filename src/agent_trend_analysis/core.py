from typing import Sequence

import numpy as np


def trend_mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean of a sequence of numbers.

    This is a tiny helper used as a placeholder for more advanced trend analysis.

    Args:
        values: sequence of numeric values (floats or ints)

    Returns:
        float: mean of the values

    Raises:
        ValueError: if values is empty
    """
    if not values:
        raise ValueError("values must not be empty")
    arr = np.asarray(values, dtype=float)
    return float(np.mean(arr))
