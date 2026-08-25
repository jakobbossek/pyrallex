from pyrallex import Registry
from pyrallex import SequentialRunnerBackend, JoblibRunnerBackend

import os
import shutil
import random
import pandas as pd

# NOTE: if tests fail use pip install -e . to install the package in 'editable' mode

def test_registry():
    path = "pyrallex-unit-test"

    reg = Registry(path = path, overwrite = True, backend = SequentialRunnerBackend())

    # Runner function.
    # Expects the job's ID and a dictionary of parameters.
    # Here the parameters are the objective function "fun" (str) and the decision space dimension "n" (int).
    # Note: jobid is not used here
    def my_runner(jobid, params):
        if jobid == 1:
            raise Exception()
        return {'fx': random.randint(1, 10)}

    # Add full factorial design (2 x 3 x 10 = 60)
    fun = ["f1", "f2"]
    n = [10, 25, 50]
    repl = list(range(1, 11))

    njobs_expected = len(fun) * len(n) * len(repl)

    reg.add_jobs(fun = fun, n = n, repl = repl)
    assert reg.size() == njobs_expected
    assert (set(reg.get_initialised()) == set(list(range(1, njobs_expected + 1))))

    # Now exclude some jobs
    reg = Registry(path = path, overwrite = True, backend = SequentialRunnerBackend())

    njobs_expected = len(fun) * (len(n) - 1) * len(repl)

    reg.add_jobs(fun = fun, predicate = lambda params: params["n"] != 25, n = n, repl = repl)
    print(reg)
    assert reg.size() == njobs_expected
    assert (set(reg.get_initialised()) == set(list(range(1, njobs_expected + 1))))


    # Run all jobs and return a "simplified" single dictionary per job
    # including the jobid, the parameters and the results.
    res = reg.pyrallex(my_runner, jobids = [1, 4, 6, 10])
    df = reg.get_results(jobids = reg.get_done(), simplify = True)
    df = pd.DataFrame(df)
    assert df.shape[0] == 3 # rows

    # Note that job 1 failed by design
    assert set(reg.get_failed()) == set([1])
    assert set(reg.get_done()) == set([4, 6, 10])
    assert set(reg.get_done(jobids = [1, 4, 6])) == set([4, 6])

    # Reset a job
    reg.reset_jobs([6])
    assert set(reg.get_done()) == set([4, 10])

    # Cleanup
    shutil.rmtree(path)
    