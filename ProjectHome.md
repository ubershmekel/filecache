"filecache" is a decorator that saves the return values of a decorated function to a file. The cache lives even after the interpreter restarts. For example a function which downloads stuff and does heavy duty parsing can benefit from this package.

Here's a usage example:

```
from filecache import filecache

# cache this function, return values invalidate after 24 hours
@filecache(24 * 60 * 60)
def time_consuming_function(args):
    # do the work

```

You'll notice filecache saves a file (shelf) with the same name as your python script and a '.cache' suffix. Feel free to erase the file if you want to clear the cache.

That's it! Have fun using filecache.