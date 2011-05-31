# Copyright 2009, 2010, 2011 Peter Williams
#
# This file is part of miriad-python.
#
# Miriad-python is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Miriad-python is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with miriad-python.  If not, see <http://www.gnu.org/licenses/>.

'''mirtask.keys - process task arguments in the MIRIAD style'''

from mirtask.lowlevel import MiriadError
import lowlevel as ll

class KeyHolder (object):
    """:synopsis: Methodless object that holds keyword data

This class is merely an empty subclass of :class:`object`. Instances
of it are created in and returned by
:meth:`mirtask.keys.KeySpec.process` for holding values of keyword
arguments to a task.
"""
    pass


def _get_unlimited (name, mget):
    # Get a potentially unlimited number of values for a keyword
    # using the function 'mget', which satisfies
    # 
    # mget (name, nmax) -> list of values (length <= nmax)

    allvals = []

    while True:
        newvals = mget (name, 100)
        if len (newvals) == 0:
            break
        allvals += newvals

    return allvals


def _mget (name, mget, nmax, format):
    """Get multiple values for a keyword using the function *mget*. If
*nmax* is None, a potentially unlimited number of values is returned;
otherwise at most *nmax* are. If *format* is not None, it is passed to
*mget* as an argument."""

    if format is None:
        if nmax is None:
            return _get_unlimited (name, mget)
        return mget (name, nmax)

    if nmax is None:
        return _get_unlimited (name,
                               lambda name, nmax: mget (name, nmax, format))

    return mget (name, nmax, format)


def _get_string (name, default):
    # MIRIAD parses commas in string-valued keywords: if I pass
    # keyword=val,with,comma to MIRIAD, keya() returns only "val".
    # This can be somewhat confusing, so in the case that a single
    # string value is requested, use mkeya to get every value (from
    # MIRIAD's point of view) and stitch them into a single string.
    vals = _get_unlimited (name, ll.mkeya)
    if len (vals) == 0:
        return default
    return ','.join (vals)


def _make_getters (coerce, useFormat, llget, llmget):
    if useFormat:
        def get (name, format, default):
            return llget (name, format, coerce (default))
        def mget (name, format, nmax):
            return _mget (name, llmget, nmax, format)
    else:
        def get (name, format, default):
            return llget (name, coerce (default))
        def mget (name, format, nmax):
            return _mget (name, llmget, nmax, None)

    return get, mget


_typeinfo = {
    # Mapping is (kind) -> (single-key-fetch-func, multi-key-fetch-func)
    'i': _make_getters (int, False, ll.keyi, ll.mkeyi),
    'd': _make_getters (float, False, ll.keyd, ll.mkeyd),
    'f': _make_getters (str, False, ll.keyf, ll.mkeyf),
    'a': _make_getters (str, False, _get_string, ll.mkeya),
    't': _make_getters (str, True, ll.keyt, ll.mkeyt),
}

_formatinfo = {
    # Mapping is (kind) -> (set of valid format values)
    't': set (('dms', 'hms', 'dtime', 'atime', 'time')),
}


def _check_misc (name, kind, format):
    if kind not in _typeinfo:
        raise ValueError ('Unknown type %s for keyword %s' % (kind, name))

    if kind not in _formatinfo:
        if format is not None:
            raise ValueError ('Format type %s not needed for keyword %s '
                              'of kind %s' % (format, name, kind))
    else:
        if format is None:
            raise ValueError ('Must specify format for keyword %s' % name)
        if format not in _formatinfo[kind]:
            raise ValueError ('Unknown format type %s for keyword %s' % \
                                  (format, name))


KT_SINGLE, KT_MULTI, KT_KEYMATCH, KT_CUSTOM = range (4)

