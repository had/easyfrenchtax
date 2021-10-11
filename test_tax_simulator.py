from easyfrenchtax import TaxSimulator, TaxInfoFlag

# NOTE: all tests value have been checked against the official french tax simulator:
# https://www3.impots.gouv.fr/simulateur/calcul_impot/2021/simplifie/index.htm

def test_basic():
    tax_input = {
        "household_shares": 2,
        "nb_kids": 0,
        "salary_1_1AJ": 30000,
        "salary_2_1BJ": 40000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == 6912.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "30%"


def test_3_shares():
    tax_input = {
        "household_shares": 3,
        "nb_kids": 2,
        "salary_1_1AJ": 28000,
        "salary_2_1BJ": 35000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == 2909.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "11%"


def test_family_quotient_capping():
    tax_input = {
        "household_shares": 3,
        "nb_kids": 2,
        "salary_1_1AJ": 35000,
        "salary_2_1BJ": 48000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == 7282.0
    assert tax_sim.flags[TaxInfoFlag.FAMILY_QUOTIENT_CAPPING] == "tax += 2392.44€"
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "11%"


def test_fee_rebate_capping():
    tax_input = {
        "household_shares": 2,
        "nb_kids": 0,
        "salary_1_1AJ": 10000,
        "salary_2_1BJ": 130000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == 25916.0
    assert tax_result["deduction_10p_2"] == 12652
    assert tax_result["taxable_income"] == 126348
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "30%"
    assert tax_sim.flags[TaxInfoFlag.FEE_REBATE_INCOME_2] == "taxable income += 348€"


def test_fee_rebate_capping():
    tax_input = {
        "household_shares": 2,
        "nb_kids": 0,
        "salary_1_1AJ": 10000,
        "salary_2_1BJ": 130000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == 25916.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "30%"
    assert tax_sim.flags[TaxInfoFlag.FEE_REBATE_INCOME_2] == "taxable income += 348€"

def test_per_deduction():
    tax_input = {
        "household_shares": 2,
        "nb_kids": 0,
        "salary_1_1AJ": 30000,
        "salary_2_1BJ": 40000,
        "per_transfers_1_6NS": 4000,
        "per_transfers_2_6NT": 6000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == 3912.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "30%"

def test_children_daycare_credit():
    tax_input = {
        "household_shares": 2.5,
        "nb_kids": 1,
        "salary_1_1AJ": 10000,
        "salary_2_1BJ": 10000,
        "children_daycare_fees_7GA": 2500
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == -1150.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "0%"
    assert tax_sim.flags[TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING] == "capped to 2'300€ (originally 2500€)"

def test_home_services_credit():
    tax_input = {
        "household_shares": 2.5,
        "nb_kids": 1,
        "salary_1_1AJ": 10000,
        "salary_2_1BJ": 10000,
        "home_services_7DB": 14000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == -6750.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "0%"
    assert tax_sim.flags[TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING] == "capped to 13500€ (originally 14000€)"

def test_home_services_credit_2():
    tax_input = {
        "household_shares": 4,
        "nb_kids": 3,
        "salary_1_1AJ": 10000,
        "salary_2_1BJ": 10000,
        "home_services_7DB": 16000
    }
    tax_sim = TaxSimulator(tax_input)
    tax_result = tax_sim.state
    assert tax_result["net_taxes"] == -7500.0
    assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "0%"
    assert tax_sim.flags[TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING] == "capped to 15000€ (originally 16000€)"

# def test_charity_reduction():
#     tax_input = {
#         "household_shares": 4,
#         "nb_kids": 3,
#         "salary_1_1AJ": 10000,
#         "salary_2_1BJ": 10000,
#         "charity_donation_7UD": 500
#     }
#     tax_sim = TaxSimulator(tax_input)
#     tax_result = tax_sim.state
#     assert tax_result["net_taxes"] == 0
#     assert tax_sim.flags[TaxInfoFlag.MARGINAL_TAX_RATE] == "0%"
#     assert tax_sim.flags[TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING] == "capped to 15000€ (originally 16000€)"
