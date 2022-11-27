import pytest
import re
from src.easyfrenchtax import TaxInfoFlag, TaxField, TaxSimulator
from .common import TaxTest, TaxExceptionTest, tax_testing

tax_tests = [
    TaxTest(name="per_deduction", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.PER_TRANSFERS_1_6NS: 4000,
                TaxField.PER_TRANSFERS_2_6NT: 6000,
            },
            results={
                TaxField.NET_TAXES: 3912.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "30%"
            }),
    TaxTest(name="children_daycare_credit", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 2,
                TaxField.CHILD_1_BIRTHYEAR: 2020,
                TaxField.CHILD_2_BIRTHYEAR: 2010,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.CHILDREN_DAYCARE_FEES_7GA: 2500,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 3,
                TaxField.NET_TAXES: -1150.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING: "capped to 2300€ (originally 2500€)"
            }),
    TaxTest(name="children_daycare_credit_capped_per_child", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 2,
                TaxField.CHILD_1_BIRTHYEAR: 2020,
                TaxField.CHILD_2_BIRTHYEAR: 2018,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.CHILDREN_DAYCARE_FEES_7GA: 2500,
                TaxField.CHILDREN_DAYCARE_FEES_7GB: 2000,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 3,
                TaxField.NET_TAXES: -2150.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING: "capped to 4300€ (originally 4500€)"
            }),
    TaxTest(name="home_services_credit", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 1,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.HOME_SERVICES_7DB: 14000,
            },
            results={
                TaxField.NET_TAXES: -6750.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING: "capped to 13500€ (originally 14000€)"
            }),
    TaxTest(name="home_services_credit_2", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 3,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.HOME_SERVICES_7DB: 16000,
            },
            results={
                TaxField.NET_TAXES: -7500.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING: "capped to 15000€ (originally 16000€)"

            }),
    TaxTest(name="charity_reduction_no_credit", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 3,
                TaxField.SALARY_1_1AJ: 10000,
                TaxField.SALARY_2_1BJ: 10000,
                TaxField.CHARITY_DONATION_7UD: 500,
            },
            results={
                TaxField.HOUSEHOLD_SHARES: 4,
                TaxField.NET_TAXES: 0  # reduction is not credit
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "500€",
            }),
    TaxTest(name="charity_reduction_75p", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.CHARITY_DONATION_7UD: 500,
            },
            results={
                TaxField.NET_TAXES: 6537,
                TaxField.CHARITY_REDUCTION: 375,
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "500€",
            }),
    TaxTest(name="charity_reduction_66p", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.CHARITY_DONATION_7UD: 1250,
                TaxField.CHARITY_DONATION_7UF: 250,
            },
            results={
                TaxField.NET_TAXES: 5832,
                TaxField.CHARITY_REDUCTION: 1080,
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "1000€ (capped)",
                TaxInfoFlag.CHARITY_66P: "500€",
            }),
    TaxTest(name="charity_reduction_ceiling", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 70000,
                TaxField.SALARY_2_1BJ: 80000,
                TaxField.CHARITY_DONATION_7UD: 30000,
            },
            results={
                TaxField.NET_TAXES: 9942,
                TaxField.CHARITY_REDUCTION: 18570
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "1000€ (capped)",
                TaxInfoFlag.CHARITY_66P: "27000€ (capped)",
            }),
    TaxTest(name="charity_reduction_negative_income", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 5000,
                TaxField.SALARY_2_1BJ: 0,
                TaxField.RENTAL_INCOME_GLOBAL_DEFICIT_4BC: 10000,
                TaxField.CHARITY_DONATION_7UF: 250,
            },
            results={
                TaxField.REFERENCE_FISCAL_INCOME: 0,
                TaxField.NET_TAXES: 0,
                TaxField.CHARITY_REDUCTION: 0,
            },
            flags={
            }),
    TaxTest(name="sme_capital_subscription", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 30000,
                TaxField.SALARY_2_1BJ: 40000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CF: 1000,   # 18% reduction => 180€
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CH: 2000,   # 25% reduction => 500€
            },
            results={
                TaxField.NET_TAXES: 6232,
                TaxField.SME_SUBSCRIPTION_REDUCTION: 680,
            },
            flags={
            }),
    TaxTest(name="sme_capital_subscription_ceiling", year=2021,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 70000,
                TaxField.SALARY_2_1BJ: 80000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CF: 70000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CH: 50000,
            },
            results={
                TaxField.NET_TAXES: 18512,
                TaxField.SME_SUBSCRIPTION_REDUCTION: 20100,
            },
            flags={
            }),
    TaxTest(name="sme_capital_subscription_ceiling_single", year=2022,
            inputs={
                TaxField.MARRIED: False,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 70000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CF: 30000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CH: 40000,
            },
            results={
                TaxField.NET_TAXES: 2822,
                TaxField.SME_SUBSCRIPTION_REDUCTION: 10400,
            },
            flags={
            }),
    TaxTest(name="global_fiscal_advantages_capping_1", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 0,
                TaxField.SALARY_1_1AJ: 70000,
                TaxField.SALARY_2_1BJ: 80000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CH: 50000,
            },
            results={
                TaxField.NET_TAXES: 18344,
            },
            flags={
                TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES: "capped to 10'000€ (originally 12500.0€)",
            }),
    TaxTest(name="global_fiscal_advantages_capping_2", year=2022,
            inputs={
                TaxField.MARRIED: True,
                TaxField.NB_CHILDREN: 1,
                TaxField.CHILD_1_BIRTHYEAR: 2020,
                TaxField.SALARY_1_1AJ: 70000,
                TaxField.SALARY_2_1BJ: 80000,
                TaxField.SME_CAPITAL_SUBSCRIPTION_7CH: 35000,
                TaxField.CHILDREN_DAYCARE_FEES_7GA: 2500,
                TaxField.HOME_SERVICES_7DB: 5000,
            },
            results={
                TaxField.NET_TAXES: 16752,
            },
            flags={
                TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES: "capped to 10'000€ (originally 12400.0€)",
            }),
]


@pytest.mark.parametrize("year,inputs,results,flags",
                         [pytest.param(t.year, t.inputs, t.results, t.flags) for t in tax_tests],
                         ids=[t.name for t in tax_tests])
def test_tax(year, inputs, results, flags):
    tax_testing(year, inputs, results, flags)


tax_exception_tests = [
    TaxExceptionTest(name="children_daycare_credit_too_old", year=2021,
                     inputs={
                        TaxField.MARRIED: True,
                        TaxField.NB_CHILDREN: 1,
                        TaxField.CHILD_1_BIRTHYEAR: 2010,
                        TaxField.SALARY_1_1AJ: 10000,
                        TaxField.SALARY_2_1BJ: 10000,
                        TaxField.CHILDREN_DAYCARE_FEES_7GA: 2500,
                     },
                     message=re.escape("You are declaring more children daycare fees (1) than you have children below 6y old (0)")),
]

@pytest.mark.parametrize("year,inputs,message",
                         [pytest.param(t.year, t.inputs, t.message) for t in tax_exception_tests],
                         ids=[t.name for t in tax_exception_tests])
def test_tax_exception(year, inputs, message):
    with pytest.raises(Exception, match=message):
        TaxSimulator(year, inputs)

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