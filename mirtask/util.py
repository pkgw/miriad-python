"""Miscellaneous utility MIRIAD subroutines."""

import lowlevel as ll

def decodeBaseline (encoded, check=True):
    """Decode an encoded baseline double into two antenna numbers."""
    return ll.basants (encoded, check)

def encodeBaseline (ant1, ant2):
    """Encode a pair of antenna numbers into one baseline number
suitable for use in UV data preambles."""
    return ll.antbas (ant1, ant2)
