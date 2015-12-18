#!/usr/bin/env python3
"""Helper utility for processing elements of an iterable collection in parallel, in a multithreaded fashion

Based on http://scipy.github.io/old-wiki/pages/Cookbook/Multithreading.html"
"""

import sys
import time
import threading
from itertools import count
from sortedcontainers import SortedDict
from multiprocessing import cpu_count

__maintainer__ = "Boris Capitanu"
__version__ = "1.0.0"


def parallel_for(f, l, *, threads=int(cpu_count()/2), return_=False, return_ordered=True):
    """Applies f to each element of l, in parallel over the specified number of threads

    :param f: The function to apply
    :param l: The iterable to process
    :param threads: The number of threads
    :param return_: True whether this is a 'map'-like operation that returns results
    :param return_ordered: True whether the order of the results should match the order of the iterable
    :return: Optionally returns the f(l) result, if return_=True
    """
    if threads > 1:
        iteratorlock = threading.Lock()
        exceptions = []
        if return_:
            if return_ordered:
                d = SortedDict()
                i = zip(count(), l.__iter__())
            else:
                d = list()
                i = l.__iter__()
        else:
            i = l.__iter__()

        def runall():
            while True:
                iteratorlock.acquire()
                try:
                    try:
                        if exceptions:
                            return
                        v = next(i)
                    finally:
                        iteratorlock.release()
                except StopIteration:
                    return
                try:
                    if return_:
                        if return_ordered:
                            n, x = v
                            d[n] = f(x)
                        else:
                            d.append(f(v))
                    else:
                        f(v)
                except:
                    e = sys.exc_info()
                    iteratorlock.acquire()
                    try:
                        exceptions.append(e)
                    finally:
                        iteratorlock.release()
        
        threadlist = [threading.Thread(target=runall) for j in range(threads)]
        for t in threadlist:
            t.start()
        for t in threadlist:
            t.join()
        if exceptions:
            a, b, c = exceptions[0]
            raise a(b).with_traceback(c)
        if return_:
            if return_ordered:
                return d.values()
            else:
                return d
    else:
        if return_:
            return [f(v) for v in l]
        else:
            for v in l:
                f(v)
            return


def parallel_map(f, l, *, threads=int(cpu_count()/2), ordered=True):
    """Applies f to each element of l, in parallel over the specified number of threads, and returns the result

    :param f: The function to apply
    :param l: The iterable to process
    :param threads: The number of threads
    :param ordered: True whether the order of the results should match the order of the iterable
    :return: The f(l) result
    """
    return parallel_for(f, l, threads=threads, return_=True, return_ordered=ordered)


if __name__ == '__main__':
    from random import randint

    def f(x):
        time.sleep(randint(0, 3))
        print(x)
        return x

    result = parallel_map(f, range(10), ordered=False)
    print(result)

    def g(x):
        time.sleep(0.5)
        print(x)
        raise ValueError(x)
        time.sleep(0.5)

    #foreach(g, range(10))
