import random
import pandas as pd
import os

from pyrallex import Registry, JoblibRunnerBackend

# BENCHMARKING STUDY
# ===
#
# In this example we run a simple (1+1) Evolutionary Algorithm (EA)
# on two classic pseudo-Boolean test functions OneMax and LeadingOnes.
# The (1+1) EA is a very simple evolutionary algorithm, i.e., a stochastic
# optimiser.
# 
# The (1+1) EA is run each 100 times independently for problem dimensions
# n = 10, 25, 50 until the optimum (the all ones string) is found.
#
# Results are collect in a pandas data frame.
#

def OneMax(x: list[int]) -> int:
    """
    Pseudo-Boolean function OneMax.

    The value of onemax is the number of ones in the input.

    Args:
        x [list[int]]: A list of zeros and ones.
    
    Returns:
        The function value.
    """
    return sum(x)

# Pseudo-Boolean function LeadingOnes
def LeadingOnes(x: list[int]) -> int:
    """
    Pseudo-Boolean function LeadingOnes.

    The value of LeadingOnes is the number of ones until the first zero occurs.

    Args:
        x [list[int]]: A list of zeros and ones.
    
    Returns:
        The function value.
    """
    los = 0
    for i in x:
        if i == 0:
            return los
        los += 1
    return los

def mutate(x: list[int], p: float = None) -> list[int]:
    """
    Bit-wise mutation.

    Args:
        x [list[int]]: The parent bit-string.
        p [float]: Probability to flip each bit of x. Default is 1/len(x).
    
    Returns:
        A mutation version of x.
    """
    if not p:
        p = 1 / len(x)
    y = x[:]
    for i in range(len(x)):
        if random.random() < p:
            y[i] = 1 - y[i]
    return y

def ea(fun, n: int, opt: int, maxevals: int) -> dict[str, any]:
    """
    Implements the (1+1) Evolutionary Algorithm (EA).

    The (1+1) EA is a very well studied basic algorithm in the field of evolutionary optimisation.
    On pseudo-Boolean functions it works as follows. It first initialises a random bit-string.
    Next, it makes a copy of x termed y. This child y undergoes bit-wise mutation. If y is no worse
    than x with respect to the objective function value, y replaces x. Otherwise y is discared.
    This process is repeated until a termination criterion is reached.
    In this implementation the algorithm terminates either if the optimum of the function is reached
    (the all-ones string for both OneMax and LeadingOnes) or a maximum number of function evaluations
    was performed.

    Args:
        fun [Callable]: The objective function.
        n [int]: The decision space dimension.
        opt [int]: The optimal objective function value (termination criterion).
        maxevals [int]: Maximum number of objective function evaluations (termination criterion).
    """
    # Create initial inidividual
    x: list[int] = [random.randint(0, 1) for _ in range(n)]

    # Calculate its objective function value
    fx: int = fun(x)
    nevals: int = 1

    # Evolutionary loop
    while (nevals <= maxevals and (fx != n)):
        y = mutate(x)
        fy = fun(y)
        # Replace x with y if y is no worse
        if fy >= fx:
            x, fx = y, fy
        nevals += 1
    
    # Finish
    return {'fx': fx, 'OPT': fx == n, 'nevals': nevals}


if __name__ == "__main__":
    # Registry folder in the file system 
    path = "pyrallex-registry"

    # Build the registry
    reg = Registry(path = path, overwrite = True, backend = JoblibRunnerBackend(ncores = os.cpu_count() - 1))

    # Runner function.
    # Expects the job's ID and a dictionary of parameters.
    # Here the parameters are the objective function "fun" (str) and the decision space dimension "n" (int).
    # Note: jobid is not used here
    def my_runner(jobid, params):
        # Determine the target function
        fun = OneMax if (params["fun"] == "onemax") else LeadingOnes
        n = int(params["n"])
        return ea(fun, n = n, opt = n, maxevals = 3 * n * n)


    # Add full factorial design (2 x 3 x 100 = 60)
    fun = ["onemax", "leadingones"]
    n = [10, 25, 50]
    repl = list(range(1, 101))

    reg.add_jobs(fun = fun, n = n, repl = repl)
    print(reg)

    # Run all jobs
    reg.pyrallex(my_runner, batchsize = 25)

    # Get status information
    print(reg.get_failed())
    print(reg.get_done())

    # Collect results in a list of 3-tuples (jobid, dict of parameter, dict of results)
    res = reg.get_results(jobids = reg.get_done())
    
    # Collect results in a list of dictionaries ...
    res = reg.get_results(jobids = reg.get_done(), simplify = True)
    # ... which can be easily transformed into a pandas data frame
    print(pd.DataFrame(res).to_string())
