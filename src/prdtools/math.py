from math import gcd
import typing as tp
from numbers import Number

__all__ = (
    'SPEED_OF_SOUND', 'wavelength_meters', 'wavelength_cm',
    'frequency_meters', 'frequency_cm', 'prim_roots',
    'is_prime', 'is_coprime', 'iter_divisors', 'iter_coprimes', 'prime_root_seq',
)

SPEED_OF_SOUND: Number = 343
"""Speed of sound in meters per second at 20°C (68°F)
"""

def wavelength_meters(
    freq: int, sos: tp.Optional[Number] = SPEED_OF_SOUND
) -> Number:
    """Calculate the wavelength of the given frequency in meters

    Arguments:
        freq: The frequency in Hz
        sos: Speed of sound in meters per second
    """
    if sos is None:
        sos = SPEED_OF_SOUND
    return sos / freq

def wavelength_cm(
    freq: int, sos: tp.Optional[Number] = SPEED_OF_SOUND
) -> Number:
    """Calculate the wavelength of the given frequency in centimeters

    Arguments:
        freq: The frequency in Hz
        sos: Speed of sound in meters per second
    """
    return wavelength_meters(freq, sos) * 100

def frequency_meters(
    wavelength: Number, sos: tp.Optional[Number] = SPEED_OF_SOUND
) -> Number:
    """Calculate the frequency of the given wavelength in meters

    Arguments:
        wavelength: The wavelength in meters
        sos: Speed of sound in meters per second
    """
    if sos is None:
        sos = SPEED_OF_SOUND
    return sos / wavelength

def frequency_cm(
    wavelength: Number, sos: tp.Optional[Number] = SPEED_OF_SOUND
) -> Number:
    """Calculate the frequency of the given wavelength in centimeters

    Arguments:
        wavelength: The wavelength in centimeters
        sos: Speed of sound in meters per second
    """
    return frequency_meters(wavelength / 100, sos)

def prim_roots(modulo: int) -> tp.List[int]:
    """Calculate all :term:`primitive roots <primitive root>` for the given modulo
    """
    required_set = {num for num in range(1, modulo) if gcd(num, modulo) }
    return [g for g in range(1, modulo) if required_set == {pow(g, powers, modulo)
            for powers in range(1, modulo)}]

def congruence_classes(n: int) -> tp.List[int]:
    results = []
    for k in range(1, n + 1):
        if gcd(n, k) == 1:
            results.append(k)
    return results

def is_prime(n: int) -> bool:
    """Return True if *n* is a prime number
    """
    n = abs(n)
    if n == 0:
        return False
    elif n <= 3:
        return True
    elif n == 4:
        return False
    for i in range(2, n // 2):
        if n % i == 0:
            return False
    return True

def is_coprime(a: int, b: int) -> bool:
    """Return True if a and b are :term:`coprime`
    """
    return gcd(a, b) == 1

def iter_divisors(total_size: int) -> tp.Iterable[tp.Tuple[int, int]]:
    """Iterate over all possible numerator/denominator pairs of the given number
    """
    if total_size == 4:
        yield 2, 2
    seen = set()
    for i in range(2, total_size // 2):
        if i in seen:
            continue
        v = total_size / i
        if v in seen:
            continue
        intv = int(v)
        if v == intv:
            yield i, intv
            seen |= set([i, intv])

def iter_coprimes(total_size: int) -> tp.Iterable[tp.Tuple[int, int]]:
    """Iterate over all :term:`coprime` pairs for the given number
    """
    for i, v in iter_divisors(total_size):
        if is_coprime(i, v):
            yield i, v

def prime_root_seq(
    prime_num: int, prime_root: tp.Optional[int] = None
) -> tp.Iterable[int]:
    r"""Calculate the primitive root sequence :math:`S_h` for the given prime
    and its root

    .. math::

        S_h = g ^ h \bmod{N}

    where :math:`N` = *prime_num*, :math:`g` = *prime_root* and :math:`h` is
    the sequence index (starting with 1). The sequence continues until
    the first repetition of :math:`S_h`.

    Arguments:
        prime_num: Prime number for the sequence
        prime_root: A :term:`primitive root` of the *prime_num*. If not given, an
            attempt will be made to find the first primitive root

    """
    if prime_root is None:
        prime_root = min(prim_roots(prime_num))
    seen = set()
    h = 1
    while True:
        Sh = (prime_root ** h) % prime_num
        if Sh in seen:
            break
        yield Sh
        seen.add(Sh)
        h += 1
