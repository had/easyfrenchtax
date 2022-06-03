from collections import namedtuple
from src.easyfrenchtax import TaxSimulator
import pytest


TaxTest = namedtuple("TaxTest", ["name", "year", "inputs", "results", "flags"])
TaxExceptionTest = namedtuple("TaxExceptionTest", ["name", "year", "inputs", "message"])

def tax_testing(year, inputs, results, flags):
    tax_sim = TaxSimulator(year, inputs)
    tax_result = tax_sim.state
    tax_flags = tax_sim.flags
    for k, res in results.items():
        assert tax_result[k] == res
    for k, f in flags.items():
        assert tax_flags[k] == f
