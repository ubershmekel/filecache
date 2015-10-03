'''
filecache

filecache is a decorator which saves the return value of functions even
after the interpreter dies. For example this is useful on functions that download
and parse webpages. All you need to do is specify how long
the return values should be cached (use seconds, like time.sleep).

USAGE:

    from filecache import filecache

    @filecache(24 * 60 * 60)
    def time_consuming_function(args):
        # etc

    @filecache(filecache.YEAR)
    def another_function(args):
        # etc


NOTE: All arguments of the decorated function and the return value need to be
    picklable for this to work.

NOTE: The cache isn't automatically cleaned, it is only overwritten. If your
    function can receive many different arguments that rarely repeat, your
    cache may forever grow. One day I might add a feature that once in every
    100 calls scans the db for outdated stuff and erases.

NOTE: This is less useful on methods of a class because the instance (self)
    is cached, and if the instance isn't the same, the cache isn't used. This
    makes sense because class methods are affected by changes in whatever
    is attached to self.

Tested on python 2.7 and 3.1

License: BSD, do what you wish with this. Could be awesome to hear if you found
it useful and/or you have suggestions. ubershmekel at gmail


A trick to invalidate a single value:

    @filecache.filecache
    def somefunc(x, y, z):
        return x * y * z

    del somefunc._db[filecache._args_key(somefunc, (1,2,3), {})]
    # or just iterate of somefunc._db (it's a shelve, like a dict) to find the right key.


'''
cache_name_suffix = ''

import collections as _collections
import datetime as _datetime
import functools as _functools
import inspect as _inspect
import os as _os
try:
    # if dill is available: use it instead of stock pickle: this will allow to
    # pickle lambdas and several other objects
    # use different cache name for dill pickles
    import dill as _pickle
    cache_name_suffix += '-dill'
except ImportError:
    import pickle as _pickle
import shelve as _shelve
import sys as _sys
import time as _time
import traceback as _traceback
import types
import atexit


json = None

def json_default(obj):
    if hasattr(obj, 'for_json'):
        return obj.for_json()
    try:
        iterable = iter(obj)
    except TypeError:
        pass
    else:
        return list(obj)
    raise TypeError

try:
    import simplejson as json
except ImportError:
    pass

if not json:
    import json



_retval = _collections.namedtuple('_retval', 'timesig data')
_SRC_DIR = _os.path.dirname(_os.path.abspath(__file__))

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
YEAR = 365 * DAY
FOREVER = None

OPEN_DBS = dict()

if _sys.version_info[0] == 3:
    cache_name_suffix += '-3'

def _get_cache_name(function):
    """
    returns a name for the module's cache db.
    """
    module_name = _inspect.getfile(function)
    cache_name = '.' + module_name

    # fix for '<string>' or '<stdin>' in exec or interpreter usage.
    cache_name = cache_name.replace('<', '_lt_')
    cache_name = cache_name.replace('>', '_gt_')

    cache_name += '.cache'
    cache_name += cache_name_suffix
    return cache_name


def _log_error(error_str):
    try:
        error_log_fname = _os.path.join(_SRC_DIR, 'filecache.err.log')
        if _os.path.isfile(error_log_fname):
            fhand = open(error_log_fname, 'a')
        else:
            fhand = open(error_log_fname, 'w')
        fhand.write('[%s] %s\r\n' % (_datetime.datetime.now().isoformat(), error_str))
        fhand.close()
    except Exception:
        pass

def _args_key(function, args, kwargs):
    arguments = (args, kwargs)
    arguments_pickle = None
    try:
        # prefer to use json dumps as it always returns same strings (unlike
        # pickle.dumps())
        arguments_pickle = json.dumps(
            arguments,
            sort_keys=True,
            default=json_default,
        )
    except Exception:
        pass

    # Check if you have a valid, cached answer, and return it.
    # Sadly this is python version dependant
    if arguments_pickle is None:
        if _sys.version_info[0] == 2:
            arguments_pickle = _pickle.dumps(arguments)
        else:
            # NOTE: protocol=0 so it's ascii, this is crucial for py3k
            #       because shelve only works with proper strings.
            #       Otherwise, we'd get an exception because
            #       function.__name__ is str but dumps returns bytes.
            arguments_pickle = _pickle.dumps(arguments, protocol=0).decode('ascii', 'replace')

    key = function.__name__ + arguments_pickle
    return key

def filecache(seconds_of_validity=None, fail_silently=False, force_sync=True):
    '''
    filecache is called and the decorator should be returned.
    '''
    def filecache_decorator(function):
        @_functools.wraps(function)
        def function_with_cache(*args, **kwargs):
            try:
                key = _args_key(function, args, kwargs)

                if key in function._db:
                    rv = function._db[key]
                    if seconds_of_validity is None or _time.time() - rv.timesig < seconds_of_validity:
                        return rv.data
            except Exception:
                # in any case of failure, don't let filecache break the program
                error_str = _traceback.format_exc()
                _log_error(error_str)
                if not fail_silently:
                    raise

            retval = function(*args, **kwargs)

            # store in cache
            # NOTE: no need to _db.sync() because there was no mutation
            # NOTE: it's importatnt to do _db.sync() because otherwise the cache doesn't survive Ctrl-Break!
            try:
                function._db[key] = _retval(_time.time(), retval)
                if force_sync:
                    function._db.sync()
            except Exception:
                # in any case of failure, don't let filecache break the program
                error_str = _traceback.format_exc()
                _log_error(error_str)
                if not fail_silently:
                    raise

            return retval

        # make sure cache is loaded
        if not hasattr(function, '_db'):
            cache_name = _get_cache_name(function)
            if cache_name in OPEN_DBS:
                function._db = OPEN_DBS[cache_name]
            else:
                function._db = _shelve.open(cache_name)
                OPEN_DBS[cache_name] = function._db
                atexit.register(function._db.close)

            function_with_cache._db = function._db

        return function_with_cache

    if type(seconds_of_validity) == types.FunctionType:
        # support for when people use '@filecache.filecache' instead of '@filecache.filecache()'
        func = seconds_of_validity
        seconds_of_validity = None
        return filecache_decorator(func)

    return filecache_decorator



