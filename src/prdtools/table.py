import os
import argparse
from dataclasses import dataclass
import typing as tp
from numbers import Number
import locale

import numpy as np
import numpy.typing as npt

from .math import *

__all__ = (
    'TableParameters', 'TableResult', 'well_height_table', 'prime_root_table',
    'well_width', 'build_diag_indices', 'ValidationError', 'TableArray', 'TABLE_DTYPE',
)


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

class ValidationError(ValueError):
    """Raised by :class:`TableParameters` if any parameter values are invalid
    """

    #: Error message
    msg: str

    #: Tuples of ``(field_name, value)`` that caused the error
    fields: tp.Sequence[tp.Tuple[str, tp.Any]]

    #: Field name(s) that caused the error
    field_names: tp.Tuple[str]

    def __init__(self, msg, *fields):
        self.msg = msg
        self.fields = fields
        self.field_names = tuple([fname for fname, fval in fields])

    def __str__(self):
        if len(self.fields) == 1:
            fname, fval = self.fields[0]
            return f'Value "{fval}" invalid for "{fname}": {self.msg}'
        elif len(self.fields):
            fields = ', '.join(self.field_names)
            return f'Invalid values for "{fields}": {self.msg}'
        else:
            return self.msg

def build_diag_indices(
    nrows: int, ncols: int
) -> tp.Tuple[npt.NDArray[int], npt.NDArray[int]]:
    """Create indices for all diagonals of a 2-d array of shape ``(nrows, ncols)``

    The results may be used to directly index an array of shape
    ``(nrows, ncols)`` along the diagonals.

    Arguments:
        nrows: Number of rows in the array (``shape[0]``)
        ncols: Number of columns in the array (``shape[1]``)
    """
    size = nrows * ncols
    rows = np.resize(np.arange(nrows), size)
    cols = np.resize(np.arange(ncols), size)
    return rows, cols


def prime_root_table(parameters: 'TableParameters') -> TableArray:
    """Calculate well indices and prime elements for the given
    :class:`TableParameters`

    The returned array will be of shape ``(nrows, ncols)``
    """
    p = parameters
    p.validate()
    root_gen = prime_root_seq(p.prime_num, p.prime_root)
    result = np.zeros((p.nrows, p.ncols), dtype=TABLE_DTYPE)

    diag_ix = build_diag_indices(p.nrows, p.ncols)
    primes = np.fromiter(root_gen, dtype=int)
    primes = np.resize(primes, result.size)

    result['primes'][diag_ix] = primes
    result['indices'][diag_ix] = np.arange(result.size)
    return result

def calc_hi_frequency(
    well_width: Number, speed_of_sound: tp.Optional[Number] = SPEED_OF_SOUND
) -> int:
    """Calculate the highest diffusion frequency for the given well width

    Arguments:
        well_width: The well width in centimeters
        speed_of_sound: Speed of sound in meters per second
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

    #: A :term:`primitive root` of :attr:`prime_num` used to calculate the sequence
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

        Raises:
            ValidationError: If any parameters are invalid
        """
        p = self.prime_num
        r = self.prime_root
        if not is_prime(p):
            raise ValidationError(
                'Not a prime number', ('prime_num', p),
            )
        if not is_prim_root(r, p):
            raise ValidationError(
                f'{r} is not a primitive root of {p}', ('prime_root', r),
            )
        num_wells = self.ncols * self.nrows
        if num_wells != p - 1:
            raise ValidationError(
                'ncols * nrows must equal prime_num-1',
                ('ncols', self.ncols), ('nrows', self.nrows),
            )
        if not is_coprime(self.ncols, self.nrows):
            raise ValidationError(
                'ncols and nrows must be coprime',
                ('ncols', self.ncols), ('nrows', self.nrows),
            )

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

    def to_csv(
        self, separator: tp.Optional[str] = ',', offset: tp.Optional[int] = 0
    ) -> str:
        """Format the :attr:`well_heights` array as a multiline string of
        comma-separated values

        The *offset* argument will be added to the :attr:`well_heights` before
        output. For well heights of ``0``, there would be no block attached to
        the diffusor in that position. If (for aesthetic reasons) this is
        undesirable, an offset of ``1`` (for example) could be applied to all
        wells.

        Arguments:
            offset: An offset to apply to the well heights. Can be used if wells
                of height ``0`` are undesired.
        """
        heights = self.well_heights + offset
        line_width = self._calc_line_width()
        lines = []
        for i in range(heights.shape[0]):
            row = heights[i]
            s = np.array2string(row, separator=separator, max_line_width=line_width)
            s = s.lstrip('[').rstrip(']')
            lines.append(s)
        return os.linesep.join(lines)

    def to_rst(self, offset: tp.Optional[int] = 0) -> str:
        """Format the :attr:`well_heights` array as an :duref:`rST table <grid-tables>`

        The *offset* argument will be added to the :attr:`well_heights` before
        output. For well heights of ``0``, there would be no block attached to
        the diffusor in that position. If (for aesthetic reasons) this is
        undesirable, an offset of ``1`` (for example) could be applied to all
        wells.

        Arguments:
            offset: An offset to apply to the well heights. Can be used if wells
                of height ``0`` are undesired.
        """
        nrows, ncols = self.parameters.nrows, self.parameters.ncols
        value_lines = self.to_csv(offset=offset).splitlines()
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
    locale.setlocale(locale.LC_NUMERIC, '')
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
    p.add_argument(
        '--offset', dest='offset', type=int, default=0,
    )
    p.add_argument(
        '--format', dest='format', choices=('csv', 'rst'), default='csv',
    )

    args = p.parse_args()
    if args.prime_num is None:
        args.prime_num = args.ncols * args.nrows + 1
        print(f'{args.prime_num=}')
        assert is_prime(args.prime_num)
    if args.prime_root is None:
        args.prime_root = min(prim_roots(args.prime_num))
    out_fmt = args.format
    offset = args.offset
    kwargs = vars(args)
    del kwargs['format']
    del kwargs['offset']
    result = TableResult.from_kwargs(**kwargs)

    if out_fmt == 'csv':
        print(result.to_csv(offset=offset))
    else:
        print(result.to_rst(offset=offset))
    print('')
    print('Well Counts:')
    counts = result.get_well_counts()
    print(os.linesep.join([f'{k:2d}cm: {v:2d}' for k,v in counts.items()]))
    print('')
    total_length = result.well_heights.sum()
    print(f'Total well length: {total_length:n}cm')
    p = result.parameters
    print(f'Highest frequency: {p.high_frequency:n} Hz')
    print(f'Total size: {p.total_width:.3f}cm x {p.total_height}cm')
    print('')
    return result

if __name__ == '__main__':
    main()
