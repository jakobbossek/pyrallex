import os
import shutil
import random
import itertools
from timeit import default_timer as timer

from collections.abc import Callable
from typing import Self

from pyrallex.Job import Job
from pyrallex.RunnerBackend import *

class Registry:
    """
    Registry for defining and executing computational jobs.

    Jobs can be registered with arbitrary parameters and subsequently
    executed using a configurable execution backend. The registry
    keeps track of completed and failed jobs and provides methods for
    inspecting their results.

    Args:
        path: Path to registry folder in the file system.
        overwrite: Shall the registry folder be overwriten if it already exists? Default is ``False``.
        readonly: Is the registry in read-only mode? In read-only mode jobs cannot be added anymore. Default is ``False``.
        backend: Instance of a runner backend. Default is an instance of the JoblibRunnerBackend.

    Attributes:
        path (str): Path to registry folder in the file system.
        overwrite (bool): Shall the registry folder be overwriten if it already exists?
        job_collection (list[Job]): List of Jobs. Note that the first element is a dummy (always ``None``) since jobs are numbered with natural numbers.
        njobs (int): Number of jobs.
        max_job_id (int): Highest sequential job number assigned so far.
        readonly (bool): Is the registry in read-only mode? In read-only mode jobs cannot be added anymore.
        design_path (str): path to experimental design file in the registry.
        backend (RunnerBackend): Instance of a runner backend. Default is an instance of the JoblibRunnerBackend.
    """
    def __init__(
            self,
            path: str,
            overwrite: bool = False,
            readonly: bool = False,
            backend: RunnerBackend | None = None
    ):
        self.path: str = path
        self.overwrite: bool = overwrite

        # List of jobs
        self.job_collection: list[Job] = [None] # dummy at position 0
        self.njobs: int = 0

        # Jobs are numbered sequentially starting with 1
        self.max_job_id: int = 1

        # Is the registry in read-only mode?
        self.readonly: bool = readonly

        # Path to design in registry
        self.design_path: str = os.path.join(path, "design.csv")

        # Parallelisation backend
        self.backend: RunnerBackend = backend if backend is not None else JoblibRunnerBackend()

        if os.path.exists(path) and os.path.isdir(path) and not overwrite:
            print(f"Path '{path}' already exists and overwrite = ``False``.")
            return

        if os.path.exists(path) and overwrite:
            shutil.rmtree(path, ignore_errors = False)
            print(f"Deleted registry dir: '{path}'")

        # create directory
        try:
            os.makedirs(path)
        except FileExistsError:
            print(f"One or more directories in '{path}' already exist.")
        except PermissionError:
            print(f"Permission denied: Unable to create '{path}'.")
        except Exception as e:
            print(f"An error occurred in initialiser: {e}")


    def set_backend(
            self,
            backend: RunnerBackend
    ) -> Self:
        """
        Set runner backend.

        Args:
            backend: Instance of a sub-class of 'RunnerBackend'.

        Returns:
            The callee itself (enables chaining).
        """
        self.backend = backend
        return self
        

    def reset_jobs(
            self,
            jobids: list[int]
    ) -> Self:
        """
        Resets jobs.

        I.e., all results will be deleted and the job status will be reset to 'initialised'.

        Args:
            jobids: A list of integer job IDs.
        
        Returns:
            The callee itself (enables chaining).
        """
        for jobid in jobids:
            self.get_job(jobid).reset()
        
        return self
    
    
    def tag(
            self,
            jobids: list[int],
            tags: list[str]) -> Self:
        """
        Append tags to jobs.

        Args:
            jobids: list of job IDs.
            tags: list of tags, i.e., simple strings.

        Returns:
            The callee itself (enables chaining).
        """
        for job in self.get_jobs(jobids):
            job.tag(tags)


    def add_jobs(
            self,
            predicate: Callable[[dict[str, any]], bool] = lambda _: True,
            **kwargs
    ) -> Self:
        """
        Adds jobs via a full factorial design by default.
        
        Optionally, arbitrary configurations can be excluded via a filter function.

        Args:
            **kwargs (dict[str, any]): dictionary of keyword arguments.
            predicate: Optional function that allows to ignore certain 
            parameter configurations. More precisely, the function is expected to receive a parameter combination as a ``dict[str, any]``
            and to return a Boolean: ``True`` if the parameter combination shall be kept and ``False`` if it is meant to be discarded.
            Default is to accept any configuration.

        Returns:
            The callee itself (enables chaining).
        """

        if self.readonly:
            print(f"Registry is in 'read-only' mode. Adding jobs is not possible.")
            return

        def to_dict(l):
            # TODO: aweful implementation
            d = {}
            for x in l:
                d[x[0]] = x[1]
            return d
        
        # Extract the parameter values
        param_values = list(kwargs.values())

        # Extract the parameter names
        param_names  = list(kwargs.keys())

        # Build the experimental design (a list(dict(param_name, param_value)))
        design = [to_dict(list(zip(param_names, x))) for x in itertools.product(*(param_values))]

        # Actually add the jobs
        for params in design:
            # skip if configuration does not meet requirements
            if not predicate(params):
                continue
            jobid = self.max_job_id
            self.job_collection.append(Job(jobid, self.path, params))
            self.max_job_id += 1
            self.njobs += 1
        
        # Store the design file
        self._write_design()

        return self


    def load_design(
            self,
            path: str,
            sep: str = ","
    ) -> Self:
        """
        Read setup parameters from a CSV file.

        The file-format expected is a Comma Separated Values (CSV) file. The first line is interpreted as the header line
        with the experimental parameter names.
        Each following line contains the parameter values for one experiment.

        Args:
            path: Path to the design file.
            sep: Seperator used in the CSV-file to separate columns. Default is ','.

        Returns:
            The callee itself (enables chaining).
        """

        if self.readonly:
            print(f"Registry is in 'read-only' mode. Loading design is not possible.")
            return

        try:
            with open(path, 'r') as f:
                # Read all rows
                rows = [x for _, x in enumerate(f)]

                # Explode by seperator
                rows = [row.strip("\n").split(sep) for row in rows]

                # The first rows entries are interpreted as the parameter names
                header = rows[0]

                design = rows[1:]
                for row in design:
                    # Sequential numbering
                    jobid = self.max_job_id

                    # Wrap parameter into a dictionary
                    params = dict(zip(header, row))

                    # Add job 
                    self.job_collection.append(Job(jobid, self.path, params))

                    # ... and ensure consistency
                    self.njobs += 1
                    self.max_job_id += 1

            # copy design to internals
            self._write_design()

        except FileNotFoundError:
            print(f"File '{path}' not found.")
        except PermissionError:
            print(f"Permission denied: Unable to read '{path}'.")
        except Exception as e:
            print(f"An error occurred: {e}")

        return self


    def size(self) -> int:
        """Return the number of jobs."""
        return self.njobs
    

    def _write_design(self) -> None:
        """Write the experimental design to a CSV file."""
        if self.njobs == 0:
            return
        
        with open(self.design_path, 'w') as f:
            param_names = ["jobid"] + self.job_collection[1].get_param_names()
            param_names_string = ",".join(param_names)
            f.write(param_names_string + "\n")

            for job in self.get_jobs():
                # Extract the job's parameter values
                param_values = list(job.get_params().values())
                jobid = job.get_id()

                # Put into one list
                row = [jobid] + param_values
                row = [str(x) for x in row]

                # Join
                row = ",".join(row)
                f.write(row + "\n")


    def _get_all_jobids(self) -> list[int]:
        """Return a list of all job IDs."""
        return list(range(1, self.njobs + 1))


    def _get_status(
            self,
            jobids: list[int] = None
    ) -> list[str]:
        """Return list of statuses of jobs."""
        if jobids is None:
            jobids = self._get_all_jobids()

        return [job.get_status() for job in self.get_jobs(jobids)]


    def _get_by_status(
            self,
            predicate: Callable[[Job], bool] = lambda _: True,
            jobids: list[int] = None
    ) -> list[int]:
        """
        Calculate job IDs of jobs by status.

        Note: if the registry is in 'read-only' mode we assume that it is run in a seperate process to monitor running jobs.
        Thus, in this case the jobs are accessed in the file system before.

        Args:
            predicate (Callable[[Job], bool]): A function that takes a Job object and returns a Boolean.
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.

        Returns:
            An integer list of job IDs.
        """
        if self.readonly:
            self.touch()

        filtered_jobids = [job.get_id() for job in self.get_jobs() if predicate(job)]
        if jobids is None:
            return filtered_jobids
        return list(set(filtered_jobids) & set(jobids))


    def get_failed(
            self,
            jobids: list[int] = None
    ) -> list[int]:
        """
        Calculate job IDs of failed jobs.

        Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.

        Returns:
            An integer list of job IDs.
        """
        return self._get_by_status(lambda job: job.is_failed(), jobids)


    def get_running(
            self,
            jobids: list[int] = None
    ) -> list[int]:
        """
        Calculate job IDs of running jobs.

        Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.

        Returns:
            An integer list of job IDs.
        """
        return self._get_by_status(lambda job: job.is_running(), jobids)


    def get_initialised(
            self,
            jobids: list[int] = None
    ) -> list[int]:
        """
        Calculate job IDs of initialised jobs.

        Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.

        Returns:
            An integer list of job IDs.
        """
        return self._get_by_status(lambda job: job.is_initialised(), jobids)
    

    def get_done(
            self,
            jobids: list[int] = None
    ) -> list[int]:
        """
        Calculate job IDs of done/finished jobs.

        Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.

        Returns:
            An integer list of job IDs.
        """
        return self._get_by_status(lambda job: job.is_done(), jobids)


    def get_jobs(
            self,
            jobids: list[int] = None,
            tags: list[str] = None
    ) -> list[Job]:
        """
        Return jobs.

        Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.
            tags: An optional list of tags. Defaults to no tags at all.

        Returns:
            A list of Job objects.
        """
        if jobids is None:
            jobids = self._get_all_jobids()
        if tags is None:
            tags = []
        return [self.job_collection[jobid] for jobid in jobids if self.job_collection[jobid].has_tags(tags)]


    def clear_logs(
            self,
            jobids: list[int] = None) -> Self:
        """
        Clears job logs.

        Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.
        
        Returns:
            The callee itself (enables chaining).
        """
        for job in self.get_jobs(jobids):
            job.clear_log()

    
    def show_logs(
            self,
            jobids: list[int] = None
    ) -> Self:
        """
        Display job logs to stdout.

        The function goes through all log files and prints the content to stdout as a side effect.

                Args:
            jobids: An optional list of job IDs. If ``None`` (the default) all job IDs are used.
        
        Returns:
            The callee itself (enables chaining).
        """
        for job in self.get_jobs(jobids):
            print(f"Log of job {job.get_id()}:")
            print(f"=====")
            print(job.get_log())


    def get_job(
            self,
            jobid: int
    ) -> Job:
        """
        Return the job with the respective job ID.

        Args:
            jobid: The ID of the job starting at 1 (not 0).

        Returns:
            The respective 'Job' object.
        """

        # Job-IDs are 1, 2, 3, ...
        return self.job_collection[jobid]


    def touch(self) -> Self:
        """
        Update job statuses.

        The function goes through re-loads all jobs from their pickle files.
        In particular the job status is loaded.
        
        Returns:
            The callee itself (enables chaining).
        """
        for job in self.get_jobs():
            job._load()
        
        return self


    def run(self,
            runner: Callable[[int, dict[any]], bool],
            jobids: list[int] | None = None,
            batchsize: int | None = None,
            shuffle: bool = True,
            rerun: bool = False
    ) -> tuple[int, dict[str, any], dict[str, any]]:
        """
        Run jobs in parallel.

        Args:
            runner: The actual runner function. It expects exactly two parameters:
            The integer job ID and a dictionary of algorithm parameters.
            jobids: Optional list of job IDs. If ``None`` (the default), all job IDs are used.
            batchsize: Size of job batches. If ``None`` (the default) the value is set via a heuristic as follows. The
            batch size is 3 * max{(number of cores - 1), 1}. The 'max' function asures that the value is non-zero on single-core machines.
            shuffle: Shall jobs be shuffled randomly prior to execution? Default is ``True``. Setting this value to ``True`` is
            beneficial if the jobs have very different running times.
            rerun: Shall already finished jobs be re-run? Default is ``False``, i.e., finished jobs are skipped.

        Returns:
            A list of 3-tuples (jobid, dictionary of parameters, dictionary of results).
        """
        # If no jobs are passed, assume that all jobs are meant
        if jobids is None:
            jobids = self._get_all_jobids()
        njobs = len(jobids)

        # Shuffle jobs
        if shuffle:
            random.shuffle(jobids)

        if batchsize is None:
            # ensure that on single-core systems the value is not zero
            ncores = max(os.cpu_count() - 1, 1)
            batchsize = (3 * ncores)
        
        batches = [jobids[i:i+batchsize] for i in range(0, njobs, batchsize)]


        def runner_wrapper(jobid):
            job = self.get_job(jobid)
            params = job.get_params()

            # Skip jobs if already finished
            if job.is_done() and not rerun:
                print(f"Skipping job #{jobid} (already finished).")

            time_passed = None
            try:
                start_time = timer()
                result = runner(jobid, params)
                end_time = timer()
                time_passed = start_time - end_time

                return ("done", result, time_passed)
            except Exception as e:
                print(f"Job #{jobid}: An error occured (see logs for details).")
                return ("failed", e, time_passed)
            
        for batch in batches:
            # Run using backend
            results = self.backend.run(runner_wrapper, batch)

            # NOTE: we need to do this here. Inside the wrapper we have no write-access to the jobs since they are executed in different processes
            for jobid, (status, value, time_passed) in zip(batch, results):
                job = self.job_collection[jobid]
                if status == "done":
                    job.set_done(time_passed).set_result(value)
                else:
                    job.set_failed().log(value)

        return self.get_results(jobids, filter_none = False) 


    def get_results(
            self,
            jobids: list[int],
            filter_none: bool = True,
            simplify: bool = False
    ) -> list[tuple[int, dict[str, any], dict[str, any]]] | list[dict[str, any]]:
        """
        Return job results.

        Args:
            jobids: List of integer job IDs, e.g., of finished jobs.
            filter_none: If ``True`` jobs that did not return anything are skipped. Default is ``True``.
            simplify: Should the result returned per job be simplified to a single dictionary? Default is ``False``.
        
        Returns:
            A list of 3-tuples (jobid, dictionary of parameters, dictionary of results) or a list of "merged" dictionaries if
            the argument simplify is set to ``True``.
        """

        # Filter "None" results or not
        predicate = lambda job: job.get_result()[2] is not None if filter_none else lambda _: True

        return [job.get_result(simplify) for job in self.get_jobs(jobids) if predicate(job)]


    def __str__(self) -> str:
        """
        Return informal readable string representation.

        Returns:
            Human-readbale string representation.
        """
        return (
            "PYRALLEX REGISTRY\n"
            f"Path: {self.path!r} ({"read-only" if self.readonly else "writable"})\n"
            f"Backend: {self.backend!r}\n\n"
            f"STATE OF JOBS\n"
            f"#total      : {self.size()}\n"
            f"#initialised: {len(self.get_initialised())}\n"
            f"#running    : {len(self.get_running())}\n"
            f"#done       : {len(self.get_done())}\n"
            f"#failed     : {len(self.get_failed())}"
        )
    
    
    def __repr__(self) -> str:
        """
        Return official string representation, which is aimed at programmers as they develop and maintain a program.

        Returns:
            Technical string representation.
        """
        class_name = type(self).__name__
        return f"Experiments.{class_name}(path={self.path!r}, read-only={str(self.readonly)!r}, #jobs={str(self.njobs)!r})"


    @staticmethod
    def load(
        path: str,
        readonly: bool = True
    ):
        """
        Load registry from file system.

        Args:
            path: Path to registry folder in the file system.
            readonly: Load in read-only mode? Default is ``True``.

        Returns:
            A registry object.
        """
        reg = Registry(path, overwrite = False, readonly = readonly)

        #  TODO: this is copy and paste
        exp_path = os.path.join(path, "design.csv")
        try:
            with open(exp_path, 'r') as f:
                # Read all rows
                rows = [x for _, x in enumerate(f)]
                
                # Split by separator
                rows = [row.strip("\n").split(',') for row in rows]

                # First line contains the 'jobid' + parameter names
                header = rows[0]

                design = rows[1:]
                for row in design:
                    jobid = int(row[0])
                    params = dict(zip(header, row))

                    reg.job_collection.append(Job(jobid, path, params))
                    reg.njobs += 1
                    reg.max_job_id += 1

            reg.touch()

        except FileNotFoundError:
            print(f"File '{path}' not found.")
        except PermissionError:
            print(f"Permission denied: Unable to read '{path}'.")
        except Exception as e:
            print(f"An error occurred: {e}")

        return reg
