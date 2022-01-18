from math import gcd
from prdtools import math

def test_is_prime(prime_numbers):
    primes = set(prime_numbers)
    for p in prime_numbers:
        assert math.is_prime(p)
        assert math.is_prime(-p)
    print(f'{max(primes)=}')
    all_n = set(range(max(primes)))
    non_primes = all_n - primes
    len_non_p = len(non_primes)
    print(f'{len(primes)=}, {len(non_primes)=}')
    for non_p in non_primes:
        assert not math.is_prime(non_p)
        assert not math.is_prime(-non_p)

def test_divisors():
    for num in range(1000):
        found = False
        print(f'{num=}')
        all_divs = set()
        for numer, denom in math.iter_divisors(num):
            assert numer * denom == num
            s = set([numer, denom])
            assert not len(s & all_divs)
            all_divs |= s
            found = True
        if math.is_prime(num) or num == 0:
            assert not found
        else:
            assert found

def test_coprimes():
    for i in range(200):
        for j in range(200):
            coprime = gcd(i, j) == 1
            assert math.is_coprime(i, j) is coprime
            assert math.is_coprime(j, i) is coprime

    for num in range(1000):
        pairs = set()
        for a, b in math.iter_coprimes(num):
            assert gcd(a, b) == 1
            pairs.add((a, b))
        if math.is_prime(num):
            assert not len(pairs)

def phi(n):
    count = 0
    for k in range(1, n+1):
        if gcd(n, k) == 1:
            count += 1
    return count

def test_prim_roots():
    for modulo in range(2, 400):
        roots = list(math.prim_roots(modulo))
        order = phi(modulo)
        power = order * modulo
        print(f'{modulo=}, {order=}, {len(roots)=}')

        for r in roots:
            assert pow(r, power, modulo) == 1
            assert math.is_prim_root(r, modulo)

        all_n = set(range(2, modulo))
        non_roots = all_n - set(roots)
        for nr in non_roots:
            assert nr not in roots
            assert not math.is_prim_root(nr, modulo)
