import pytest
from src.easyfrenchtax import TaxSimulator, TaxInfoFlag
from .common import TaxTest

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
                "nb_children": 1,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "children_daycare_fees_7GA": 2500
            },
            results={
                "household_shares": 2.5,
                "net_taxes": -1150.0,
            },
            flags={
                TaxInfoFlag.MARGINAL_TAX_RATE: "0%",
                TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING: "capped to 2'300€ (originally 2500€)"
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
                "reference_fiscal_income": -5500,
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
    TaxTest(name="capital_gain", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "capital_gain_3VG": 20000
            },
            results={
                "reference_fiscal_income": 83000,
                "net_taxes": 9472,
                "capital_gain_tax": 2560,
                "net_social_taxes": 3440
            },
            flags={
            }),
    TaxTest(name="capital_gain_and_tax_reductions", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "capital_gain_3VG": 20000,
                # the following is big enough to swallow income tax, but it can't reduce capital gain tax
                "charity_donation_7UD": 30000
            },
            results={
                "net_taxes": 2560,  # tax reduction doesn't apply to capital gain tax
                "capital_gain_tax": 2560,
                "net_social_taxes": 3440
            },
            flags={
            }),
    TaxTest(name="capital_gain_and_tax_credit", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 10000,
                "salary_2_1BJ": 10000,
                "capital_gain_3VG": 20000,
                # the following is big enough to swallow income tax AND capital gain tax (because it's credit)
                "home_services_7DB": 10000
            },
            results={
                "net_taxes": -2440,
                "capital_gain_tax": 2560,
                "net_social_taxes": 3440
            },
            flags={
            }),
    TaxTest(name="social_taxes_on_stock_options", year=2021,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "exercise_gain_1_1TT": 1000,
                "exercise_gain_2_1UT": 2000,
                "capital_gain_3VG": 4000,
                "taxable_acquisition_gain_1TZ": 8000,
                "acquisition_gain_rebates_1UZ": 16000,
                "acquisition_gain_50p_rebates_1WZ": 32000
            },
            results={
                "net_taxes": 10634,
                "net_social_taxes": 10911
            },
            flags={
            }),
    TaxTest(name="fixed_income_investments", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "fixed_income_interests_2TR": 150,
            },
            results={
                "reference_fiscal_income": 63150,
                "simple_tax_right": 6744,
                "investment_income_tax": 19,
                "net_taxes": 6763,
                "net_social_taxes": 26
            },
            flags={
            }),
    TaxTest(name="fixed_income_investments_already_taxed", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 30000,
                "salary_2_1BJ": 40000,
                "fixed_income_interests_2TR": 200,
                "fixed_income_interests_already_taxed_2BH": 100,
                "interest_tax_already_paid_2CK": 15
            },
            results={
                "reference_fiscal_income": 63200,
                "simple_tax_right": 6744,
                "investment_income_tax": 26,
                "net_taxes": 6755,
                "net_social_taxes": 18
            },
            flags={
            }),
    TaxTest(name="partial_tax_and_global_capping", year=2022,
            inputs={
                "married": True,
                "nb_children": 0,
                "salary_1_1AJ": 70000,
                "salary_2_1BJ": 80000,
                "pme_capital_subscription_7CH": 50000,
                "fixed_income_interests_2TR": 200,
                "fixed_income_interests_already_taxed_2BH": 100,
                "interest_tax_already_paid_2CK": 15
            },
            results={
                "reference_fiscal_income": 135200,
                "simple_tax_right": 28344,
                "investment_income_tax": 26,
                "net_taxes": 18355,
                "net_social_taxes": 18
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
    tax_sim = TaxSimulator(year, inputs)
    tax_result = tax_sim.state
    tax_flags = tax_sim.flags
    for k, res in results.items():
        assert tax_result[k] == res
    for k, f in flags.items():
        assert tax_flags[k] == f
