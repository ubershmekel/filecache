

import unittest
import imp
import time
import random
import os

import filecache


def erase_all_cache_files():
    shelve_suffixes = ('.cache', '.cache.bak', '.cache.dir', '.cache.dat')
    # os.listdir doesn't accept an empty string but dirname returns ''
    here = os.path.dirname(__file__) or '.'
    fname_list = os.listdir(here)

    for fname in fname_list:
        fpath = os.path.join(here, fname)
        # NOTE: test that path still exists because chained tests sometimes don't
        #       immediately erase things.
        if fname.endswith(shelve_suffixes) and os.path.exists(fpath):
            os.remove(fpath)


# NOTE: this comes so early so that the NotInnerClass's @filecache isn't erased from the disk
erase_all_cache_files()

class TestFilecache(unittest.TestCase):

    #@classmethod               
    #def setUpClass(self):
    #    self.erase_all_cache_files()
    
    #@classmethod                
    #def tearDownClass(self):
    #    self.erase_all_cache_files()
    
    def test_returns(self):
        # make sure the thing works
        @filecache.filecache(30)
        def donothing(x):
            return x

        params = [1, 'a', 'asdfa', set([1,2,3])]
        for item in params:
            self.assertEqual(donothing(item), item)
        
    def test_speeds(self):
        DELAY = 0.5
        @filecache.filecache(60)
        def waiter(x):
            time.sleep(DELAY)
            return x

        start = time.time()
        self.assertEqual(waiter(123), 123)
        self.assertEqual(waiter(123), 123)
        self.assertEqual(waiter(123), 123)
        self.assertEqual(waiter(123), 123)
        finish = time.time()

        # ran it 4 times but it should run faster than DELAY * 4
        self.assertLess(finish - start, (DELAY * 2))

    def test_invalidates(self):
        wait = 0.1
        items = [1337, 69]
        
        @filecache.filecache(wait)
        def popper():
            return items.pop()

        first = popper()
        # I would wait just for 'wait' exactly but time.time() isn't accurate enough.
        time.sleep(wait * 1.1)
        second = popper()
        
        self.assertNotEqual(first, second)

    def test_works_after_reload(self):
        import stub_for_test
        first = stub_for_test.the_time()
        # sleep a bit because time.time() == time.time()
        time.sleep(0.1)
        imp.reload(stub_for_test)
        second = stub_for_test.the_time()
        self.assertEqual(first, second)
    
    def test_interpreter_usage(self):
        '''
        This test is good for exec or interpreter usage of filecache.
        
        inspect.getfile(function) returned a bad filename for these cases.
        
        e.g. old exception:
        IOError: [Errno 22] Invalid argument: '<string>.cache.dat'
        '''
        d = {}
        exec('''from filecache import filecache\n@filecache(60)\ndef function(x): return x''',d ,d)
        first = d['function'](13)
        second = d['function'](13)
        self.assertEqual(first, second)
    
    def test_error_handling(self):
        
        temp = filecache._log_error
        try:
            passed_test = [False]
            def mock_logger(*args, **kwargs):
                passed_test[0] = True
            
            filecache._log_error = mock_logger
            
            def popper():
                return 'arbitrary obj here'
            
            # put anything in _db that you know will break filecache
            popper._db = 123
            
            popper = filecache.filecache(0.1, fail_silently=True)(popper)
            
            first = popper()
            
            self.assertTrue(passed_test[0])
        finally:
            filecache._log_error = temp

    # TODO: maybe make class methods work somehow, problem is methods rely on instance
    #       members so I'd have to serialize the class maybe. A bit complex.
    def AAA_test_class_methods(self):
        # won't work because class A isn't picklable
        class A:
            def __init__(self):
                self.number = 1
            
            @filecache.filecache(5.0)
            def donothing(self, x):
                self.number += x
                return self.number
        
        instance = NotInnerClass()
        first = instance.donothing(1)
        
        second = instance.donothing(1)
        self.assertEqual(first, second)

class NotInnerClass:
    def __init__(self):
        self.number = 1
    
    @filecache.filecache(5.0)
    def donothing(self, x):
        self.number += x
        return self.number


if __name__ == '__main__':
    unittest.main()
    erase_all_cache_files()

