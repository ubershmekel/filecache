`filecache` is a decorator which saves the return value of functions even after the interpreter dies. For example this is useful on functions that download
and parse webpages. You can specify how long the return values should be cached (use seconds, like time.sleep) or just cache forever. The cache is in a file right next to the calling `.py` file.

# Install

    pip install filecache
    
    # or for developing and debugging after cloning this package
    
    pip install -e .

# Usage

    from filecache import filecache

    @filecache(24 * 60 * 60)
    def time_consuming_function(args):
        # etc

    @filecache(filecache.YEAR)
    def another_function(args):
        # etc

# How it works

Each time a decorated function is called, filecache checks in a `shelve` [1] to see if the arguments and function name have a recorded return value. If the recorded return value is still valid, it's returned, otherwise the original function is called and its return value is recorded with a timestamp.


[1] A shelve is a dictionary in a file with string keys and `pickle` values. The shelve file is named according to the module name that called filecache.

# Caveats

* All arguments of the decorated function and the return value need to be
    picklable for this to work.

* The cache isn't automatically cleaned, it is only overwritten. If your
    function can receive many different arguments that rarely repeat, your
    cache may forever grow. One day I might add a feature that once in every
    100 calls scans the db for outdated stuff and erases.

* This is less useful on methods of a class because the instance (self)
    is cached, and if the instance isn't the same, the cache isn't used. This
    makes sense because class methods are affected by changes in whatever
    is attached to self.

* Tested on python 2.7, 3.3, 3.8

* License: BSD, do what you wish with this. Could be awesome to hear if you found
it useful and/or you have suggestions. ubershmekel at gmail


Here's a trick to invalidate a single value:

    @filecache.filecache
    def somefunc(x, y, z):
        return x * y * z

    del somefunc._db[filecache._args_key(somefunc, (1,2,3), {})]
    # or just iterate through `somefunc._db` (it's a shelve, which is like a dict) to find the right key.
