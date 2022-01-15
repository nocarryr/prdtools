from pathlib import Path
import pytest

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / 'data'

PRIME_NUMBERS = None

def get_primes():
    global PRIME_NUMBERS
    if PRIME_NUMBERS is not None:
        return PRIME_NUMBERS
    p = DATA_DIR / 'prime-numbers.txt'
    s = p.read_text()
    PRIME_NUMBERS = [int(line) for line in s.splitlines()]
    return PRIME_NUMBERS

@pytest.fixture
def prime_numbers():
    return get_primes()
