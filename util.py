import math


def meters_pretty(meters: float, fdigits: int = 0) -> str:
    suffix = ''
    base = math.log10(meters)    
    if base >= 3:
        base = 3
        suffix = 'km'
    elif base >= 0:
        base = 0
        suffix = 'm'
    elif base >= -2:
        base = -2
        suffix = 'cm'
    elif base >= -3:
        base = -3
        suffix = 'mm'
    elif base >= -6:
        base = -6
        suffix = 'um'
    elif base >= -9:
        base = -9
        suffix = 'nm'
    elif base >= -12:
        base = -12
        suffix = 'pm'
    else:
        base = -15
        suffix = 'fm'
    
    n = meters / math.pow(10, base)
    return f'{n:.{fdigits}f} {suffix}'


def approx_equal(a: float, b: float, epsilon: float = 1.0e-9) -> bool:
    return abs(a - b) < epsilon


def smaller_pow(value: float, base: float = 10) -> float:
    n = math.log(value, base)
    n = math.floor(n)
    return math.pow(base, n)


def larger_pow(value: float, base: float = 10) -> float:
    n = math.log(value, base)
    n = math.ceil(n)
    return math.pow(base, n)


def round_to_next(value: float, div: float) -> float:
    n = value / div
    n = math.ceil(n)
    return n * div


def clamp(value, mini, maxi):
    return min(max(value, mini), maxi)
