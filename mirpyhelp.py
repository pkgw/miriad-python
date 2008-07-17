#! /usr/bin/env python
"""= mirpyhelp.py - Provide Miriad help with support for Python tasks.
& pkgw
: Tools
+

 This script pages documentation for standard Miriad tasks as well as
 Python tasks.

 Usage:
   mirpyhelp.py [name1] [name2] [...]

 If no names are specified, the documentation to mirpyhelp.py (this
 text) is printed.

 Each name is checked to see if it corresponds to a file in the
 standard Miriad documentation directories, $MIRPDOC and $MIRSDOC. If
 so, that documentation file is fed through the lowlevel "doc" command
 and paged (via the program named in $PAGER or "more" if $PAGER is
 unset). If "name" is not in one of those directories, the directories
 listed in $PATH are searched for a file with the specified name. If
 such a file exists, and it appears to be a Python file, a special
 Miriad docstring is read from the file, processed with the "doc"
 command, and paged as above.

 This process is repeated for each name on the commandline.

 This script can be used similarly to the script "mir.help" (which is
 usually known as "mirhelp"), but it is not an identical drop-in
 replacement. It is suggested that "mirhelp" be re-aliased to this
 script and that the true script name, "mir.help", be used if certain
 features found in that script are needed.
--
"""

import sys, os
from subprocess import Popen, PIPE
from os.path import join, exists
from tempfile import mkdtemp

def findExeFile (stem):
    exepath = os.environ['PATH'].split (os.pathsep)

    for d in exepath:
        full = join (d, stem)

        if exists (full): return d, full

    return None, None

def printKeywordDoc (keyword, dest):
    if 'MIRCAT' not in os.environ:
        print >>dest, ' [$MIRCAT not defined! Unable to look up'
        print >>dest, 'standard keyword documentation.]'
        return

    kwfile = join (os.environ['MIRCAT'], 'keywords.kdoc')

    if not exists (kwfile):
        print >>dest, ' [No standard keyword docfile %s]' % kwfile
        return

    match = '%N ' + keyword
    inKeyword = False
    
    for l in file (kwfile, 'r'):
        if inKeyword:
            if l.startswith ('%N'): break

            # I don't get the point of these lines in keywords.kdoc.
            if l[0] == '>': continue

            # normalize the indentation by stripping.
            print >>dest, '#', l.strip ()
        else:
            if l.startswith (match):
                print >>dest, '#@', keyword
                inKeyword = True

def printDocSection (name, full, dest):
    # We can't import the file as a module since that will execute
    # the task. (We don't want to have to write every task inside some big
    # function with "if __name__ == '__main__': doit ()" at the bottom of
    # the file.) So read the file ourselves and look for a
    # specially-formatted docstring.

    inString = False
    
    for line in file (full, 'r'):
        if not inString:
            if line.startswith ('"""='):
                inString = True
                # 'line' still has the trailing newline so use the
                # finishing comma with print
                print >>dest, '#' + line[3:], 
        else:
            if line.startswith ('"""'): break

            if line[0] != '<':
                # As above.
                print >>dest, '#' + line,
                continue

            # We have a standard-keyword line. 'doc' won't substitute
            # those for us because we're a -e file, so do it manually.
            keyword = line[1:].strip ()
            printKeywordDoc (keyword, dest)

    if not inString:
        print >>dest, """#= %s - Undocumented
#& Unknown
#: Unknown
#+
#
# No documentation string has been written for this task.
# This is a serious omission on the part of its author.
#
#--
""" % name

def showDoc (name, pdoc, sdoc):
    from glob import glob1

    hits = glob1 (pdoc, name + '.*') + glob1 (sdoc, name + '.*')

    if len (hits) > 1:
        print >>sys.stderr, 'Multiple matches for', name
        print >>sys.stderr, 'FIXME: add disambiguation.'
        return True

    if len (hits) == 1:
        isPython = False
        full = join (pdoc, hits[0])

        if not exists (full):
            full = join (sdoc, hits[0])
    else:
        dirname, full = findExeFile (name)

        if dirname is None:
            print >>sys.stderr, 'No matches for', name, 'and couldn\'t find it in $PATH.'
            print >>sys.stderr, '(Note that exact filename matches are required.)'
            return True

        fcheck = file (full, 'r')
        start = fcheck.read (32)

        if 'mirpymodtask' in start:
            # This script is a wrapper; look for a Python module
            # with the same name and use that for the docs.
            try:
                modobj = __import__ (name)
                full = modobj.__file__
            except Exception, e:
                print >>sys.stderr, 'Error: The task', name, 'seems to be a Python module'
                print >>sys.stderr, 'but I can\'t successfully load the module to get its'
                print >>sys.stderr, 'docs.'
                print >>sys.stderr, 'Exception:', e
                return True
        elif 'python' not in start:
            print >>sys.stderr, 'No standard entry for', name, 'and it doesn\'t appear'
            print >>sys.stderr, ' to be a Python file.'
            return True
        
        isPython = True

    tmpdir = tmpin = None

    try:
        # If python, we have the pipeline:
        #
        # [our extracted docstring] |doc [args] |$PAGER
        #
        # Fool 'doc' into printing out the right pathname for the task ...

        if isPython:
            tmpdir = mkdtemp ()
            tmpin = join (tmpdir, name)
            os.symlink ('/dev/stdin', tmpin)
                
        pager_cmd = os.environ.get ('PAGER') or 'more'
        pager = None
        
        try:
            pager = Popen (pager_cmd, stdin=PIPE,
                           shell=True, close_fds=True)

            try:
                doc = None
                
                if isPython:
                    doc_cmd = ['doc', '-e', '-o', dirname, tmpin]
                    doc = Popen (doc_cmd, stdin=PIPE,
                                 stdout=pager.stdin, shell=False,
                                 close_fds=True)

                    printDocSection (name, full, doc.stdin)
                else:
                    doc_cmd = ['doc', full]
                    doc = Popen (doc_cmd, stdin=file (os.devnull, 'r'),
                                 stdout=pager.stdin, shell=False,
                                 close_fds=True)
            finally:
                if doc is not None:
                    if isPython: doc.stdin.close ()
                    doc.wait ()
        finally:
            pager.stdin.close ()
            pager.wait ()
    finally:
        if tmpin is not None: os.unlink (tmpin)
        if tmpdir is not None: os.rmdir (tmpdir)

    return False

def cmdline (args):
    if 'MIRPDOC' not in os.environ:
        print >>sys.stderr, 'Error: Environment variable $MIRPDOC not defined.'
        print >>sys.stderr, 'Unable to look up documentation.'
        sys.exit (1)

    pdoc = os.environ['MIRPDOC']
    sdoc = os.environ['MIRSDOC']
    
    if len (args) == 1:
        failures = showDoc ('mirpyhelp.py', pdoc, sdoc)
    else:
        failures = False

        for arg in args[1:]:
            failures = failures or showDoc (arg, pdoc, sdoc)

    if failures: return 1

    return 0

if __name__ == '__main__':
    sys.exit (cmdline (sys.argv))

    
