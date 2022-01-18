Glossary
========

.. glossary::
    coprime
        Two integers whose only common divisor is 1

        .. seealso::
            https://en.wikipedia.org/wiki/Coprime_integers

    primitive root
        A number :math:`g` is a primitive root modulo :math:`n` if every
        number :term:`coprime` to :math:`n` is congruent to a power
        of :math:`g \bmod{n}`.

        .. seealso::
            https://en.wikipedia.org/wiki/Primitive_root_modulo_n

    Euler's totient function

        Euler's totient function :math:`\varphi (n)` counts the positive integers
        up to :math:`n` that are :term:`relatively prime <coprime>` to :math:`n`

        .. seealso::
            https://en.wikipedia.org/wiki/Euler%27s_totient_function

    Carmichael function
        The Carmichael function :math:`\lambda (n)` is the smallest possible
        integer :math:`m` satisfying

        .. math::

            a ^ m \equiv 1 \bmod{n} \quad \text{for } n\in \mathbb {Z} > 0

        for every integer :math:`a` between 1 and :math:`n` that is :term:`coprime`
        to :math:`n`

        .. seealso::
            https://en.wikipedia.org/wiki/Carmichael_function
