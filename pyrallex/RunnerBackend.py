import os

from joblib import Parallel, delayed

from collections.abc import Callable

class RunnerBackend:
    """
    Backend used to execute computational jobs.

    Backends define how jobs registered in a :class:`Registry` are
    executed. Implementations may execute jobs sequentially, in
    separate processes, or using other parallelization mechanisms.
    """
    
    def run(self, runner: Callable[[int], any], jobids: list[int]):
        pass

    def __str__(self) -> str:
        """
        Return informal readable string representation.

        Returns:
            Human-readbale string representation.
        """
        return self.__repr__()

    def __repr__(self) -> str:
        """
        Return official string representation, which is aimed at programmers as they develop and maintain a program.

        Returns:
            Technical string representation.
        """
        class_name = type(self).__name__
        return f"Experiments.{class_name}()"

class SequentialRunnerBackend(RunnerBackend):
    """
    Plain sequential execution of jobs.
    """

    def __init__(self):
        """
        Initialise the backend.
        """
        super().__init__()

    def run(
            self,
            runner: Callable[[int], any],
            jobids: list[int]
    ) -> list[any]:
        """
        Run experiments in parallel.

        Args:
            runner (Callable[[int], any]): A function that expects a job ID and returns anything. As a side effect the function shall write to the job's output path.
            jobids (list[int]): List of job IDs to be executed.

        Returns:
            A list of whatever the 'runner' function returns.
        """
        return [runner(jobid) for jobid in jobids]

class JoblibRunnerBackend(RunnerBackend):
    """
    Parallelisation backend based on the pyrallex Python library.

    Attributes:
        ncores (int): Number of cores to use for parallelisation.
    """

    def __init__(
            self,
            ncores: int = os.cpu_count() - 1):
        """
        Initialise the pyrallex backend.

        Args:
            ncores (int): ncores (int): Number of cores to use for parallelisation. Defaults to one less than the available number of cores on your machine.

        """
        super().__init__()
        self.ncores: int = ncores


    def run(
            self,
            runner: Callable[[int], any],
            jobids: list[int]
    ) -> list[any]:
        """
        Run experiments in parallel.

        Args:
            runner (Callable[[int], any]): A function that expects a job ID and returns anything. As a side effect the function shall write to the job's output path.
            jobids (list[int]): List of job IDs to be executed.

        Returns:
            A list of whatever the 'runner' function returns.
        """
        return Parallel(n_jobs = self.ncores)(delayed(runner)(jobid) for jobid in jobids)
