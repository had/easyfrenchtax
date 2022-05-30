from collections import namedtuple
from src.easyfrenchtax import TaxSimulator


TaxTest = namedtuple("TaxTest", ["name", "year", "inputs", "results", "flags"])
TaxExceptionTest = namedtuple("TaxExceptionTest", ["name", "year", "inputs", "message"])
