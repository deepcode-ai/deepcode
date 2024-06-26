import time
import logging
import psutil
import torch


def print_rank_0(message):
    if torch.distributed.is_initialized():
        if torch.distributed.get_rank() == 0:
            print(message, flush=True)
    else:
        print(message, flush=True)


class SynchronizedWallClockTimer:
    """Group of timers. Borrowed from Nvidia Megatron code"""
    class Timer:
        """Timer."""
        def __init__(self, name):
            self.name_ = name
            self.elapsed_ = 0.0
            self.started_ = False
            self.start_time = time.time()

        def start(self):
            """Start the timer."""
            assert not self.started_, 'timer has already been started'
            torch.cuda.synchronize()
            self.start_time = time.time()
            self.started_ = True

        def stop(self):
            """Stop the timer."""
            assert self.started_, 'timer is not started'
            torch.cuda.synchronize()
            self.elapsed_ += (time.time() - self.start_time)
            self.started_ = False

        def reset(self):
            """Reset timer."""
            self.elapsed_ = 0.0
            self.started_ = False

        def elapsed(self, reset=True):
            """Calculate the elapsed time."""
            started_ = self.started_
            # If the timing in progress, end it first.
            if self.started_:
                self.stop()
            # Get the elapsed time.
            elapsed_ = self.elapsed_
            # Reset the elapsed time
            if reset:
                self.reset()
            # If timing was in progress, set it back.
            if started_:
                self.start()
            return elapsed_

    def __init__(self):
        self.timers = {}

    def __call__(self, name):
        if name not in self.timers:
            self.timers[name] = self.Timer(name)
        return self.timers[name]

    def log(self, names, normalizer=1.0, reset=True):
        """Log a group of timers."""
        assert normalizer > 0.0
        string = 'time (ms)'
        for name in names:
            elapsed_time = self.timers[name].elapsed(reset=reset) * 1000.0 / normalizer
            string += ' | {}: {:.2f}'.format(name, elapsed_time)
        print_rank_0(string)


class ThroughputTimer():
    def __init__(self,
                 batch_size,
                 num_workers,
                 start_step=2,
                 steps_per_output=50,
                 monitor_memory=True,
                 logging_fn=None):
        self.start_time = 0
        self.end_time = 0
        self.started = False
        self.batch_size = batch_size
        if batch_size is None:
            self.batch_size = 1
        self.num_workers = num_workers
        self.start_step = start_step
        self.epoch_count = 0
        self.local_step_count = 0
        self.total_step_count = 0
        self.total_elapsed_time = 0
        self.steps_per_output = steps_per_output
        self.monitor_memory = monitor_memory
        self.logging = logging_fn
        if self.logging is None:
            self.logging = logging.info
        self.initialized = False

    def update_epoch_count(self):
        self.epoch_count += 1
        self.local_step_count = 0

    def _init_timer(self):
        self.initialized = True

    def start(self):
        self._init_timer()
        self.started = True
        if self.total_step_count >= self.start_step:
            torch.cuda.synchronize()
            self.start_time = time.time()

    def stop(self, report_speed=True):
        if not self.started:
            return
        self.started = False
        self.total_step_count += 1
        self.local_step_count += 1
        if self.total_step_count > self.start_step:
            torch.cuda.synchronize()
            self.end_time = time.time()
            duration = self.end_time - self.start_time
            self.total_elapsed_time += duration
            if self.local_step_count % self.steps_per_output == 0:
                if report_speed:
                    self.logging("{}/{}, SamplesPerSec={}".format(
                        self.epoch_count,
                        self.local_step_count,
                        self.avg_samples_per_sec()))
                if self.monitor_memory:
                    virt_mem = psutil.virtual_memory()
                    swap = psutil.swap_memory()
                    self.logging("{}/{}, vm percent: {}, swap percent: {}".format(
                        self.epoch_count,
                        self.local_step_count,
                        virt_mem.percent,
                        swap.percent))

    def avg_samples_per_sec(self):
        if self.total_step_count > 0:
            samples_per_step = self.batch_size * self.num_workers
            total_step_offset = self.total_step_count - self.start_step
            avg_time_per_step = self.total_elapsed_time / total_step_offset
            # training samples per second
            return samples_per_step / avg_time_per_step
        return float("-inf")
