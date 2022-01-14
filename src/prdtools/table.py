import os
import argparse
from dataclasses import dataclass
import typing as tp
from numbers import Number

import numpy as np
import numpy.typing as npt

from .math import *

__all__ = (
    'TableParameters', 'TableResult', 'well_height_table', 'prime_root_table',
    'well_width', 'iter_diags', 'kth_diag_indices',
    'TableArray', 'TABLE_DTYPE', 'TableIndices',
)

TableIndices = tp.NewType('TableIndices', tp.Tuple[tp.Sequence[int], tp.Sequence[int]])
"""Tuple of row and column indices for indexing an :class:`ndarray <numpy.ndarray>`
"""

TABLE_DTYPE = np.dtype([
    ('primes', int),
    ('indices', int),
    ('wells', float),
])
"""A :term:`structured data type` for table results

:param primes: Value from the :func:`prime root sequence <.math.prime_root_seq>`
:param indices: The index of the *primes* value within the sequence
:param wells: The physical well height calculated from *primes* and the
    design wavelength
"""

TableArray = tp.NewType('TableArray', npt.NDArray[TABLE_DTYPE])
"""A structured array of type :data:`TABLE_DTYPE`
"""

def kth_diag_indices(
    ncols: int, nrows: int, k: int
) -> TableIndices:
    """Calculate the indices representing a diagonal of a 2-d array

    This is similar to :func:`numpy.diagonal` and :func:`numpy.diag_indices`,
    but supports arrays with non-uniform shapes (where ``ncols != nrows``).

    The results may be used to directly index an array of shape ``(nrows, ncols)``.

    Arguments:
        ncols: Number of columns in the array (``shape[0]``)
        nrows: Number of rows in the array (``shape[1]``)
        k: The diagonal to calculate where k=0 is the main diagonal, k>0 for
            diagonals above the main, and k<0 for diagonals below the main

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
    of an array of shape ``(nrows, ncols)``

    Uses :func:`kth_diag_indices` to generate the indices

    Arguments:
        ncols: Number of columns in the array (``shape[0]``)
        nrows: Number of rows in the array (``shape[1]``)

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


def prime_root_table(parameters: 'TableParameters') -> TableArray:
    """Calculate well indices and prime elements for the given
    :class:`TableParameters`

    The returned array will be of shape ``(nrows, ncols)``
    """
    p = parameters
    p.validate()
    root_sequence = list(prime_root_seq(p.prime_num, p.prime_root))
    result = np.zeros((p.nrows, p.ncols), dtype=TABLE_DTYPE)
    def iter_roots():
        while True:
            yield from root_sequence

    root_iter = iter_roots()
    diag_iter = iter_diags(p.ncols, p.nrows)

    count = 0
    while count < result.size:
        diag_ix = next(diag_iter)
        diag_count = len(diag_ix[0])
        values = np.fromiter(root_iter, dtype=int, count=diag_count)
        result['primes'][diag_ix] = values
        result['indices'][diag_ix] = np.arange(count, count+diag_count)
        count += diag_count
    return result

def calc_hi_frequency(
    well_width: Number, speed_of_sound: tp.Optional[Number] = SPEED_OF_SOUND
) -> int:
    """Calculate the highest diffusion frequency for the given well width

    Arguments:
        well_width: The well width in centimeters
        speed_of_sound: Speed of sound in meters per second. Defaults to 343
    """
    hf = frequency_cm(well_width * 2, speed_of_sound)
    return round(hf)

def well_height_table(parameters: 'TableParameters') -> TableArray:
    """Calculate the well heights in centimeters for the given
    :class:`TableParameters`

    The returned array will be of shape ``(nrows, ncols)``
    """
    p = parameters
    result = prime_root_table(p)
    w = wavelength_cm(p.design_freq, p.speed_of_sound)
    result['wells'] = result['primes'] * w / (p.prime_num*2)
    return result


@dataclass
class TableParameters:
    """Parameters used to calculate a :class:`TableResult`

    :attr:`ncols` and :attr:`nrows` must be coprime factors of :attr:`prime_num`
    """

    #: Number of table columns
    ncols: int

    #: Number of table rows
    nrows: int

    #: The basis prime number where ``prime_num - 1 == ncols * nrows``
    prime_num: int

    #: A primitive root of :attr:`prime_num` used to calculate the sequence
    prime_root: int

    #: The lowest frequency (in Hz) the diffusor is designed for
    design_freq: int

    #: The width of each well in centimeters
    well_width: tp.Optional[float] = 3.81

    #: Speed of sound in meters per second
    speed_of_sound: tp.Optional[int] = SPEED_OF_SOUND

    @property
    def high_frequency(self) -> int:
        """The highest diffusion frequency possible with the specified
        :attr:`well_width` and :attr:`speed_of_sound`
        """
        return calc_hi_frequency(self.well_width, self.speed_of_sound)

    @property
    def total_width(self) -> float:
        """The total width of the diffusor in centimeters
        """
        return self.well_width * self.ncols

    @property
    def total_height(self) -> float:
        """The total height of the diffusor in centimeters
        """
        return self.well_width * self.nrows

    def validate(self) -> None:
        """Validate the parameters
        """
        assert is_prime(self.prime_num), f'{self.prime_num} is not a prime number'
        assert is_prime(self.prime_root), f'{self.prime_root} is not a prime number'
        num_wells = self.ncols * self.nrows
        assert num_wells == self.prime_num - 1, f'ncols * nrows must equal prime_num-1'
        assert is_coprime(self.ncols, self.nrows), f'ncols and nrows must be coprime'

    def calculate(self) -> 'TableResult':
        """Calculate the :func:`well height table <well_height_table>` and
        return it as a :class:`TableResult`
        """
        data = well_height_table(self)
        return TableResult(self, data)


class TableResult:
    """A calculated table result
    """

    #: The :class:`TableParameters` used to generate the result
    parameters: TableParameters

    #: The result array calculated by :func:`well_height_table`
    data: TableArray

    #: The well heights in :attr:`data` rounded to the nearest centimeter
    well_heights: npt.NDArray[int]

    def __init__(self, parameters: TableParameters, data: TableArray):
        self.parameters = parameters
        self.data = data
        self.well_heights = np.asarray(np.rint(data['wells']), dtype=int)
        self._line_width = None

    @classmethod
    def from_parameters(cls, parameters: TableParameters) -> 'TableResult':
        """Calculate the result from the given :class:`TableParameters`
        """
        return parameters.calculate()

    @classmethod
    def from_kwargs(cls, **kwargs) -> 'TableResult':
        """Calculate the result using parameter values as keyword arguments

        The keyword arguments given must include all necessary values to create
        a :class:`TableParameters` instance
        """
        parameters = TableParameters(**kwargs)
        return cls.from_parameters(parameters)

    def get_well_counts(self) -> tp.Dict[int, int]:
        """Count the total number of each unique well height in
        :attr:`well_heights`

        Returns the result as a dict of ``{well_height: count}``
        """
        heights = self.well_heights
        bins = np.unique(heights)
        bins.sort()
        counts = [heights[heights==h].size for h in bins]
        return {h:c for h,c in zip(bins, counts)}

    def _calc_line_width(self) -> int:
        line_width = self._line_width
        if line_width is not None:
            return line_width
        line_width = np.get_printoptions()['linewidth']
        heights = self.well_heights
        s = np.array2string(heights, separator=',', max_line_width=line_width)
        lines = s.splitlines()
        if not lines[0].endswith('],'):
            line_width += len(lines[1])
            s = np.array2string(heights, separator=',', max_line_width=line_width)
        self._line_width = line_width
        return line_width

    def to_csv(self, separator=',') -> str:
        """Format the :attr:`well_heights` array as a multiline string of
        comma-separated values
        """
        heights = self.well_heights
        line_width = self._calc_line_width()
        lines = []
        for i in range(heights.shape[0]):
            row = heights[i]
            s = np.array2string(row, separator=separator, max_line_width=line_width)
            s = s.lstrip('[').rstrip(']')
            lines.append(s)
        return os.linesep.join(lines)

    def to_rst(self) -> str:
        """Format the :attr:`well_heights` array as an :duref:`rST table <grid-tables>`
        """
        nrows, ncols = self.parameters.nrows, self.parameters.ncols
        value_lines = self.to_csv().splitlines()
        cell_width = value_lines[0].index(',') + 1
        row_sep = '-' * cell_width
        row_sep = f'+{row_sep}' * ncols
        row_sep = f'{row_sep}+'
        lines = [row_sep]
        for line in value_lines:
            line = ' |'.join(line.split(','))
            line = f'|{line} |'
            lines.append(line)
            lines.append(row_sep)
        return os.linesep.join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('ncols', type=int)
    p.add_argument('nrows', type=int)
    p.add_argument('-p', '--prime', dest='prime_num', type=int)
    p.add_argument('-r', '--root', dest='prime_root', type=int)
    p.add_argument('-f', '--freq', dest='design_freq', type=int, required=True)
    p.add_argument('-w', '--well-width',
        dest='well_width', type=float, default=3.81,
    )
    p.add_argument('-s', '--sos',
        dest='speed_of_sound', type=int,
        help='Speed of sound (in meters per second)', default=SPEED_OF_SOUND,
    )

    args = p.parse_args()
    if args.prime_num is None:
        args.prime_num = args.ncols * args.nrows + 1
        print(f'{args.prime_num=}')
        assert is_prime(args.prime_num)
    if args.prime_root is None:
        args.prime_root = min(prim_roots(args.prime_num))
    result = TableResult.from_kwargs(**vars(args))
    print(result.to_rst())
    print('')
    print('Well Counts:')
    print(result.get_well_counts())
    return result

if __name__ == '__main__':
    main()
