import os
import typing as tp
from numbers import Number
from dataclasses import dataclass

try:
    import click
except ImportError:
    click = None

from .math import *
from .table import TableParameters

__all__ = ('Designer', 'DesignResult')

class Designer:
    """A utility to assist in choosing correct values for
    :class:`~.table.TableParameters`
    """
    ncols: int #: Current number of columns
    nrows: int #: Current number of rows
    prime_num: int #: Current prime number
    aspect_ratio_min: Number #: Minimum valid value for :attr:`aspect_ratio`
    aspect_ratio_max: Number #: Maximum valid value for :attr:`aspect_ratio`
    def __init__(
        self, aspect_ratio_min: Number = 0.4, aspect_ratio_max: Number = 2.5,
    ):
        self.ncols, self.nrows, self.prime_num = 1, 1, 1
        self.aspect_ratio_min = aspect_ratio_min
        self.aspect_ratio_max = aspect_ratio_max

    @property
    def aspect_ratio(self) -> float:
        """The aspect ratio of :attr:`ncols` and :attr:`nrows`
        """
        return self.ncols / self.nrows

    def next_prime(self):
        p = self.prime_num
        x = p + 1
        while True:
            if all(x % i != 0 for i in range(2, int(x**.5)+1)):
                self.prime_num = x
                return x
            x += 1

    def is_aspect_ratio_valid(self):
        rmin, rmax = self.aspect_ratio_min, self.aspect_ratio_max
        return rmin <= self.aspect_ratio <= rmax

    def is_valid(self) -> bool:
        """Check whether the current values are valid

        * :attr:`prime_num` must equal :attr:`ncols` + :attr:`nrows` + 1
        * :attr:`aspect_ratio` must be within the range (:attr:`aspect_ratio_min`,
          :attr:`aspect_ratio_max`)
        * :attr:`ncols` and :attr:`nrows` must be :term:`coprime` to each other
        * :attr:`prime_num` must be a prime number
        """
        if self.ncols * self.nrows + 1 != self.prime_num:
            return False
        if not self.is_aspect_ratio_valid():
            return False
        if not is_coprime(self.nrows, self.ncols):
            return False
        if not is_prime(self.prime_num):
            return False
        if not has_prim_roots(self.prime_num):
            return False
        return True

    def from_ncols(self, ncols: int) -> tp.Iterable['DesignResult']:
        """Find possible choices for :attr:`nrows` (and thus :attr:`prime_num`)
        with the given value for :attr:`ncols`

        Iterates through all possible values for :attr:`nrows` that are valid
        using the constraints listed in :meth:`is_valid`. For each valid result,
        a :class:`DesignResult` is yielded.
        """
        self.ncols = ncols
        min_rows = 2
        max_rows = ncols * 3

        results = set()

        self.nrows = min_rows
        while self.nrows <= max_rows:
            self.prime_num = self.ncols * self.nrows + 1
            while not is_prime(self.prime_num):
                self.nrows += 1
                self.prime_num = self.ncols * self.nrows + 1
            if self.is_valid() and self.prime_num not in results:
                yield self._build_result()
                results.add(self.prime_num)
            self.nrows += 1

    def from_prime_num(self, prime_num: int) -> tp.Iterable['DesignResult']:
        """Find possible choices for :attr:`ncols` and :attr:`nrows` for the
        given prime number

        Iterates through all :term:`coprime` pairs of ``prime_num - 1`` that
        match the constraints listed in :meth:`is_valid`. For each valid pair,
        a :class:`DesignResult` is yielded.
        """
        self.prime_num = prime_num
        prime_changed = False
        while not is_prime(self.prime_num) and not has_prim_roots(self.prime_num):
            self.next_prime()
            prime_changed = True
        print(f'using {self.prime_num} for prime')

        coprime_pairs = []
        for ncols, nrows in iter_coprimes(self.prime_num - 1):
            self.ncols, self.nrows = ncols, nrows
            if self.is_valid():
                yield self._build_result()
                coprime_pairs.append((nrows, ncols))
        for ncols, nrows in coprime_pairs:
            self.ncols, self.nrows = ncols, nrows
            if self.is_valid():
                yield self._build_result()

    def _build_result(self) -> 'DesignResult':
        return DesignResult(
            ncols=self.ncols, nrows=self.nrows, prime_num=self.prime_num,
        )

