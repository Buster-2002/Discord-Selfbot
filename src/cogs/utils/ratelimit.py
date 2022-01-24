# -*- coding: utf-8 -*-
'''Based on https://github.com/tomasbasham/ratelimit/blob/18d5f3382724a8ae2d4f066a1bd51c74d5ae1524/ratelimit/decorators.py
'''
import sys
import time
from math import floor


def now():
    if hasattr(time, 'monotonic'):
        return time.monotonic
    return time.time


class RateLimit:
    def __init__(self, calls: int, period: int, clock=now()):
        self.clamped_calls: int = max(1, min(sys.maxsize, floor(calls)))
        self.calls = calls
        self.period = period
        self.clock = clock
        self.last_reset: float = clock()
        self.num_calls: int = 0

    def is_ratelimited(self) -> bool:
        period_remaining = self._get_period_remaining()
        if period_remaining <= 0:
            self.num_calls = 0
            self.last_reset = self.clock()

        self.num_calls += 1
        if self.num_calls > self.clamped_calls:
            return True
        return False

    def _get_period_remaining(self) -> float:
        elapsed = self.clock() - self.last_reset
        return self.period -  elapsed
