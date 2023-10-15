# -*- coding: utf-8 -*-

import unittest
import datetime
import imp
import time
import random
import os
import typing

import filecache


def erase_all_cache_files() -> None:
    # Cache files are usually next to the code (__file__) except
    # for when it's an interpreter which just goes to wherever the
    # current process directory is.
    # Tests need to wipe them all clean, especially if both Py2 and Py3 are being tested.
    code_dir = os.path.abspath(os.path.dirname(__file__))
    process_dir = os.path.abspath('.')
    erase_dir_cache_files(code_dir)
    if code_dir != process_dir:
        erase_dir_cache_files(process_dir)


def erase_dir_cache_files(dir_path: str) -> None:
    shelve_suffixes = ('.cache', '.cache.bak', '.cache.dir', '.cache.dat')
    # os.listdir doesn't accept an empty string but dirname returns ''
    fname_list = os.listdir(dir_path)

    for fname in fname_list:
        fpath = os.path.join(dir_path, fname)
        # NOTE: test that path still exists because chained tests sometimes don't
        #       immediately erase things.
        if fname.endswith(shelve_suffixes) and os.path.exists(fpath):
            print("erasing {}".format(fpath))
            os.remove(fpath)


# NOTE: this comes so early so that the NotInnerClass's @filecache isn't erased from the disk
erase_all_cache_files()

T = typing.TypeVar('T')

class TestFilecache(unittest.TestCase):

    #@classmethod               
    #def setUpClass(self):
    #    self.erase_all_cache_files()
    
    #@classmethod                
    #def tearDownClass(self):
    #    self.erase_all_cache_files()
    
    def test_returns(self) -> None:
        # make sure the thing works
        @filecache.filecache(30)
        def donothing(x: T) -> T:
            return x

        params: list[object] = [1, 'a', 'asdfa', set([1,2,3])]
        for item in params:
            self.assertEqual(donothing(item), item)
        
    def test_speeds(self) -> None:
        DELAY: typing.Final[float] = 0.5

        @filecache.filecache(60)
        def waiter(x: int) -> int:
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

    def test_simple_decorate(self) -> None:
        ran_once: dict[str, int] = {}

        @filecache.filecache
        def whatever(x: int) -> int:
            if 'yes' in ran_once:
                return 12345
            else:
                ran_once['yes'] = 1
                return x

        self.assertEqual(whatever(2), 2)
        self.assertEqual(whatever(2), 2)

    def test_invalidates(self) -> None:
        wait: float = 0.1
        items: list[int] = [1337, 69]

        @filecache.filecache(wait)
        def popper() -> int:
            return items.pop()

        first: int = popper()
        # I would wait just for 'wait' exactly but time.time() isn't accurate enough.
        time.sleep(wait * 1.1)
        second: int = popper()
        
        self.assertNotEqual(first, second)

    def test_works_after_reload(self) -> None:
        from . import stub_for_test
        first = stub_for_test.the_time()
        # sleep a bit because time.time() == time.time()
        time.sleep(0.1)
        imp.reload(stub_for_test)
        second = stub_for_test.the_time()
        self.assertEqual(first, second)
    
    def test_interpreter_usage(self) -> None:
        '''
        This test is good for exec or interpreter usage of filecache.
        
        inspect.getfile(function) returned a bad filename for these cases.
        
        e.g. old exception:
        IOError: [Errno 22] Invalid argument: '<string>.cache.dat'
        '''
        d: dict[str, typing.Callable[[int], int]] = {}
        exec('''from filecache import filecache\n@filecache(60)\ndef function(x): return x''',d ,d)
        first = d['function'](13)
        second = d['function'](13)
        self.assertEqual(first, second)
    
    def test_error_handling(self) -> None:
        
        temp = filecache._log_error
        try:
            passed_test: list[bool] = [False]
            def mock_logger(*args, **kwargs):
                passed_test[0] = True
            
            filecache._log_error = mock_logger
            
            def popper() -> str:
                return 'arbitrary obj here'
            
            popper = filecache.filecache(0.1, fail_silently=True)(popper)

            # put anything in _db that you know will break filecache
            popper._db = 123  # type: ignore[assignment]
             
            first = popper()
            
            self.assertTrue(passed_test[0])
        finally:
            filecache._log_error = temp

    # TODO: maybe make class methods work somehow, problem is methods rely on instance
    #       members so I'd have to serialize the class maybe. A bit complex.
    def AAA_test_class_methods(self) -> None:
        # won't work because class A isn't picklable
        class A:
            number: int
            def __init__(self):
                self.number = 1
            
            @filecache.filecache
            def donothing(self, x: int) -> int:
                self.number += x
                return self.number
        
        instance = NotInnerClass()
        first = instance.donothing(1)
        
        second = instance.donothing(1)
        self.assertEqual(first, second)

    def test_utf_8_string(self) -> None:
        ran_once: dict[str, int] = {}

        @filecache.filecache
        def parse_pounds(x: str) -> str | int:
            if 'yes' in ran_once:
                return 12345
            else:
                ran_once['yes'] = 1
                return x

        self.assertEqual(parse_pounds("¼ pounds"), "¼ pounds")
        self.assertEqual(parse_pounds("¼ pounds"), "¼ pounds")
    
    
    def test_datetime_args(self) -> None:
        start = datetime.datetime.utcnow()

        @filecache.filecache(100)
        def go_back_an_hour(dt: datetime.datetime) -> datetime.datetime:
            return dt - datetime.timedelta(hours=1)

        new_time = go_back_an_hour(start)
        new_time_2 = go_back_an_hour(start)
        self.assertEqual(new_time, new_time_2)
        self.assertTrue(new_time < start, "Somehow datetime subtraction did not work")

class NotInnerClass:
    number: int
    def __init__(self) -> None:
        self.number = 1
    
    @filecache.filecache(5.0)
    def donothing(self, x: int) -> int:
        self.number += x
        return self.number


if __name__ == '__main__':
    unittest.main()
    erase_all_cache_files()

