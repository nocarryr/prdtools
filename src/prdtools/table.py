import argparse
import typing as tp
from numbers import Number

import numpy as np
import numpy.typing as npt

from .math import *

TableIndices = tp.NewType('TableIndices', tp.Tuple[tp.List[int], tp.List[int]])

TABLE_DTYPE = np.dtype([
    ('primes', int),
    ('indices', int),
    ('wells', float),
])

def kth_diag_indices(
    ncols: int, nrows: int, k: int
) -> TableIndices:
    """Calculate the indices representing a diagonal of a 2-d array

    This is similar to :func:`numpy.diagonal` and :func:`numpy.diag_indices`,
    but supports arrays with non-uniform shapes (where ``ncols != nrows``).

    The results may be used to directly index an array of shape(nrows, ncols).

    Arguments:
        ncols: Number of columns in the array (shape[0])
        nrows: Number of rows in the array (shape[1])
        k: The diagonal to calculate where k=0 is the main diagonal, k>0 for
            diagonals above the main, and k<0 for diagonals below the main

    Returns:
        rows: The row indices of the diagonal
        cols: The column indices of the diagonal
    """

    shape = (nrows, ncols)
    max_len, min_len = max(shape), min(shape)

    if k >= 0:
        start_row, start_col = 0, k
    else:
        start_row, start_col = -k, 0

    l = list(zip(range(start_row, nrows), range(start_col, ncols)))

    rows = [v[0] for v in l]
    cols = [v[1] for v in l]
    return rows, cols

def iter_diags(ncols: int, nrows: int) -> tp.Iterable[TableIndices]:
    """Iterate over the indices for all diagonals
    of an array of shape(nrows, ncols)

    Uses :func:`kth_diag_indices` to generate the indices

    Arguments:
        ncols: Number of columns in the array (shape[0])
        nrows: Number of rows in the array (shape[1])

    """
    pos_ks = list(range(max([ncols, nrows])))
    neg_ks = [-v for v in pos_ks if v != 0]
    all_ks = set(pos_ks) | set(neg_ks)

    k = 0
    next_row = 1
    while True:
        all_ks.discard(k)
        ix = kth_diag_indices(ncols, nrows, k)
        yield ix
        if not len(all_ks):
            break
        next_col = ix[1][-1] + 1
        if next_col >= ncols:
            next_row = ix[0][-1] + 1
            k = -next_row
        else:
            k = next_col
        assert k in all_ks


def check_arguments(
    prime_num: int, prime_root: int, ncols: int, nrows: int
) -> None:

    assert is_prime(prime_num), f'{prime_num} is not a prime number'
    assert is_prime(prime_root), f'{prime_root} is not a prime number'
    num_wells = ncols * nrows
    assert num_wells == prime_num - 1, f'ncols * nrows must equal prime_num-1'
    assert is_coprime(ncols, nrows), f'ncols and nrows must be coprime'

def prime_root_table(
    prime_num: int, prime_root: int, ncols: int, nrows: int
) -> npt.NDArray[TABLE_DTYPE]:
    """Calculate well indices and prime elements

    Arguments:
        prime_num: The basis prime number where ``prime_num - 1 == ncols * nrows``
        prime_root: A primitive root of *prime_num* used to calculate the sequence
        ncols: Number of columns in the table
        nrows: Number of rows in the table

    *ncols* and *nrows* must be coprime factors of *prime_num*

    The returned array will be of shape ``(nrows, ncols)``
    """
    check_arguments(prime_num, prime_root, ncols, nrows)
    root_sequence = list(prime_root_seq(prime_num, prime_root))
    print(f'{root_sequence=}')
    result = np.zeros((nrows, ncols), dtype=TABLE_DTYPE)
    def iter_roots():
        while True:
            yield from root_sequence

    root_iter = iter_roots()
    diag_iter = iter_diags(ncols, nrows)

    count = 0
    while count < result.size:
        diag_ix = next(diag_iter)
        diag_count = len(diag_ix[0])
        values = np.fromiter(root_iter, dtype=int, count=diag_count)
        result['primes'][diag_ix] = values
        result['indices'][diag_ix] = np.arange(count, count+diag_count)
        count += diag_count
        # print(f'{count=}')
    return result

def well_width(design_freq: int) -> float:
    """Calculate the well width for the given design frequency (in centimeters)
    """
    return wavelength_meters(design_freq) / 2 * 100

def well_height_table(
    prime_num: int, prime_root: int, ncols: int, nrows: int,
    design_freq: int, sos: tp.Optional[Number] = None
) -> npt.NDArray[TABLE_DTYPE]:
    """Calculate the well heights in centimeters for the given arguments

    Arguments:
        prime_num: The basis prime number where ``prime_num - 1 == ncols * nrows``
        prime_root: A primitive root of *prime_num* used to calculate the sequence
        ncols: Number of columns in the table
        nrows: Number of rows in the table
        design_freq: The lowest frequency (in Hz) the diffusor is designed for
        sos: Speed of sound in meters per second. Defaults to 343

    *ncols* and *nrows* must be coprime factors of *prime_num*

    The returned array will be of shape ``(nrows, ncols)``
    """
    result = prime_root_table(prime_num, prime_root, ncols, nrows)
    w = wavelength_cm(design_freq, sos)
    result['wells'] = result['primes'] * w / (prime_num*2)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('ncols', type=int)
    p.add_argument('nrows', type=int)
    p.add_argument('-p', '--prime', dest='prime_num', type=int)
    p.add_argument('-r', '--root', dest='prime_root', type=int)
    p.add_argument('-f', '--freq', dest='design_freq', type=int, required=True)
    p.add_argument('-s', '--sos',
        dest='sos', type=int,
        help='Speed of sound (in meters per second)', default=SPEED_OF_SOUND,
    )

    args = p.parse_args()
    if args.prime_num is None:
        args.prime_num = args.ncols * args.nrows + 1
        print(f'{args.prime_num=}')
        assert is_prime(args.prime_num)
    if args.prime_root is None:
        args.prime_root = min(prim_roots(args.prime_num))
    result = well_height_table(**vars(args))
    wells = np.rint(result['wells'])
    print(np.asarray(wells, dtype=int))
    return result

if __name__ == '__main__':
    main()
