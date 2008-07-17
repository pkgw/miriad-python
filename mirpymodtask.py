#! /bin/sh
#mirpymodtask
#
# The above line is a code used by mirpyhelp.py to detect
# tasks that are implemented as modules. Keep it within the
# first 32 bytes of the file.
#
# This is a wrapper script for Miriad-Python tasks that are
# implemented as Python modules. (This is something you might
# want to do if you want the task to be directly callable from
# other Python code.)
#
# This wrapper should be used by creating a symlink to this file. The
# symlink should have the same name as the module (minus the .py
# extension) and be located in a directory in $PATH.
#
# This script basically runs "python -m modname args...". This syntax
# looks up the module "modname" in Python's module search path and
# runs it as a script. The module should have some code that looks like
#
# if __name__ == '__main__':
#    run as task
#
# that implements the module as a task. You need to protect the task
# code in this way because otherwise, it will be run unconditionally
# when the module is imported by other Python code, which is not
# desireable, or polite, behavior.

exec python -m `basename $0` "$@"