class KeySpec (object):
    """:synopsis: Specifies the structure of keywords expected by a task.

A :class:`~KeySpec` object is used to specify the keywords accepted by
a task and then retrieve their values given a set of command-line
arguments. Its usage is outlined in the :ref:`module documentation
<pytaskskeys>`.
"""
    _uvdatFlags = None
    _uvdatCals = None
    _uvdatViskey = None

    def __init__ (self):
        self._keywords = {}
        self._options = set ()


    def keyword (self, name, kind, default, format=None):
        """Declare a single-valued keyword.

:arg name: the name of the keyword
:type name: :class:`str`
:arg kind: the kind of the keyword (see :ref:`keywordtypes`)
:type kind: a single character
:arg default: the default value of the keyword
:type default: any
:arg format: an optional format specifying how the keyword should be
             parsed (see :ref:`keywordformats`)
:type format: :const:`None` or :class:`str`
:rtype: :class:`KeySpec`
:returns: self

This function declares a single-valued keyword. If the user doesn't
specify the keyword, it will take on the value *default* (after an
attempt to coerce it to the correct type, which might raise an
exception).

If the keyword *kind* is "t", then the parse format *format* must be
specified.

If the keyword *kind* is "a" (character string), the MIRIAD subsystems
will consider the keyword to have multiple values if commas occur in
the string outside of parentheses. These semantics are overridden by
miriad-python such that such a string value appears to be a single
string. Thus::

  ks = keys.KeySpec ()
  ks.keyword ('demo', 'a', 'default')
  opts = ks.process (['demo=a(1,2),b,c,d'])
  print opts.demo

yields ``'a(1,2),b,c,d'``, whereas::

  ks = keys.KeySpec ()
  ks.mkeyword ('demo', 'a', 'default')
  opts = ks.process (['demo=a(1,2),b,c,d'])
  print opts.demo

yields ``['a(1,2)', 'b', 'c', 'd']``.

If the user specifies multiple values for the keyword on the
command-line, the keyword will take on the first value specified, and
a warning will be issued.

This function returns *self* for convenience in chaining calls.
"""
        if not isinstance (name, basestring):
            raise ValueError ('Keyword name "%s" must be a string' % name)
        _check_misc (name, kind, format)
        self._keywords[name] = (KT_SINGLE, kind, default, format)
        return self


    def mkeyword (self, name, kind, nmax, format=None):
        """Declare a multi-valued keyword.

:arg name: the name of the keyword
:type name: :class:`str`
:arg kind: the kind of the keyword (see :ref:`keywordtypes`)
:type kind: a single character
:arg nmax: the maximum number of different values that each keyword may take
:type nmax: :class:`int` or :const:`None`
:arg format: an optional format specifying how the keyword should be
             parsed (see :ref:`keywordformats`)
:type format: :const:`None` or :class:`str`
:rtype: :class:`KeySpec`
:returns: self

This function declares a multi-valued keyword. The value of the
keyword is a list of the values provided by the user, or an empty list
if the user doesn't specify any. If *nmax* is not :const:`None`, at
most *nmax* values will be returned; if the user specifies more, a
warning will be issued about the keyword not being fully consumed.

If the keyword *kind* is "t", then the parse format *format* must be
specified.

This function returns *self* for convenience in chaining calls.
"""
        if not isinstance (name, basestring):
            raise ValueError ('Keyword name "%s" must be a string' % name)
        _check_misc (name, kind, format)
        self._keywords[name] = (KT_MULTI, kind, nmax, format)
        return self


    def keymatch (self, name, nmax, allowed):
        """Declare a keyword with enumerated values.

:arg name: the name of the keyword
:type name: :class:`str`
:arg nmax: the maximum number of values to process
:type nmax: :class:`int`
:arg allowed: the allowed values of the keyword
:type allowed: an iterable of :class:`str`
:rtype: :class:`KeySpec`
:returns: self

This function declares a keyword that can take on one or more
enumerated, textual values. The user can abbreviate values to
uniqueness when specifying the keyword, and these abbreviations will
be expanded upon processing. If *nmax* is not :const:`None`, at most
*nmax* values will be returned; if the user specifies more, a warning
will be issues about the keyword not being fully consumed.

For example::

  ks = keys.KeySpec ()
  ks.keymatch ('demo', 3, ['phase', 'amplitude', 'real', 'imaginary'])
  opts = ks.process (['demo=am,re,ph,im'])
  print opts.demo

yields::

  ['amplitude', 'real', phase']

and a warning about the keyword not being fully consumed.

This function returns *self* for convenience in chaining calls.
"""
        if not isinstance (name, basestring):
            raise ValueError ('Keyword name "%s" must be a string' % name)
        self._keywords[name] = (KT_KEYMATCH, nmax, allowed)
        return self


    def custom (self, name, handler):
        """Declare a custom-handled keyword.

:arg name: the name of the keyword
:type name: :class:`str`
:arg handler: a function that returns the keyword's value
:type handler: callable
:rtype: :class:`KeySpec`
:returns: self

This function declares a keyword that will be specially handled. Upon
keyword processing, the callable *handler* will be called with one
argument, the *name* of the keyword. The keyword will take on whatever
value is returned by *handler*.

The intended usage is for *handler* to manually invoke the lowlevel
MIRIAD value-fetching routines found in :mod:`mirtask.lowlevel`, but
you can obtain a value however you like.

This function returns *self* for convenience in chaining calls.
"""
        if not isinstance (name, basestring):
            raise ValueError ('Keyword name "%s" must be a string' % name)
        if not callable (handler):
            raise ValueError ('handler must be callable')
        self._keywords[name] = (KT_CUSTOM, handler)
        return self


    def option (self, *names):
        """Declare one or more options to be handled.

:arg names: the names of the options to declare
:type names: tuple of :class:`str`
:rtype: :class:`KeySpec`
:returns: self

This function declares one or more of options that will be
handled. Each option takes on the value :const:`True` if it is
specified in the "options=" line by the user, and :const:`False`
otherwise. You can call this function multiple times.

This function returns *self* for convenience in chaining calls.
"""
        for name in names:
            self._options.add (str (name))
        return self


    def uvdat (self, flags, addCalOpts=True, viskey='vis'):
        """Declare that this task will make use of the UVDAT subsystem.

:arg flags: see below
:type flags: :class:`str`
:arg addCalOpts: whether the standard calibration options should be used
:type addCalOpts: :class:`bool`
:arg viskey: the keyword from which to take input dataset names
:type viskey: :class:`str`
:rtype: :class:`KeySpec`
:returns: self

Calling this functions indicates that the MIRIAD UVDAT subsystem should
be initialized when command-line arguments are processed. If this is done,
several keywords and options may be automatically processed by the UVDAT
subsystem to set up the subsequent reading of UV data.

The *flags* argument is a character string that controls optional
behavior of the UVDAT subsystem. Each feature in the subsystem is
identified with a character; if that character is present in *flags*,
the corresponding feature is enabled. Features that enable the
processing of certain keywords are:

==========      ==================
Character       Feature behavior
==========      ==================
*d*             Input data should be filtered via the standard
                "select" keyword.
*l*             Input spectral data should be processed via the
                standard "line" keyword.
*s*             Input data should be polarization-processed via
                the standard "stokes" keyword.
*r*             Input data should be divided by a reference 
                via the standard "ref" keyword.
==========      ==================

There are also features that control the format of the data returned
by the UVDAT routines:

==========      ==================
Character       Feature behavior
==========      ==================
*p*             Planet rotation and scaling corrections should be applied.
*w*             UVW coordinates should be returned in wavelength units, not
                nanoseconds. (Beware when writing these data to new UV 
                datasets, as the output routines expect the values to
                be in nanoseconds.)
*1*             (The character is the number one.) Average the data
                down to one channel.
*x*             The input data must be cross-correlations.
*a*             The input data must be autocorrelations.
*b*             The input must be exactly one UV dataset (not multiple).
*3*             The "preamble" returned while reading data will always have 5
                elements and include the *w* coordinate.
==========      ==================

If *addCalOpts* is :const:`True`, three options will be enabled: the
standard "nocal", "nopass", and "nopol". These control which kinds of
on-the-fly calibrations are applied to the data. (These options are
implemented by additional flags that may be passed to the
UVDAT initialization function, UVDATINP. See its documentation for
more information.) If *addCalOpts* is :const:`False`, no on-the-fly
calibrations will be applied, even if all of the necessary information
is present in the input data.

It is possible to specify which keyword is used to obtain the names of
the UV datasets that UVDAT will read. By MIRIAD convention this
keyword is "vis". The argument *viskey* allows you to override this
default, however.

Unless your task has unusual needs, it is recommended that you supply
at least the flags "dlsr" and leave *addCalOpts* as :const:`True` as
well as *viskey* as "vis".
"""
        self._uvdatFlags = flags
        self._uvdatCals = addCalOpts
        self._uvdatViskey = viskey

        if addCalOpts:
            self.option ('nocal', 'nopol', 'nopass')
        return self


    def process (self, args=None):
        """Process arguments and return their values.

:arg args: an optional array of argument values
:type args: iterable of :class:`str`
:rtype: :class:`KeyHolder`
:returns: data structure containing keyword values

This function processes the command-line arguments and returns an
object containing keyword and option values. If *args* is
:const:`None`, the command-line arguments contained in :data:`sys.argv`
are used; otherwise, *args* should be an array of :class:`str` to be
interpreted as the command-line arguments. The initial element of
*args* should be the first command-line parameter, *not* the name of
the executable. *I.e.*, to pass :data:`sys.argv` to this function
manually, the correct code is::

  ks.process (sys.argv[1:]) # correct but complicated
  ks.process (None) # same semantics

The return value is a :class:`KeyHolder` object with an attribute set
for each declared keyword and option; the value of each attribute
depends on the way in which it was declared. (See documentation of the
associated functions.)

If :meth:`KeySpec.uvdat` was called, the MIRIAD UVDAT subsystem is
also (re)initialized upon a call to this function using the parameters
set in the call to :meth:`KeySpec.uvdat`.

If an argument cannot be converted to its intended type, or the UVDAT
subsytem encounters an error initializing, :exc:`SystemExit`
will be raised. If there are unrecognized keywords or extra values
specified for a given keyword, a warning, *not* an error, will be
issued.
"""
        try:
            return self._process (args)
        except MiriadError, e:
            raise SystemExit ('Error: ' + str (e))


    def _process (self, args):
        from sys import argv

        if args is None:
            ll.keyini (argv)
        else:
            ll.keyini ([argv[0]] + list (args))

        res = KeyHolder ()

        for name, info in self._keywords.iteritems ():
            kt = info[0]

            if kt == KT_SINGLE:
                kind, default, format = info[1:]
                get, mget = _typeinfo[kind]
                val = get (name, format, default)
            elif kt == KT_MULTI:
                kind, nmax, format = info[1:]
                get, mget = _typeinfo[kind]
                val = mget (name, format, nmax)
            elif kt == KT_KEYMATCH:
                nmax, allowed = info[1:]
                val = ll.keymatch (name, allowed, nmax)
            elif kt == KT_CUSTOM:
                handler = info[1]
                val = handler (name)

            setattr (res, name, val)

        # Options. Must flatten the set() into an array
        # to be sure our indexing is well-defined.

        ml = 0
        names = []

        for name in self._options:
            ml = max (ml, len (name))
            names.append (name)

        optarr = []

        for name in names:
            optarr.append (name.ljust (ml, ' '))

        present = ll.options ('options', optarr)

        for i, name in enumerate (names):
            setattr (res, name, present[i] != 0)

        # UVDAT initialization. UVDATINP can potentially
        # raise a MiriadError if there are argument problems.

        if self._uvdatFlags is not None:
            f = self._uvdatFlags

            if self._uvdatCals:
                if not res.nocal:
                    f += 'c'
                if not res.nopass:
                    f += 'f'
                if not res.nopol:
                    f += 'e'

            ll.uvdatinp (self._uvdatViskey, f)

        # All done. Check for any unexhausted keywords.

        ll.keyfin ()
        return res


__all__ = ['KeySpec']
