`filecache` is a decorator which saves the return value of functions even after the interpreter dies. For example this is useful on functions that download
and parse webpages. You can specify how long the return values should be cached (use seconds, like time.sleep) or just cache forever. The cache is in a file right next to the calling `.py` file.

Install
----

    python setup.py install


Usage
----

    from filecache import filecache, YEAR

    @filecache(24 * 60 * 60)
    def time_consuming_function(args):
        # etc

    @filecache(YEAR)
    def another_function(args):
        # etc


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

* Note that pickling of the same arguments may result in different keys each
    time you run interpreter so cache may be not used. You can work around this
    problem by using json-serializable arguments. You can also defind `for_json`
    method for any class that is used as argument.

* You can install `dill` (`pip install dill`) to allow caching of functions that
    accept lambdas, generators and some other types. But cache keys of arguments
    may still change from run to run and so cache will miss

* Tested on python 2.7 and 3.3

* License: BSD, do what you wish with this. Could be awesome to hear if you found
it useful and/or you have suggestions. ubershmekel at gmail




Here's a trick to invalidate a single value:

    @filecache.filecache
    def somefunc(x, y, z):
        return x * y * z

    del somefunc._db[filecache._args_key(somefunc, (1,2,3), {})]
    # or just iterate of somefunc._db (it's a shelve, like a dict) to find the right key.

By default cache is saved to file on every change. You can avoid this to save
only on programm exit by using `@filecache.filecache(force_sync=False)`. But in
that case cache may be lost if program extits in unclean manner (with Ctrl-Break
or some exceptions)