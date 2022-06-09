import pytest
from .common import TaxTest, tax_testing
from src.easyfrenchtax import TaxField

tax_tests = [
    TaxTest(name="capital_gain", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.CAPITAL_GAIN_3VG: 20000,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 83000,
                TaxField.NET_TAXES: 9472,
                TaxField.CAPITAL_GAIN_TAX: 2560,
                TaxField.NET_SOCIAL_TAXES: 3440
            },
            flags={
            }),
    TaxTest(name="capital_gain_and_tax_reductions", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.CAPITAL_GAIN_3VG: 20000,
                # the following is big enough to swallow income tax, but it can't reduce capital gain tax
                TaxField.CHARITY_DONATION_7UD: 30000,
            },
            results={
                TaxField.NET_TAXES: 2560,  # tax reduction doesn't apply to capital gain tax
                TaxField.CAPITAL_GAIN_TAX: 2560,
                TaxField.NET_SOCIAL_TAXES: 3440,
            },
            flags={
            }),
    TaxTest(name="capital_gain_and_tax_credit", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.CAPITAL_GAIN_3VG: 20000,
                # the following is big enough to swallow income tax AND capital gain tax (because it's credit)
                TaxField.HOME_SERVICES_7DB: 10000,
            },
            results={
                TaxField.NET_TAXES: -2440,
                TaxField.CAPITAL_GAIN_TAX: 2560,
                TaxField.NET_SOCIAL_TAXES: 3440,
            },
            flags={
            }),
    TaxTest(name="social_taxes_on_stock_options", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.EXERCISE_GAIN_1_1TT: 1000,
                TaxField.EXERCISE_GAIN_2_1UT: 2000,
                TaxField.CAPITAL_GAIN_3VG: 4000,
                TaxField.TAXABLE_ACQUISITION_GAIN_1TZ: 8000,
                TaxField.ACQUISITION_GAIN_REBATES_1UZ: 16000,
                TaxField.ACQUISITION_GAIN_50P_REBATES_1WZ: 32000,
            },
            results={
                TaxField.NET_TAXES: 10634,
                TaxField.NET_SOCIAL_TAXES: 10911,
            },
            flags={
            }),
    TaxTest(name="fixed_income_investments", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.FIXED_INCOME_INTERESTS_2TR: 150,
            },
            results={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.FIXED_INCOME_INTERESTS_2TR: 150
            },
            flags={
            }),
    TaxTest(name="fixed_income_investments_already_taxed", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.FIXED_INCOME_INTERESTS_2TR: 200,
                TaxField.FIXED_INCOME_INTERESTS_ALREADY_TAXED_2BH: 100,
                TaxField.INTEREST_TAX_ALREADY_PAID_2CK: 15,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 63200,
                TaxField.SIMPLE_TAX_RIGHT: 6744,
                TaxField.INVESTMENT_INCOME_TAX: 26,
                TaxField.NET_TAXES: 6755,
                TaxField.NET_SOCIAL_TAXES: 18,
            },
            flags={
            }),
    TaxTest(name="partial_tax_and_global_capping", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 70000,
                TaxField.SALARY_2_1BJ: 80000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CH: 50000,
                TaxField.FIXED_INCOME_INTERESTS_2TR: 200,
                TaxField.FIXED_INCOME_INTERESTS_ALREADY_TAXED_2BH: 100,
                TaxField.INTEREST_TAX_ALREADY_PAID_2CK: 15
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 135200,
                TaxField.SIMPLE_TAX_RIGHT: 28344,
                TaxField.INVESTMENT_INCOME_TAX: 26,
                TaxField.NET_TAXES: 18355,
                TaxField.NET_SOCIAL_TAXES: 18
            },
            flags={
            }),
]


@pytest.mark.parametrize("year,inputs,results,flags",
                         [pytest.param(t.year, t.inputs, t.results, t.flags) for t in tax_tests],
                         ids=[t.name for t in tax_tests])
def test_tax(year, inputs, results, flags):
    tax_testing(year, inputs, results, flags)
