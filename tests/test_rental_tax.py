import re

import pytest
from src.easyfrenchtax import TaxSimulator, TaxField
from .common import TaxTest, TaxExceptionTest, tax_testing


tax_tests = [
    TaxTest(name="rental_income_simplified", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.SIMPLIFIED_RENTAL_INCOME_4BE: 12000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 80400,
                TaxField.NET_TAXES: 11964,
                TaxField.RENTAL_INCOME_RESULT: 8400,
                TaxField.NET_SOCIAL_TAXES: 1445,
            },
            flags={
            }),
    TaxTest(name="rental_income_profit", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.REAL_RENTAL_PROFIT_4BA: 10000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 82000,
                TaxField.NET_TAXES: 12444,
                TaxField.RENTAL_INCOME_RESULT: 10000,
                TaxField.NET_SOCIAL_TAXES: 1720,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 0,
            },
            flags={
            }),
    TaxTest(name="rental_income_profit_minus_previous_deficit_1", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.REAL_RENTAL_PROFIT_4BA: 10000,
                TaxField.PREVIOUS_RENTAL_INCOME_DEFICIT_4BD: 3000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 79000,
                TaxField.NET_TAXES: 11544,
                TaxField.RENTAL_INCOME_RESULT: 7000,
                TaxField.NET_SOCIAL_TAXES: 1204,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 0,
            },
            flags={
            }),
    TaxTest(name="rental_income_profit_minus_previous_deficit_2", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.REAL_RENTAL_PROFIT_4BA: 10000,
                TaxField.PREVIOUS_RENTAL_INCOME_DEFICIT_4BD: 13000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 72000,
                TaxField.NET_TAXES: 9444,
                TaxField.RENTAL_INCOME_RESULT: 0,
                TaxField.NET_SOCIAL_TAXES: 0,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 3000,
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.REAL_RENTAL_INCOME_DEFICIT_4BB: 10000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 72000,
                TaxField.NET_TAXES: 9444,
                TaxField.RENTAL_INCOME_RESULT: 0,
                TaxField.NET_SOCIAL_TAXES: 0,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 10000,
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit_current_and_past", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.REAL_RENTAL_INCOME_DEFICIT_4BB: 10000,
                TaxField.PREVIOUS_RENTAL_INCOME_DEFICIT_4BD: 20000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 72000,
                TaxField.NET_TAXES: 9444,
                TaxField.RENTAL_INCOME_RESULT: 0,
                TaxField.NET_SOCIAL_TAXES: 0,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 30000,
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit_global_1", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 50000,
                TaxField.REAL_RENTAL_INCOME_DEFICIT_4BB: 10000,
                TaxField.RENTAL_INCOME_GLOBAL_DEFICIT_4BC: 2000,
                TaxField.PREVIOUS_RENTAL_INCOME_DEFICIT_4BD: 1000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 70000,
                TaxField.NET_TAXES: 8844,
                TaxField.RENTAL_INCOME_RESULT: -2000,
                TaxField.NET_SOCIAL_TAXES: 0,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 11000,
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit_global_2", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 5000,
                TaxField.SALARY_2_1BJ: 0,
                TaxField.RENTAL_INCOME_GLOBAL_DEFICIT_4BC: 10000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 0,
                TaxField.NET_TAXES: 0,
                TaxField.RENTAL_INCOME_RESULT: -10000,
                TaxField.NET_SOCIAL_TAXES: 0,
                TaxField.RENTAL_DEFICIT_CARRYOVER: 0,
            },
            flags={
            }),
    TaxTest(name="lmnp_income", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 50000,
                TaxField.SALARY_2_1BJ: 30000,
                TaxField.LMNP_MICRO_INCOME_1_5ND: 1000,
                TaxField.LMNP_MICRO_INCOME_2_5OD: 12000
            },
            results={
                TaxField.TAXABLE_LMNP_INCOME: 6500,
                TaxField.REFERENCE_FISCAL_INCOME: 78500,
                TaxField.NET_TAXES: 11394,
                TaxField.NET_SOCIAL_TAXES: 1119,
            },
            flags={
            }),
    ]

@pytest.mark.parametrize("year,inputs,results,flags",
                         [pytest.param(t.year, t.inputs, t.results, t.flags) for t in tax_tests],
                         ids=[t.name for t in tax_tests])
def test_tax(year, inputs, results, flags):
    tax_testing(year, inputs, results, flags)

tax_exception_tests = [
    TaxExceptionTest(name="rental_income_simplified_exceeds_ceiling", year=2022,
                     inputs={
                         TaxField.MARRIED: True,
                         TaxField.NB_CHILDREN: 0,
                         TaxField.SALARY_1_1AJ: 30000,
                         TaxField.SALARY_2_1BJ: 50000,
                         TaxField.SIMPLIFIED_RENTAL_INCOME_4BE: 18000,
                     },
                     message=re.escape("Simplified rental income reporting (4BE) cannot exceed 15'000€")),
    TaxExceptionTest(name="rental_income_simplified_cannot_combine", year=2022,
                     inputs={
                         TaxField.MARRIED: True,
                         TaxField.NB_CHILDREN: 0,
                         TaxField.SALARY_1_1AJ: 30000,
                         TaxField.SALARY_2_1BJ: 50000,
                         TaxField.SIMPLIFIED_RENTAL_INCOME_4BE: 12000,
                         TaxField.REAL_RENTAL_PROFIT_4BA: 1000,
                     },
                     message=re.escape(
                         "The simplified rental income reporting (4BE) cannot be combined with the default rental income reporting (4BA 4BB 4BC)")),
    TaxExceptionTest(name="rental_income_global_deficit_exceeds_ceiling", year=2022,
                     inputs={
                         TaxField.MARRIED: True,
                         TaxField.NB_CHILDREN: 0,
                         TaxField.SALARY_1_1AJ: 30000,
                         TaxField.SALARY_2_1BJ: 50000,
                         TaxField.RENTAL_INCOME_GLOBAL_DEFICIT_4BC: 12000,
                     },
                     message=re.escape(
                         "Rental deficit for global deduction (4BC) cannot exceed 10'700€")),
]

@pytest.mark.parametrize("year,inputs,message",
                         [pytest.param(t.year, t.inputs, t.message) for t in tax_exception_tests],
                         ids=[t.name for t in tax_exception_tests])
def test_tax_exception(year, inputs, message):
    with pytest.raises(Exception, match=message):
        TaxSimulator(year, inputs)
