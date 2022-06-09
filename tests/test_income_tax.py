import pytest
from src.easyfrenchtax import TaxInfoFlag, TaxField
from .common import TaxTest, tax_testing

# NOTE: all tests value have been checked against the official french tax simulator:
# https://www3.impots.gouv.fr/simulateur/calcul_impot/2021/simplifie/index.htm

tax_tests = [
    TaxTest(name="married", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 2,
                TaxField.NET_TAXES: 6912.0,
            },
            flags={}),
    TaxTest(name="married_2_children", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 2,
                TaxField.SALARY_1_1AJ: 28000,
                TaxField.SALARY_2_1BJ: 35000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 3,
                TaxField.NET_TAXES: 2909.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "11%"
            }),
    TaxTest(name="married_5_children", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 5,
                TaxField.SALARY_1_1AJ: 50000,
                TaxField.SALARY_2_1BJ: 60000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 6,
                TaxField.NET_TAXES: 4808.0,
            },
            flags={
            }),
    TaxTest(name="single", year=2022,
            inputs={
                TaxField.MARRIED: False,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 1,
                TaxField.NET_TAXES: 2022.0,
            },
            flags={}),
    TaxTest(name="single_1_child", year=2022,
            inputs={
                TaxField.MARRIED: False,
                TaxField.NB_CHILDREN: 1,
                TaxField.SALARY_1_1AJ: 50000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 1.5,
                TaxField.NET_TAXES: 5830.0,
            },
            flags={}),
    TaxTest(name="single_5_children", year=2022,
            inputs={
                TaxField.MARRIED: False,
                TaxField.NB_CHILDREN: 5,
                TaxField.SALARY_1_1AJ: 80000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 5,
                TaxField.NET_TAXES: 2786.0,
            },
            flags={}),
    TaxTest(name="family_quotient_capping", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 2,
                TaxField.SALARY_1_1AJ: 35000,
                TaxField.SALARY_2_1BJ: 48000,
            },
            results={
                TaxField.NET_TAXES: 7282.0,
            },
            flags={
                TaxInfoFlag.FAMILY_QUOTIENT_CAPPING: "tax += 2392.44€",
                TaxInfoFlag.MARGINAL_TAX_RATE: "11%"
            }),
    TaxTest(name="fee_rebate_capping", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 130000,
            },
            results={
                TaxField.NET_TAXES: 25916.0,
                TaxField.DEDUCTION_10P_2: 12652,
                TaxField.TAXABLE_INCOME: 126348,
            },
            flags={
                TaxInfoFlag.FEE_REBATE_INCOME_2: "taxable income += 348€",
                TaxInfoFlag.MARGINAL_TAX_RATE: "30%"
            }),
    TaxTest(name="fee_rebate_floor_2021", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 4000,
                TaxField.SALARY_2_1BJ: 60000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 57558.0,
                TaxField.NET_TAXES: 5279.0,
            },
            flags={
            }),
    TaxTest(name="fee_rebate_floor_2022", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 4000,
                TaxField.SALARY_2_1BJ: 60000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 57552.0,
                TaxField.NET_TAXES: 5110.0,
            },
            flags={
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
