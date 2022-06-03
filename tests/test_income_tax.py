import pytest
from src.easyfrenchtax import TaxInfoFlag
from .common import TaxTest, tax_testing

# NOTE: all tests value have been checked against the official french tax simulator:
# https://www3.impots.gouv.fr/simulateur/calcul_impot/2021/simplifie/index.htm

# TODO: split into several files
tax_tests = [
    TaxTest(name="basic", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000
            },
            results={
                "household_shares": 2,
                "net_taxes": 6912.0
            },
            flags={}),
    TaxTest(name="3_shares", year=2021,
            inputs={
                "married": True,
                "nb_children": 2,
                "salary_1_1AJ": 28000,
                "salary_2_1BJ": 35000
            },
            results={
                "household_shares": 3,
                "net_taxes": 2909.0
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "11%"
            }),
    TaxTest(name="family_quotient_capping", year=2021,
            inputs={
                "married": True,
                "nb_children": 2,
                "salary_1_1AJ": 35000,
                "salary_2_1BJ": 48000
            },
            results={
                "net_taxes": 7282.0
            },
            flags={
                TaxInfoFlag.FAMILY_QUOTIENT_CAPPING: "tax += 2392.44€",
                TaxInfoFlag.MARGINAL_TAX_RATE: "11%"
            }),
    TaxTest(name="fee_rebate_capping", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 130000
            },
            results={
                "net_taxes": 25916.0,
                "deduction_10p_2": 12652,
                "taxable_income": 126348
            },
            flags={
                TaxInfoFlag.FEE_REBATE_INCOME_2: "taxable income += 348€",
                TaxInfoFlag.MARGINAL_TAX_RATE: "30%"
            }),
]


@pytest.mark.parametrize("year,inputs,results,flags",
                         [pytest.param(t.year, t.inputs, t.results, t.flags) for t in tax_tests],
                         ids=[t.name for t in tax_tests])
def test_tax(year, inputs, results, flags):
    tax_testing(year, inputs, results, flags)
