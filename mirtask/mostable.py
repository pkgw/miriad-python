"""mostable - read mosaic info table dataset items
"""

import numpy as np


class MosaicTable (object):
    nx2 = None
    """Rounded image half-width, not seemingly useful"""

    ny2 = None
    """Rounded image half-height, not seemingly useful"""

    radec = None
    """The celestial coordinates of the pointing centers in radians"""

    pbtype = None
    """Strings describing primary beams associated with each pointing"""

    rms = None
    """The rms associated with each pointing in Jy"""

    radec2 = None
    """?? Something associated with on-the-fly mosaicing"""


def readItem (itemhandle):
    otf = False
    blocksize = 48
    kind = itemhandle.read (4, np.int32, 1)

    if kind == 2:
        blocksize += 16
        otf = True

    offset = 8
    size = itemhandle.getSize ()
    npnt = (size - offset) // blocksize

    if npnt * blocksize + offset != size:
        raise RuntimeError ('unexpected mosaic table size: npnt=%d blocksize=%d '
                            'offset=%d size=%d' % (npnt, blocksize, offset, size))

    radec = np.empty ((npnt, 2), dtype=np.double)
    telescopes = [None] * npnt
    rms2 = np.empty (npnt, dtype=np.float)
    radec2 = np.empty ((npnt, 2), dtype=np.double)

    for i in xrange (npnt):
        # note: same for every entry, apparently
        wh = itemhandle.read (offset, np.int32, 2)
        offset += 8

        itemhandle.readInto (offset, radec[i], 2)
        offset += 16

        telescopes[i] = itemhandle.read (offset, str, 16).rstrip ()
        offset += 16

        itemhandle.readInto (offset, rms2[i:i+1], 1)
        offset += 8 # note: 4 bytes skipped (for alignment)

        if otf:
            itemhandle.readInto (offset, radec2[i], 2)
            offset += 16

    mostable = MosaicTable ()
    mostable.nx2, mostable.ny2 = (wh - 1) // 2
    mostable.radec = radec
    mostable.pbtype = telescopes
    mostable.rms = rms2
    if otf:
        mostable.radec2 = radec2
    return mostable


def readDataSet (dshandle):
    if dshandle.hasItem ('mostable'):
        h = dshandle.getItem ('mostable', 'r')
        mt = readItem (h)
        h.close ()
        return mt, []

    # Fake a one-entry table from the standard dataset items.

    w, warnings = dshandle.wcs ()
    mt = MosaicTable ()

    # crpix is 1-based
    csky = w.wcs_pix2sky (np.atleast_2d (w.wcs.crpix), 1)[0]
    ra = csky[w.wcs.lng] * np.pi / 180
    dec = csky[w.wcs.lat] * np.pi / 180
    mt.radec = np.asarray ([[ra, dec]], dtype=np.double)

    # The nx2 and ny2 values seem off by a few, but our
    # implementation at least agrees with MIRIAD.
    c = w.wcs.crpix[w.wcs.lng]
    n = dshandle.axes[w.wcs.lng]
    mt.nx2 = max (c - 1, n - c) + 1

    c = w.wcs.crpix[w.wcs.lat]
    n = dshandle.axes[w.wcs.lat]
    mt.ny2 = max (c - 1, n - c) + 1

    rms = dshandle.getScalarItem ('rms', 0)
    if rms <= 0:
        rms = 1. # should maybe just set mt.rms = None
    mt.rms = np.asarray ([[rms]], dtype=np.double)

    # This is a copy of pb.for:pbRead()

    pbtype = dshandle.getScalarItem ('pbtype')
    if pbtype is None:
        fwhm = dshandle.getScalarItem ('pbfwhm', -1)

        if fwhm == 0:
            pbtype = 'SINGLE'
        elif fwhm > 0:
            pbtype = 'GAUS(%f)' % fwhm
        else:
            pbtype = dshandle.getScalarItem ('telescop', ' ')

    mt.pbtype = [pbtype]
    return mt, warnings
