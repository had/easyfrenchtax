import pytest
from easyfrenchtax import StockHelper
from datetime import date

@pytest.fixture
def stock_helper_with_plan():
    stock_helper = StockHelper()
    stock_helper.rsu_plan("CAKE JUN 16", date(2016, 6, 28), "CAKE", "USD")
    stock_helper.rsu_vesting("CAKE JUN 16", 240, date(2018,6,29), 20)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,7,30), 18)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,8,28), 19)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,9,28), 14)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,10,29), 15)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,11,28), 14)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2018,12,28), 19)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2019,1,28), 23)
    stock_helper.rsu_vesting("CAKE JUN 16", 10, date(2019,2,28), 24)
    stock_helper.add_espp(50, date(2019,1,15),22, "USD")
    return stock_helper

def test_weighted_average_price(stock_helper_with_plan):
    weighted_average_price = stock_helper_with_plan.compute_weighted_average_prices(date(2018, 7, 1))
    rsu_under_test = stock_helper_with_plan.rsus[0]
    assert rsu_under_test.acq_price_eur == stock_helper_with_plan.weighted_average_prices[(rsu_under_test.plan_name, rsu_under_test.acq_date)], "weighted average price is computed on 1st element only, should be equal to original price"
    assert weighted_average_price == rsu_under_test.acq_price_eur, "returned value should also match the original price"
    assert len(stock_helper_with_plan.weighted_average_prices) == 1, "weighted average price should NOT be computed for the next elements"

def test_selling_rsus(stock_helper_with_plan):
    assert sum([r.available for r in stock_helper_with_plan.rsus]) == 320
    final_count_1, _, _ = stock_helper_with_plan.sell_rsus(200, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count_1 == 200
    assert stock_helper_with_plan.rsus[0].available == 40
    assert all([r.available == 10 for r in stock_helper_with_plan.rsus[1:]])
    final_count_2, _, _ = stock_helper_with_plan.sell_rsus(200, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count_2 == 120, "Cannot sell more than we have"

def test_selling_too_many_rsus(stock_helper_with_plan):
    assert sum([r.available for r in stock_helper_with_plan.rsus]) == 320
    final_count, _, _ = stock_helper_with_plan.sell_rsus(400, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count == 320, "Cannot sell more than we have"

def test_acquisition_gain_tax(stock_helper_with_plan):
    final_count, weighted_average_price, sell = stock_helper_with_plan.sell_rsus(200,date(2019,1,16), sell_price=22, fees=0, currency="USD")
#     final_count, weighted_average_price, sell = stock_helper_with_plan.sell_rsus(200,date(2018,7,2), sell_price=22, fees=0, currency="USD")
    print(sell)
    taxes = stock_helper_with_plan.compute_acquisition_gain_tax(2019)
    assert taxes["taxable_acquisition_gain_1TZ"] == 3431
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 0
    assert taxes["other_taxable_gain_1TT_1UT"] == 0

def test_acquisition_gain_tax_rebates(stock_helper_with_plan):
    final_count, weighted_average_price, sell = stock_helper_with_plan.sell_rsus(200,date(2021,8,2), sell_price=28, fees=0, currency="USD")
    taxes = stock_helper_with_plan.compute_acquisition_gain_tax(2021)
    assert taxes["taxable_acquisition_gain_1TZ"] == 1716
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 1716
    assert taxes["other_taxable_gain_1TT_1UT"] == 0


def test_bofip_case():
    # example from https://bofip.impots.gouv.fr/bofip/3619-PGP.html/identifiant=BOI-RPPM-PVBMI-20-10-20-40-20191220#Regle_du_prix_moyen_pondere_10
    stock_helper = StockHelper()
    stock_helper.rsu_plan("Test", date(2013,1,1), "X", "EUR")
    # plan_name, acq_count, acq_date, acq_price, currency = None
    year_N = 2010
    stock_helper.rsu_vesting("Test", 100, date(year_N    ,1,1), 95)
    stock_helper.rsu_vesting("Test", 200, date(year_N + 2,1,1), 105)
    stock_helper.rsu_vesting("Test", 100, date(year_N + 3,1,1), 107)
    _, weighted_average_price_1, _ = stock_helper.sell_rsus(150, date(year_N + 7,1,1), 110, 0)
    capital_gain_tax_1 = stock_helper.compute_capital_gain_tax(year_N + 7)
    assert weighted_average_price_1 == 103
    assert capital_gain_tax_1["2042C"]["capital_gain_3VG"] == 1050
    assert sum([r.available for r in stock_helper.rsus]) == 250
    stock_helper.rsu_vesting("Test", 50, date(year_N + 8,9,1), 100)
    stock_helper.rsu_vesting("Test", 300, date(year_N + 8,11,1), 107.50)
    _, weighted_average_price_2, _ = stock_helper.sell_rsus(200, date(year_N + 9,1,1), 108, 0)
    capital_gain_tax_2 = stock_helper.compute_capital_gain_tax(year_N + 9)
    assert weighted_average_price_2 == 105
    assert capital_gain_tax_2["2042C"]["capital_gain_3VG"] == 600
    assert sum([r.available for r in stock_helper.rsus]) == 400