# ---------------------------------------------- #
# DO NOT IMPORT ANY HEC MODULES FROM THIS MODULE #
# ---------------------------------------------- #
import types
from enum import Enum
from typing import Union


def import_hec() -> types.ModuleType:
    """
    Lazy-imports the hec module to prevent circular imports

    Returns:
        types.ModuleType: the imported hec module
    """
    import hec

    return hec


class LookupMethod(Enum):
    NULL = (1, "Return null if between values or outside range")
    ERROR = (2, "Raise an exception if between values or outside range")
    LINEAR = (
        3,
        "Linear interpolation or extrapolation of independent and dependent values",
    )
    LOGARITHMIC = (
        4,
        "Logarithmic interpolation or extrapolation of independent and dependent values",
    )
    LINLOG = (
        5,
        "Linear interpolation/extrapoloation of independent values, Logarithmic of dependent values",
    )
    LOGLIN = (
        6,
        "Logarithmic interpolation/extrapoloation of independent values, Linear of dependent values",
    )
    PREVIOUS = (7, "Return the value that is lower in position")
    NEXT = (8, "Return the value that is higher in position")
    NEAREST = (9, "Return the value that is nearest in position")
    LOWER = (10, "Return the value that is lower in magnitude")
    HIGHER = (11, "Return the value that is higher in magnitude")
    CLOSEST = (12, "Return the value that is closest in magnitude")

    def __init__(self, value: int, doc: str):
        self.__value__ = value
        self.__doc__ = doc

    @classmethod
    def get(cls, key: Union[str, int]) -> "LookupMethod":
        if isinstance(key, str):
            return cls[key.upper()]
        elif isinstance(key, int):
            for name in cls.__members__:
                member = cls[name]
                if member.__value__ == key:
                    return member
            raise IndexError(key)
        else:
            raise TypeError(f"Expected str or int, got {key.__type__.__name__}")
