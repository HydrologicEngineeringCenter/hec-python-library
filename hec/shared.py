# ---------------------------------------------- #
# DO NOT IMPORT ANY HEC MODULES FROM THIS MODULE #
# ---------------------------------------------- #


def is_leap(y: int) -> bool:
    """
    Return whether the specified year is a leap year

    Args:
        y (int): The year

    Returns:
        bool: Whether the year is a leap year
    """
    return (not bool(y % 4) and bool(y % 100)) or (not bool(y % 400))


def max_day(y: int, m: int) -> int:
    """
    Return the last month day for a specified year and month

    Args:
        y (int): The year
        m (int): The month

    Returns:
        int: The last calendar day of the specified month
    """
    return (
        31
        if m in (1, 3, 5, 7, 8, 10, 12)
        else 30 if m in (4, 6, 9, 11) else 29 if is_leap(y) else 28
    )


def previous_month(y: int, m: int) -> tuple[int, int]:
    """
    Returns the previous year and for a specified year and month.

    Args:
        y (int): The specified year
        m (int): The specified month

    Returns:
        tuple[int, int]: The previous year and month
    """
    m -= 1
    if m < 1:
        y -= 1
        m = 12
    return y, m