@dataclass
class DesignResult:
    """Result from :class:`Designer`
    """
    ncols: int #: Number of columns
    nrows: int #: Number of rows
    prime_num: int #: Prime number

    @property
    def aspect_ratio(self) -> float:
        """The aspect ratio of :attr:`ncols` and :attr:`nrows`
        """
        return self.ncols / self.nrows

    def get_primitive_roots(self) -> tp.List[int]:
        """Get all :term:`primitive roots <primitive root>` of :attr:`prime_num`
        """
        return list(self.iter_primitive_roots())

    def iter_primitive_roots(self) -> tp.Iterable[int]:
        yield from prim_roots(self.prime_num)

    def choose_primitive_root(self) -> int:
        """Find the smallest :term:`primitive root` of :attr:`prime_num`

        Raises:
            ValueError: if no primitive roots exist
        """
        roots = self.get_primitive_roots()
        if not len(roots):
            raise ValueError(f'No primitive roots found for {self.prime_num}')
        try:
            root = min([r for r in roots if r > 2])
        except ValueError:
            root = min(roots)
        return root

    def to_parameters(
        self,
        design_freq: int,
        prime_root: tp.Optional[int] = None,
        well_width: tp.Optional[float] = 3.81,
        speed_of_sound: tp.Optional[int] = SPEED_OF_SOUND,
    ) -> TableParameters:
        """Create a :class:`~.table.TableParameters` instance using this result

        All arguments of this method will be passed to the constructor
        (documented :class:`here <.table.TableParameters>`).
        If *prime_root* is not given, a value will be chosen by
        :meth:`choose_primitive_root`
        """
        if prime_root is None:
            prime_root = self.choose_primitive_root()
        return TableParameters(
            nrows=self.nrows, ncols=self.ncols, prime_num=self.prime_num,
            prime_root=prime_root, design_freq=design_freq,
            well_width=well_width, speed_of_sound=speed_of_sound,
        )

if click is not None:
    @click.group()
    @click.option('-f', '--design-freq', type=int)
    @click.option('-w', '--well-width', default=3.81)
    @click.option('-s', '--speed-of-sound', default=SPEED_OF_SOUND)
    @click.option('-r', '--prime-root', type=int)
    @click.option('--offset', default=0)
    @click.option('--format',
        type=click.Choice(['csv', 'rst'], case_sensitive=False),
        default='rst',
    )
    @click.pass_context
    def design(ctx, **kwargs):
        ctx.ensure_object(dict)
        ctx.obj.update({k:v for k,v in kwargs.items()})

    def _build_result_and_output(ctx: click.Context, result: DesignResult):
        param_kw = ctx.obj.copy()
        offset, out_fmt = param_kw.pop('offset'), param_kw.pop('format')
        if not param_kw['prime_root']:
            roots = list(prim_roots(result.prime_num))
            if len(roots) > 10:
                roots = roots[:11]
            roots = [str(v) for v in roots]
            pr = click.prompt(
                'Choose a primitive root', type=click.Choice(roots),
            )
            param_kw['prime_root'] = int(pr)
        if not param_kw['design_freq']:
            value = click.prompt('Please enter design frequency', type=int)
            param_kw['design_freq'] = value
        p = result.to_parameters(**param_kw)
        tbl_result = p.calculate()
        if out_fmt == 'csv':
            click.echo(tbl_result.to_csv(offset=offset))
        else:
            click.echo(tbl_result.to_rst(offset=offset))
        click.echo(tbl_result.get_info_str(offset=offset))

    @design.command(name='cols')
    @click.option('--ncols', type=int, prompt=True)
    @click.pass_context
    def from_cols(ctx, ncols):
        d = Designer()
        found = False
        for result in d.from_ncols(ncols):
            found = True
            info_txt = (
                f'({result.ncols}x{result.nrows}), aspect={result.aspect_ratio:.3f},'
                f'prime_num={result.prime_num}'
            )
            click.echo(info_txt)
            if click.confirm('Use this design?'):
                _build_result_and_output(ctx, result)
                break
        if not found:
            click.echo('No results found')

    @design.command(name='prime')
    @click.option('--prime-num', type=int, prompt=True)
    @click.pass_context
    def from_prime_num(ctx, prime_num):
        d = Designer()
        found = False
        for result in d.from_prime_num(prime_num):
            found = True
            info_txt = (
                f'({result.ncols}x{result.nrows}), aspect={result.aspect_ratio:.3f},'
                f'prime_num={result.prime_num}'
            )
            click.echo(info_txt)
            if click.confirm('Use this design?'):
                _build_result_and_output(ctx, result)
                break
        if not found:
            click.echo('No results found')

    if __name__ == '__main__':
        design()
