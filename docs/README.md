
# pyrallex

[![PyPI](https://img.shields.io/pypi/v/pyrallex.svg)](https://pypi.python.org/pypi/pyrallex)
![CI](https://github.com/pyrallex/pyrallex/workflows/CI/badge.svg)
[![readthedocs](https://img.shields.io/badge/docs-stable-brightgreen.svg?style=flat)](https://pyrallex.readthedocs.io/en/stable/?badge=stable)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/pyrallex/pyrallex/branch/master/graph/badge.svg)](https://codecov.io/gh/pyrallex/pyrallex)


<img src="images/pyrallex-logo-512x512.png" width="30%" height="30%" alt="pyrallex python package logo" align="right">
Do you have many inherently parallel, independent computing jobs as they arise, e.g., in benchmarking of stochastic optimisation algorithms? Then *pyrallex* might be worth to consider.
*pyrallex* is a lightweight Python library for **managing and executing parameterisable, inherently parallel computing jobs**.

The typical workflow is as follows:

1. Create a **registry**. The registry is the core component of the library. It manages a collection of jobs and serves as the primary interface for interacting with them.
2. Populate the registry with jobs. Each job specifies the parameters required to execute a computational task that is completely independent of the other tasks.
3. Define a **runner**. A runner is a function that accepts an integer job identifier and a dictionary of parameters. It executes the corresponding job and returns the jobs output as a dictionary (it might also write more complex results directly into the jobs output directory).
4. Execute the jobs (in parallel) using either a built-in or custom runner backend (for example, on a multi-core local machine).
5. Monitor job progress from another Python process in read-only mode, including the number of running, completed, and failed jobs.
6. Collect and analyse the results. For benchmarking optimisation algorithms, the library provides built-in utilities for result aggregation.

## Key Features

* **Lightweight:** Focuses on the essential functionality without unnecessary complexity.
* **Extensible:** Supports multiple parallelisation backends. Currently, the library includes a simple sequential runner (no parallelelisation) and a multi-core implementation based on the [pyrallex library](https://pypi.org/project/pyrallex/). Additional backends can be easily implemented.

## Installation

The package is currently under development. At a later stage it will be available via [PyPI](https://pypi.org) (the *Python Package Index*). For the time being you can use the development version.
You need *conda* to get it running easily. On MACs I suggest to use [homebrew 🍺](https://brew.sh) to install *miniconda*
```bash
brew install --cask miniconda 
```

Once done you can proceed. First, clone the repository and navigate into the respective folder in your favourite terminal application. Once there type the following to install and activate the environment:
```bash
conda env create -f environment.yml
conda activate codebase
```

## Quickstart Example

The following code (see 'examples/demo-quickstart.py') is simplified with respect to the jobs internals to showcase the key components of the library. See 'examples/demo-advanced.py' for a more involved example.

```python
import random
import pandas as pd
import time

from pyrallex import Registry, JoblibRunnerBackend

if __name__ == "__main__":
    # Registry folder in the file system 
    path = "pyrallex-registry"

    # Build the registry
    reg = Registry(path = path, overwrite = True, backend = JoblibRunnerBackend(ncores = os.cpu_count() - 1))

    # Runner function.
    # Expects the job's ID and a dictionary of parameters.
    # Here there is only one integer parameter a (see below).
    # Note: jobid is not used here
    def my_runner(jobid, params):
        # Take a nap for some seconds to simulate expensive jobs
        time.sleep(random.randint(1, 2))
        return {'result': params["a"] + random.randint(0, 10)}

    # Add full factorial design (2 x 10 = 20)
    a = [10, 100]
    repl = list(range(1, 11)) # each 10 independent runs

    # Add full factorial design
    reg.add_jobs(a = a, repl = repl)
    print(reg)

    # Run all jobs
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
```

## Related work

The following R packages provide some methods to generate random graphs:

-   [batchtools](https://pypi.org/project/batchtools/) Python-based Command Line Tools to interact with AWS Batch.
-   [batchtools for R](https://github.com/mlr-org/batchtools): The popular package for the statistical programming language R provides a parallel implementation of Map for high performance computing systems managed by schedulers like Slurm, Sun Grid Engine, OpenLava, TORQUE/OpenPBS, Load Sharing Facility (LSF) or Docker Swarm

## Contact

Please address questions to the main author Jakob Bossek <j.bossek@gmail.com>.
