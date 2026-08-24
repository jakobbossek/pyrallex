import random
import pandas as pd
import time
import os

from pyrallex import Registry, JoblibRunnerBackend

if __name__ == "__main__":
    # Registry folder in the file system 
    path = "pyrallex-registry"

    # Build the registry
    reg = Registry(path = path, overwrite = True, backend = JoblibRunnerBackend(ncores = os.cpu_count() - 1))

    # Runner function.
    # Expects the job's ID and a dictionary of parameters.
    # Here there is only one integer parameter a.
    # Note: jobid is not used here
    def my_runner(jobid, params):
        # Take a nap for some seconds to simulate expensive jobs
        time.sleep(random.randint(1, 2))
        return {'result': params["a"] + random.randint(0, 10)}

    # Add full factorial design (2 x 10 = 20)
    a = [10, 100]
    repl = list(range(1, 11))

    # Add full factorial design
    reg.add_jobs(a = a, repl = repl)
    print(reg)

    # Run all jobs (this takes some seconds)
    reg.run(my_runner, batchsize = 10)

    # Get information on the status
    print(reg.get_failed())
    print(reg.get_done())

    # Collect results in a list of 3-tuples (jobid, dict of parameters, dict of results)
    res = reg.get_results(jobids = reg.get_done())
    
    # Collect results in a list of dicts ...
    res = reg.get_results(jobids = reg.get_done(), simplify = True)
    
    # ... which can be easily transformed into a pandas data frame
    print(pd.DataFrame(res).to_string())
