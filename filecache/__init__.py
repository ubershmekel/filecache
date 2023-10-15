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


import collections as _collections
import datetime as _datetime
import functools as _functools
import inspect as _inspect
import os as _os
import pickle as _pickle
import codecs as _codecs
import shelve as _shelve
import sys as _sys
import time as _time
import traceback as _traceback
import typing
import atexit

P = typing.ParamSpec('P')
T = typing.TypeVar('T')
R = typing.TypeVar('R')
C = typing.TypeVar('C', bound=typing.Callable[..., typing.Any])

class _retval(typing.NamedTuple, typing.Generic[T]):
    timesig: float
    data: T

_SRC_DIR: typing.Final[str] = _os.path.dirname(_os.path.abspath(__file__))

SECOND: typing.Final[int] = 1
MINUTE: typing.Final[int] = 60 * SECOND
HOUR: typing.Final[int] = 60 * MINUTE
DAY: typing.Final[int] = 24 * HOUR
WEEK: typing.Final[int] = 7 * DAY
MONTH: typing.Final[int] = 30 * DAY
YEAR: typing.Final[int] = 365 * DAY
FOREVER: typing.Final[typing.Literal[None]] = None

OPEN_DBS: typing.Final[dict[str, _shelve.Shelf]] = dict()

def _get_cache_name(function: typing.Callable[..., typing.Any]) -> str:
    """
    returns a name for the module's cache db.
    """
    module_name = _inspect.getfile(function)
    cache_name = module_name

    # fix for '<string>' or '<stdin>' in exec or interpreter usage.
    cache_name = cache_name.replace('<', '_lt_')
    cache_name = cache_name.replace('>', '_gt_')
    
    cache_name += '.cache'
    return cache_name


def _log_error(error_str: str) -> None:
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

def _args_key(function: typing.Callable[P, typing.Any], args: P.args, kwargs: P.kwargs) -> str:
    arguments = (args, kwargs)
    # Check if you have a valid, cached answer, and return it.
    # Sadly this is python version dependant
    arguments_pickle: str
    if _sys.version_info[0] == 2:
        arguments_pickle = typing.cast(str, _pickle.dumps(arguments))
    else:
        # NOTE: protocol=0 so it's ascii, this is crucial for py3k
        #       because shelve only works with proper strings.
        #       Otherwise, we'd get an exception because
        #       function.__name__ is str but dumps returns bytes.
        arguments_pickle = _codecs.encode(_pickle.dumps(arguments, protocol=0), "base64").decode()

    key = function.__name__ + arguments_pickle
    return key


class FileCacheCallable(typing.Protocol[C]):
    """
    `Protocol` of a file cache wrapping a callable.
    """
    _db: _shelve.Shelf
    __wrapped__: C
    __call__: C
    __name__: str

    @typing.overload
    def __get__(
        self: 'FileCacheCallable[C]',
        instance: None,
        owner: type | None = ...,
    ) -> 'FileCacheCallable[C]': ...

    @typing.overload
    def __get__(
        self: 'FileCacheCallable[typing.Callable[..., R]]',
        instance: object,
        owner: type | None = ...,
    ) -> 'FileCacheBoundCallable[typing.Callable[..., R]]': ...


class FileCacheBoundCallable(FileCacheCallable[C]):
    """
    A `FileCacheCallable` that is bound like a method.
    """
    __self__: object
    __call__: C

    def __init__(self, call: FileCacheCallable[C], __self__: object):
        self._call = call
        self.__self__ = __self__
        self.__wrapped__ = call.__wrapped__
        self._db = call._db
        self.__name__ = call.__name__

    def __get__(
        self: 'FileCacheBoundCallable[C]',
        instance: typing.Any,
        owner: type | None = None,
    ) -> 'FileCacheBoundCallable[C]':
        result = self._call.__get__(instance, owner)
        return typing.cast(FileCacheBoundCallable[C], result)

    def __call__(self, *args, **kwargs): # type: ignore
        return self._call(self.__self__, *args, **kwargs)

    def __func__(self) -> FileCacheCallable[C]:
        return self._call


@typing.overload
def filecache(arg0: C) -> FileCacheCallable[C]: ...

@typing.overload
def filecache(
    arg0: int | float | None = None,
    fail_silently: bool = False,
) -> typing.Callable[[C], FileCacheCallable[C]]: ...


def filecache(
    arg0: C | int | float | None = None,
    fail_silently: bool = False,
) -> FileCacheCallable[C] | typing.Callable[[C], FileCacheCallable[C]]:
    '''
    filecache is called and the decorator should be returned.
    '''
    if arg0 is None or isinstance(arg0, (int, float)):
        def filecache_decorator(call: C) -> FileCacheCallable[C]:
            return CachedFileCacheCallable(
                call,
                seconds_of_validity=arg0,
                fail_silently=fail_silently,
            )

        # support for when people use '@filecache.filecache' instead of '@filecache.filecache()'
        return filecache_decorator

    else:
        fast_wrapper = CachedFileCacheCallable(
            arg0,
            seconds_of_validity=None,
            fail_silently=fail_silently,
        )
        return _functools.update_wrapper(fast_wrapper, arg0)


class CachedFileCacheCallable(FileCacheCallable[C]):
    __wrapped__: C
    _db: _shelve.Shelf
    _seconds_of_validity: int | float | None
    _fail_silently: bool

    def __init__(self, call: C, seconds_of_validity: int | float | None = None, fail_silently: bool = False):
        self.__wrapped__ = call
        self.__name__ = call.__name__

        cache_name: str = _get_cache_name(call)
        db: _shelve.Shelf
        if cache_name in OPEN_DBS:
            db = OPEN_DBS[cache_name]
        else:
            db = _shelve.open(cache_name)
            OPEN_DBS[cache_name] = db
            atexit.register(db.close)

        self._db = db
        self._seconds_of_validity = seconds_of_validity
        self._fail_silently = fail_silently

    def __get__(self, instance: object, owner: type | None = None) -> FileCacheCallable[C]:
        if instance is None:
            return self
        return FileCacheBoundCallable(self, instance)

    def __call__(self, *args, **kwargs) -> None: # type: ignore
        try:
            key: str = _args_key(self.__wrapped__, args, kwargs)

            if key in self._db:
                rv = self._db[key]
                seconds_of_validity = self._seconds_of_validity
                if seconds_of_validity is None or _time.time() - rv.timesig < seconds_of_validity:
                    return rv.data

        except Exception:
            # in any case of failure, don't let filecache break the program
            error_str = _traceback.format_exc()
            _log_error(error_str)
            fail_silently = self._fail_silently
            if not fail_silently:
                raise
        
        retval = self.__wrapped__(*args, **kwargs)

        # store in cache
        # NOTE: no need to _db.sync() because there was no mutation
        # NOTE: it's importatnt to do _db.sync() because otherwise the cache doesn't survive Ctrl-Break!
        try:
            self._db[key] = _retval(_time.time(), retval)
            self._db.sync()
        except Exception:
            # in any case of failure, don't let filecache break the program
            error_str = _traceback.format_exc()
            _log_error(error_str)
            if not fail_silently:
                raise

        return retval
