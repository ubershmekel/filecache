Introduction
==============================================

"filecache" is a decorator that saves the return values of a decorated function to a file. The cache lives even after the interpreter restarts. For example a function which downloads stuff and does heavy duty parsing can benefit from this package. All you need to do is specify how long the return values should be cached (use seconds, like time.sleep).

Here's a usage example:

    from filecache import filecache

    # cache this function, return values invalidate after 24 hours
    @filecache(24 * 60 * 60)
    def time_consuming_function(args):
        # do the work

You'll notice filecache saves a file (shelf) with the same name as your python script and a '.cache' suffix. Feel free to erase the file if you want to clear the cache.

Installation
==============================================

From pip:

    pip install filecache

Manual install:

    python setup.py install


How it works
==============================================

Each time a decorated function is called, filecache checks in a shelve (which is named according to the module name that called filecache) to see if the arguments and function name have a recorded return value. If the recorded return value is still valid, it's returned, otherwise the original function is called and its return value is recorded with a timestamp.



Caveats
==============================================

 * All arguments of the decorated function and the return value need to be picklable for this to work.

 * The cache isn't automatically cleaned, it is only overwritten. If your function can receive many different arguments that rarely repeat, your cache may forever grow. One day I might add a feature that once in every 100 calls scans the db for outdated stuff and erases.

 * This is less useful on methods of a class because the instance (self) is cached, and if the instance isn't the same, the cache isn't used. This makes sense because class methods are affected by changes in whatever is attached to self.

 * Closures are problematic as well because different functions can have the same name.


Possible Future Plans
==============================================

 1. Add a cache cleaning function that's triggered in a smart way.
 2. Consider adding locks for multi-threaded or multi-process access. This might be tricky because shelve gives no multiple-user guarantees.
 3. Optimize a bit.
