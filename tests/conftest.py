import pytest

PRIME_NUMBERS = [1]

def next_prime(p):
    x = p + 1
    while True:
        if all(x % i != 0 for i in range(2, int(x**.5)+1)):
            return x
        x += 1

@pytest.fixture
def prime_generator():
    def generate(n):
        if n < len(PRIME_NUMBERS):
            yield from PRIME_NUMBERS[:n+1]
        else:
            yield from PRIME_NUMBERS
            p = PRIME_NUMBERS[-1]
            i = len(PRIME_NUMBERS)
            while i < n:
                p = next_prime(p)
                PRIME_NUMBERS.append(p)
                yield p
                i += 1
    return generate
