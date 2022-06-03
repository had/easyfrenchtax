import pytest
from .common import TaxTest, tax_testing

tax_tests = [
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
]


@pytest.mark.parametrize("year,inputs,results,flags",
                         [pytest.param(t.year, t.inputs, t.results, t.flags) for t in tax_tests],
                         ids=[t.name for t in tax_tests])
def test_tax(year, inputs, results, flags):
    tax_testing(year, inputs, results, flags)
