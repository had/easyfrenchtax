import re

import pytest
from src.easyfrenchtax import TaxSimulator
from .common import TaxTest, TaxExceptionTest, tax_testing


tax_tests = [
    TaxTest(name="rental_income_simplified", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "simplified_rental_income_4BE": 12000,
            },
            results={
                "reference_fiscal_income": 80400,
                "net_taxes": 11964,
                "rental_income_result": 8400,
                "net_social_taxes": 1445
            },
            flags={
            }),
    TaxTest(name="rental_income_profit", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "real_rental_profit_4BA": 10000,
            },
            results={
                "reference_fiscal_income": 82000,
                "net_taxes": 12444,
                "rental_income_result": 10000,
                "net_social_taxes": 1720,
                "rental_deficit_carryover": 0
            },
            flags={
            }),
    TaxTest(name="rental_income_profit_minus_previous_deficit_1", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "real_rental_profit_4BA": 10000,
                "previous_rental_income_deficit_4BD": 3000
            },
            results={
                "reference_fiscal_income": 79000,
                "net_taxes": 11544,
                "rental_income_result": 7000,
                "net_social_taxes": 1204,
                "rental_deficit_carryover": 0
            },
            flags={
            }),
    TaxTest(name="rental_income_profit_minus_previous_deficit_2", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "real_rental_profit_4BA": 10000,
                "previous_rental_income_deficit_4BD": 13000
            },
            results={
                "reference_fiscal_income": 72000,
                "net_taxes": 9444,
                "rental_income_result": 0,
                "net_social_taxes": 0,
                "rental_deficit_carryover": 3000
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "real_rental_income_deficit_4BB": 10000,
            },
            results={
                "reference_fiscal_income": 72000,
                "net_taxes": 9444,
                "rental_income_result": 0,
                "net_social_taxes": 0,
                "rental_deficit_carryover": 10000
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit_current_and_past", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "real_rental_income_deficit_4BB": 10000,
                "previous_rental_income_deficit_4BD": 20000
            },
            results={
                "reference_fiscal_income": 72000,
                "net_taxes": 9444,
                "rental_income_result": 0,
                "net_social_taxes": 0,
                "rental_deficit_carryover": 30000
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit_global_1", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 50000,
                "real_rental_income_deficit_4BB": 10000,
                "rental_income_global_deficit_4BC": 2000,
                "previous_rental_income_deficit_4BD": 1000
            },
            results={
                "reference_fiscal_income": 70000,
                "net_taxes": 8844,
                "rental_income_result": -2000,
                "net_social_taxes": 0,
                "rental_deficit_carryover": 11000
            },
            flags={
            }),
    TaxTest(name="rental_income_deficit_global_2", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 5000,
                "salary_2_1BJ": 0,
                "rental_income_global_deficit_4BC": 10000,
            },
            results={
                "reference_fiscal_income": -5500,
                "net_taxes": 0,
                "rental_income_result": -10000,
                "net_social_taxes": 0,
                "rental_deficit_carryover": 0
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
                         "married": True,
                         "nb_children": 0,
                         "salary_1_1AJ": 30000,
                         "salary_2_1BJ": 50000,
                         "simplified_rental_income_4BE": 18000,
                     },
                     message=re.escape("Simplified rental income reporting (4BE) cannot exceed 15'000€")),
    TaxExceptionTest(name="rental_income_simplified_cannot_combine", year=2022,
                     inputs={
                         "married": True,
                         "nb_children": 0,
                         "salary_1_1AJ": 30000,
                         "salary_2_1BJ": 50000,
                         "simplified_rental_income_4BE": 12000,
                         "real_rental_profit_4BA": 1000
                     },
                     message=re.escape(
                         "The simplified rental income reporting (4BE) cannot be combined with the default rental income reporting (4BA 4BB 4BC)")),
    TaxExceptionTest(name="rental_income_global_deficit_exceeds_ceiling", year=2022,
                     inputs={
                         "married": True,
                         "nb_children": 0,
                         "salary_1_1AJ": 30000,
                         "salary_2_1BJ": 50000,
                         "rental_income_global_deficit_4BC": 12000
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
