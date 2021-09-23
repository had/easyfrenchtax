import pytest
from easyfrenchtax import RsuHelper
from datetime import date

@pytest.fixture
def rsu_helper_with_plan():
    rsu_helper = RsuHelper()
    rsu_helper.rsu_plan("CAKE JUN 16", date(2016, 6, 28), "CAKE", "USD")
    rsu_helper.rsu_vesting("CAKE JUN 16", 240, date(2018,6,29), 20)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,7,30), 18)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,8,28), 19)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,9,28), 14)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,10,29), 15)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,11,28), 14)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,12,28), 19)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2019,1,28), 23)
    rsu_helper.rsu_vesting("CAKE JUN 16", 10, date(2019,2,28), 24)
    return rsu_helper


def test_weighted_average_price(rsu_helper_with_plan):
    rsu_helper_with_plan.compute_weighted_average_prices(date(2018, 7, 1))
    assert rsu_helper_with_plan.rsus[0]["price_eur"] == rsu_helper_with_plan.rsus[0]["weight_averaged_price"], "weighted average price is computed on 1st element only, should be equal"
    assert all(["weight_averaged_price" not in r for r in rsu_helper_with_plan.rsus[1:]]), "weighted average price should NOT be computed for the next elements"

def test_selling_rsus(rsu_helper_with_plan):
    assert sum([r["available"] for r in rsu_helper_with_plan.rsus]) == 320
    final_count_1, _, _ = rsu_helper_with_plan.sell_rsus(200, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count_1 == 200
    assert rsu_helper_with_plan.rsus[0]["available"] == 40
    assert all([r["available"] == 10 for r in rsu_helper_with_plan.rsus[1:]])
    final_count_2, _, _ = rsu_helper_with_plan.sell_rsus(200, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count_2 == 120, "Cannot sell more than we have"
    
def test_selling_too_many_rsus(rsu_helper_with_plan):
    assert sum([r["available"] for r in rsu_helper_with_plan.rsus]) == 320
    final_count, _, _ = rsu_helper_with_plan.sell_rsus(400, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count == 320, "Cannot sell more than we have"
    
def test_acquisition_gain_tax(rsu_helper_with_plan):
    final_count, weighted_average_price, sell = rsu_helper_with_plan.sell_rsus(200,date(2019,1,16), sell_price=22, fees=0, currency="USD")
    taxes = rsu_helper_with_plan.compute_acquisition_gain_tax(2019)    
    assert taxes["taxable_acquisition_gain_1TZ"] == 3431
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 0
    assert taxes["other_taxable_gain_1TT_1UT"] == 0

def test_acquisition_gain_tax_rebates(rsu_helper_with_plan):
    final_count, weighted_average_price, sell = rsu_helper_with_plan.sell_rsus(200,date(2021,8,2), sell_price=28, fees=0, currency="USD")
    taxes = rsu_helper_with_plan.compute_acquisition_gain_tax(2021)    
    assert taxes["taxable_acquisition_gain_1TZ"] == 1716
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 1716
    assert taxes["other_taxable_gain_1TT_1UT"] == 0

    
def test_bofip_case():
    # example from https://bofip.impots.gouv.fr/bofip/3619-PGP.html/identifiant=BOI-RPPM-PVBMI-20-10-20-40-20191220#Regle_du_prix_moyen_pondere_10
    rsu_helper = RsuHelper()
    rsu_helper.rsu_plan("Test", date(2013,1,1), "X", "EUR")
    # plan_name, acq_count, acq_date, acq_price, currency = None
    year_N = 2010
    rsu_helper.rsu_vesting("Test", 100, date(year_N    ,1,1), 95)
    rsu_helper.rsu_vesting("Test", 200, date(year_N + 2,1,1), 105)
    rsu_helper.rsu_vesting("Test", 100, date(year_N + 3,1,1), 107)
    _, weighted_average_price_1, _ = rsu_helper.sell_rsus(150, date(year_N + 7,1,1), 110, 0)
    capital_gain_tax_1 = rsu_helper.compute_capital_gain_tax(year_N + 7)
    assert weighted_average_price_1 == 103
    assert capital_gain_tax_1["2042C"]["capital_gain_3VG"] == 1050
    assert sum([r["available"] for r in rsu_helper.rsus]) == 250
    rsu_helper.rsu_vesting("Test", 50, date(year_N + 8,9,1), 100)
    rsu_helper.rsu_vesting("Test", 300, date(year_N + 8,11,1), 107.50)
    _, weighted_average_price_2, _ = rsu_helper.sell_rsus(200, date(year_N + 9,1,1), 108, 0)
    capital_gain_tax_2 = rsu_helper.compute_capital_gain_tax(year_N + 9)
    assert weighted_average_price_2 == 105
    assert capital_gain_tax_2["2042C"]["capital_gain_3VG"] == 600
    assert sum([r["available"] for r in rsu_helper.rsus]) == 400
    