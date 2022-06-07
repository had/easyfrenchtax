import pytest
import re
from src.easyfrenchtax import TaxInfoFlag, TaxSimulator
from .common import TaxTest, TaxExceptionTest, tax_testing

tax_tests = [
    TaxTest(name="per_deduction", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "per_transfers_1_6NS": 4000,
                "per_transfers_2_6NT": 6000
            },
            results={
                "net_taxes": 3912.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "30%"
            }),
    TaxTest(name="children_daycare_credit", year=2021,
            inputs={
                "married": True,
                "nb_children": 2,
                "child_1_birthyear": 2020,
                "child_2_birthyear": 2010,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "children_daycare_fees_7GA": 2500
            },
            results={
                "household_shares": 3,
                "net_taxes": -1150.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING: "capped to 2300€ (originally 2500€)"
            }),
    TaxTest(name="children_daycare_credit_capped_per_child", year=2021,
            inputs={
                "married": True,
                "nb_children": 2,
                "child_1_birthyear": 2020,
                "child_2_birthyear": 2018,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "children_daycare_fees_7GA": 2500,
                "children_daycare_fees_7GB": 2000
            },
            results={
                "household_shares": 3,
                "net_taxes": -2150.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING: "capped to 4300€ (originally 4500€)"
            }),
    TaxTest(name="home_services_credit", year=2021,
            inputs={
                "married": True,
                "nb_children": 1,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "home_services_7DB": 14000
            },
            results={
                "net_taxes": -6750.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING: "capped to 13500€ (originally 14000€)"
            }),
    TaxTest(name="home_services_credit_2", year=2021,
            inputs={
                "married": True,
                "nb_children": 3,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "home_services_7DB": 16000
            },
            results={
                "net_taxes": -7500.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING: "capped to 15000€ (originally 16000€)"

            }),
    TaxTest(name="charity_reduction_no_credit", year=2021,
            inputs={
                "married": True,
                "nb_children": 3,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "charity_donation_7UD": 500
            },
            results={
                "household_shares": 4,
                "net_taxes": 0,  # reduction is not credit
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "500€",
            }),
    TaxTest(name="charity_reduction_75p", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "charity_donation_7UD": 500
            },
            results={
                "net_taxes": 6537,
                "charity_reduction": 375
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "500€",
            }),
    TaxTest(name="charity_reduction_66p", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "charity_donation_7UD": 1250,
                "charity_donation_7UF": 250,
            },
            results={
                "net_taxes": 5832,
                "charity_reduction": 1080
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "1000€ (capped)",
                TaxInfoFlag.CHARITY_66P: "500€",
            }),
    TaxTest(name="charity_reduction_ceiling", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 70000,
                "salary_2_1BJ": 80000,
                "charity_donation_7UD": 30000
            },
            results={
                "net_taxes": 9942,
                "charity_reduction": 18570
            },
            flags={
                TaxInfoFlag.CHARITY_75P: "1000€ (capped)",
                TaxInfoFlag.CHARITY_66P: "27000€ (capped)",
            }),
    TaxTest(name="charity_reduction_negative_income", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 5000,
                "salary_2_1BJ": 0,
                "rental_income_global_deficit_4BC": 10000,
                "charity_donation_7UF": 250,
            },
            results={
                "reference_fiscal_income": 0,
                "net_taxes": 0,
                "charity_reduction": 0
            },
            flags={
            }),
    TaxTest(name="pme_capital_subscription", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "pme_capital_subscription_7CF": 1000,  # 18% reduction => 180€
                "pme_capital_subscription_7CH": 2000  # 25% reduction => 500€
            },
            results={
                "net_taxes": 6232,
                "pme_subscription_reduction": 680
            },
            flags={
            }),
    TaxTest(name="pme_capital_subscription_ceiling", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 70000,
                "salary_2_1BJ": 80000,
                "pme_capital_subscription_7CF": 70000,  # 18% reduction => 180€
                "pme_capital_subscription_7CH": 50000  # 25% reduction => 500€
            },
            results={
                "net_taxes": 18512,
                "pme_subscription_reduction": 20100
            },
            flags={
            }),
    TaxTest(name="pme_capital_subscription_ceiling_single", year=2022,
            inputs={
                "married": False,
                "nb_children": 0,
                "salary_1_1AJ": 70000,
                "pme_capital_subscription_7CF": 30000,  # 18% reduction => 180€
                "pme_capital_subscription_7CH": 40000  # 25% reduction => 500€
            },
            results={
                "net_taxes": 2822,
                "pme_subscription_reduction": 10400
            },
            flags={
            }),
    TaxTest(name="global_fiscal_advantages_capping_1", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 70000,
                "salary_2_1BJ": 80000,
                "pme_capital_subscription_7CH": 50000
            },
            results={
                "net_taxes": 18344,
            },
            flags={
                TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES: "capped to 10'000€ (originally 12500.0€)",
            }),
    TaxTest(name="global_fiscal_advantages_capping_2", year=2022,
            inputs={
                "married": True,
                "nb_children": 1,
                "child_1_birthyear": 2020,
                "salary_1_1AJ": 70000,
                "salary_2_1BJ": 80000,
                "pme_capital_subscription_7CH": 35000,
                "children_daycare_fees_7GA": 2500,
                "home_services_7DB": 5000
            },
            results={
                "net_taxes": 16752,
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
                         "married": True,
                         "nb_children": 1,
                         "child_1_birthyear": 2010,
                         "salary_1_1AJ": 10000,
                         "salary_2_1BJ": 10000,
                         "children_daycare_fees_7GA": 2500
                     },
                     message=re.escape("You are declaring more children daycare fees than you have children below 6y old")),
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