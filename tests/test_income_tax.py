import pytest
from src.easyfrenchtax import TaxInfoFlag
from .common import TaxTest, tax_testing

# NOTE: all tests value have been checked against the official french tax simulator:
# https://www3.impots.gouv.fr/simulateur/calcul_impot/2021/simplifie/index.htm

tax_tests = [
    TaxTest(name="married", year=2021,
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
    TaxTest(name="married_2_children", year=2021,
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
    TaxTest(name="married_5_children", year=2022,
            inputs={
                "married": True,
                "nb_children": 5,
                "salary_1_1AJ": 50000,
                "salary_2_1BJ": 60000
            },
            results={
                "household_shares": 6,
                "net_taxes": 4808.0
            },
            flags={
            }),
    TaxTest(name="single", year=2022,
            inputs={
                "married": False,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
            },
            results={
                "household_shares": 1,
                "net_taxes": 2022.0
            },
            flags={}),
    TaxTest(name="single_1_child", year=2022,
            inputs={
                "married": False,
                "nb_children": 1,
                "salary_1_1AJ": 50000,
            },
            results={
                "household_shares": 1.5,
                "net_taxes": 5830.0
            },
            flags={}),
    TaxTest(name="single_5_children", year=2022,
            inputs={
                "married": False,
                "nb_children": 5,
                "salary_1_1AJ": 80000,
            },
            results={
                "household_shares": 5,
                "net_taxes": 2786.0
            },
            flags={}),
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


# ----- Useful for TDD phases, to isolate tests and debug -----
# tax_tests_debug = [
# ]
#
#
# @pytest.mark.parametrize("year,inputs,results,flags",
#                          [pytest.param(t.year, t.inputs, t.results, t.flags) for t in tax_tests_debug],
#                          ids=[t.name for t in tax_tests_debug])
# def test_tax_debug(year, inputs, results, flags):
#     tax_testing(year, inputs, results, flags, debug=True)
