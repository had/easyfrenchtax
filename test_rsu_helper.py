import pytest
from easyfrenchtax import StockHelper
from datetime import date
from currency_converter import CurrencyConverter

@pytest.fixture
def stock_helper_with_plan():
    stock_helper = StockHelper()
    stock_helper.rsu_plan("RSU JUN 16", date(2016, 6, 28), "CAKE", "USD")
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 240, date(2018,6,29), 20)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2018,7,30), 18)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2018,8,28), 19)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2018,9,28), 14)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2018,10,29), 15)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2018,11,28), 14)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2018,12,28), 19)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2019,1,28), 23)
    stock_helper.rsu_vesting("CAKE", "RSU JUN 16", 10, date(2019,2,28), 24)
    stock_helper.add_espp("BUD", 500, date(2019,1,15),22, "USD")
    stock_helper.add_stockoptions("PZZA", "SO", 150, date(2018,1,15), 5, "USD")
    return stock_helper

@pytest.fixture
def convert_fn():
    cc = CurrencyConverter(fallback_on_wrong_date=True)
    return cc.convert

def test_summary(stock_helper_with_plan):
    summary = stock_helper_with_plan.summary()
    assert set(summary.keys()) == {"CAKE", "BUD", "PZZA"}
    assert set(summary["CAKE"].keys()) == {"RSU JUN 16"}
    assert summary["CAKE"]["RSU JUN 16"] == 320
    assert set(summary["BUD"].keys()) == {"espp"}
    assert summary["BUD"]["espp"] == 500
    assert set(summary["PZZA"].keys()) == {"SO"}
    assert summary["PZZA"]["SO"] == 150

def test_weighted_average_price(stock_helper_with_plan):
    weighted_average_price = stock_helper_with_plan.compute_weighted_average_prices("CAKE", date(2018, 7, 1))
    rsu_under_test = stock_helper_with_plan.rsus["CAKE"][0]
    assert rsu_under_test.acq_price_eur == stock_helper_with_plan.weighted_average_prices[(rsu_under_test.plan_name, rsu_under_test.acq_date)], "weighted average price is computed on 1st element only, should be equal to original price"
    assert weighted_average_price == rsu_under_test.acq_price_eur, "returned value should also match the original price"
    assert len(stock_helper_with_plan.weighted_average_prices) == 1, "weighted average price should NOT be computed for the next elements"

def test_selling_rsus(stock_helper_with_plan):
    assert sum([r.available for r in stock_helper_with_plan.rsus["CAKE"]]) == 320
    final_count_1, _, _ = stock_helper_with_plan.sell_rsus("CAKE", 200, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count_1 == 200
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 40
    assert all([r.available == 10 for r in stock_helper_with_plan.rsus["CAKE"][1:]])
    final_count_2, _, _ = stock_helper_with_plan.sell_rsus("CAKE", 200, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count_2 == 120, "Cannot sell more than we have"

def test_selling_too_many_rsus(stock_helper_with_plan):
    assert sum([r.available for r in stock_helper_with_plan.rsus["CAKE"]]) == 320
    final_count, _, _ = stock_helper_with_plan.sell_rsus("CAKE", 400, date(2019,6,3), sell_price=22, fees=0, currency="USD")
    assert final_count == 320, "Cannot sell more than we have"

def test_acquisition_gain_tax(stock_helper_with_plan):
    final_count, weighted_average_price, sell = stock_helper_with_plan.sell_rsus("CAKE", 200,date(2019,1,16), sell_price=22, fees=0, currency="USD")
    print(sell)
    taxes = stock_helper_with_plan.compute_acquisition_gain_tax(2019)
    assert taxes["taxable_acquisition_gain_1TZ"] == 3431
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 0
    assert taxes["other_taxable_gain_1TT_1UT"] == 0

def test_acquisition_gain_tax_rebates(stock_helper_with_plan):
    final_count, weighted_average_price, sell = stock_helper_with_plan.sell_rsus("CAKE", 200,date(2021,8,2), sell_price=28, fees=0, currency="USD")
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
    stock_helper.rsu_vesting("TEST", "Test", 100, date(year_N    ,1,1), 95)
    stock_helper.rsu_vesting("TEST", "Test", 200, date(year_N + 2,1,1), 105)
    stock_helper.rsu_vesting("TEST", "Test", 100, date(year_N + 3,1,1), 107)
    _, weighted_average_price_1, _ = stock_helper.sell_rsus("TEST", 150, date(year_N + 7,1,1), 110, 0)
    capital_gain_tax_1 = stock_helper.compute_capital_gain_tax(year_N + 7)
    assert weighted_average_price_1 == 103
    assert capital_gain_tax_1["2042C"]["capital_gain_3VG"] == 1050
    assert sum([r.available for r in stock_helper.rsus["TEST"]]) == 250
    stock_helper.rsu_vesting("TEST", "Test", 50, date(year_N + 8,9,1), 100)
    stock_helper.rsu_vesting("TEST", "Test", 300, date(year_N + 8,11,1), 107.50)
    _, weighted_average_price_2, _ = stock_helper.sell_rsus("TEST", 200, date(year_N + 9,1,1), 108, 0)
    capital_gain_tax_2 = stock_helper.compute_capital_gain_tax(year_N + 9)
    assert weighted_average_price_2 == 105
    assert capital_gain_tax_2["2042C"]["capital_gain_3VG"] == 600
    assert sum([r.available for r in stock_helper.rsus["TEST"]]) == 400

def test_espp_sale(stock_helper_with_plan, convert_fn):
    sell_price = 28
    final_count, unit_acquisition_price, sell = stock_helper_with_plan.sell_espp("BUD", 200, date(2021,8,2), sell_price=sell_price, fees=0, currency="USD")
    agt = stock_helper_with_plan.compute_acquisition_gain_tax(2021)
    cgt = stock_helper_with_plan.compute_capital_gain_tax(2021)
    
    sell_price_eur = convert_fn(sell_price, "USD", "EUR", date(2021,8,2))
    assert final_count == 200
    assert unit_acquisition_price == stock_helper_with_plan.espp_stocks["BUD"][0].acq_price_eur
    assert not any(agt.values()), "ESPP should not yield acquisition gain (thus no acquisition gain tax)"
    assert cgt["2042C"]["capital_gain_3VG"] == round(200*(round(sell_price_eur,2)-round(unit_acquisition_price, 2))), "Capital gain tax should be compliant"
    
def test_stockoptions_sale(stock_helper_with_plan, convert_fn):
    sell_price = 40
    final_count, _, sell = stock_helper_with_plan.sell_stockoptions("PZZA", 50, date(2021,8,2), sell_price=sell_price, fees=0, currency="USD")
    agt = stock_helper_with_plan.compute_acquisition_gain_tax(2021)
    cgt = stock_helper_with_plan.compute_capital_gain_tax(2021)

    strike_price = stock_helper_with_plan.stock_options["PZZA"][0].acq_price
    print(stock_helper_with_plan.stock_sales)
    assert final_count == 50
    assert agt["other_taxable_gain_1TT_1UT"] == round(convert_fn(50*(sell_price-strike_price), "USD", "EUR", date(2021,8,2))) , "Exercise gain tax should be compliant"
    assert not any(cgt["2042C"].values()), "Stock options 'exercise and sell' should not yield capital gain (thus no capital gain tax)"
    assert len(cgt["2074"]) == 0, "Stock options 'exercise and sell' should not yield capital gain (thus no capital gain tax)"
