from collections.abc import Callable

import pytest
from src.easyfrenchtax import StockHelper
from datetime import date
from currency_converter import CurrencyConverter


@pytest.fixture
def stock_helper_with_plan():
    stock_helper = StockHelper()
    stock_helper.rsu_plan("Cake1", date(2016, 6, 28), "CAKE", "USD")
    stock_helper.rsu_vesting("CAKE", "Cake1", 240, date(2018, 6, 29), 20)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2018, 7, 30), 18)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2018, 8, 28), 19)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2018, 9, 28), 14)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2018, 10, 29), 15)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2018, 11, 28), 14)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2018, 12, 28), 19)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2019, 1, 28), 23)
    stock_helper.rsu_vesting("CAKE", "Cake1", 10, date(2019, 2, 28), 24)
    stock_helper.rsu_vesting("CAKE", "Cake1", 100, date(2020, 2, 28), 24)
    stock_helper.rsu_plan("Pineapple", date(2016, 6, 29), "PZZA", "USD")
    stock_helper.rsu_vesting("PZZA", "Pineapple", 313, date(2020, 12, 28), 20.84)
    stock_helper.rsu_vesting("PZZA", "Pineapple", 312, date(2021, 3, 28), 27.44)
    stock_helper.rsu_vesting("PZZA", "Pineapple", 313, date(2021, 6, 28), 37.25)
    stock_helper.rsu_plan("Pepperoni", date(2017, 7, 28), "PZZA", "USD")
    stock_helper.rsu_vesting("PZZA", "Pepperoni", 398, date(2020, 12, 16), 18.75)
    stock_helper.rsu_vesting("PZZA", "Pepperoni", 133, date(2021, 1, 26), 19.13)
    stock_helper.add_espp("BUD", 200, date(2019, 1, 15), 22, "USD")
    stock_helper.add_espp("BUD", 300, date(2019, 7, 15), 19, "USD")
    stock_helper.add_stockoptions("PZZA", "SO", 150, date(2018, 1, 15), 5, "USD")
    return stock_helper


@pytest.fixture
def convert_fn() -> Callable[[float, str, str, date], float]:
    cc = CurrencyConverter(fallback_on_wrong_date=True)
    return cc.convert


def test_summary(stock_helper_with_plan):
    summary = stock_helper_with_plan.summary()
    assert set(summary.keys()) == {"CAKE", "BUD", "PZZA"}
    assert set(summary["CAKE"].keys()) == {"RSU"}
    assert summary["CAKE"]["RSU"] == 420
    assert set(summary["BUD"].keys()) == {"ESPP"}
    assert summary["BUD"]["ESPP"] == 500
    assert set(summary["PZZA"].keys()) == {"StockOption", "RSU"}
    assert summary["PZZA"]["StockOption"] == 150


def test_rsu_sale(stock_helper_with_plan):
    final_count_1 = stock_helper_with_plan.sell_rsus("CAKE", 200, date(2019, 6, 3), sell_price=22, fees=0,
                                                     currency="USD")
    assert final_count_1 == 200
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 40
    assert all([r.available == 10 or r.acq_date > date(2019, 6, 3) for r in stock_helper_with_plan.rsus["CAKE"][1:]])
    final_count_2 = stock_helper_with_plan.sell_rsus("CAKE", 200, date(2019, 6, 3), sell_price=22, fees=0,
                                                     currency="USD")
    assert final_count_2 == 120, "Cannot sell more than we have"

def test_rsu_sell_available(stock_helper_with_plan):
    # check that we only consider RSUs available at the sale date, not afterwards
    # on 1-4-2021, only 313+312+398+133 are available
    available_before = 313+312+398+133
    available_after = 313

    amount_sold = stock_helper_with_plan.sell_rsus("PZZA", available_before + available_after, date(2021, 4, 1), sell_price=22, fees=0)
    assert amount_sold == available_before
    amount_sold_2 = stock_helper_with_plan.sell_rsus("PZZA", available_after, date(2021, 12, 1), sell_price=22, fees=0)
    assert amount_sold_2 == available_after

def test_rsu_fifo(stock_helper_with_plan):
    stock_helper_with_plan.sell_rsus("PZZA", 800, date(2022,1,1), sell_price=22, fees=0)
    vestings = sorted(stock_helper_with_plan.rsus["PZZA"],key=lambda sg: sg.acq_date)
    assert vestings[0].available == 0
    assert vestings[0].count == 398
    assert vestings[1].available == 0
    assert vestings[1].count == 313
    assert vestings[2].available == 44
    assert vestings[2].count == 133
    assert vestings[3].available == 312
    assert vestings[3].count == 312
    assert vestings[4].available == 313
    assert vestings[4].count == 313


def test_rsu_acquisition_gain_tax(stock_helper_with_plan):
    stock_helper_with_plan.sell_rsus("CAKE", 200, date(2019, 1, 16),
                                     sell_price=22, fees=0, currency="USD")
    taxes = stock_helper_with_plan.compute_acquisition_gain_tax(2019)
    assert taxes["taxable_acquisition_gain_1TZ"] == 3432
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 0
    assert taxes["exercise_gain_1_1TT"] == 0
    assert taxes["exercise_gain_2_1UT"] == 0


def test_rsu_acquisition_gain_tax_rebates(stock_helper_with_plan):
    stock_helper_with_plan.sell_rsus("CAKE", 200, date(2021, 8, 2),
                                     sell_price=28, fees=0, currency="USD")
    taxes = stock_helper_with_plan.compute_acquisition_gain_tax(2021)
    assert taxes["taxable_acquisition_gain_1TZ"] == 1716
    assert taxes["acquisition_gain_50p_rebates_1WZ"] == 0
    assert taxes["acquisition_gain_rebates_1UZ"] == 1716
    assert taxes["exercise_gain_1_1TT"] == 0
    assert taxes["exercise_gain_2_1UT"] == 0


def test_rsu_capital_gain_simple(stock_helper_with_plan):
    final_count = stock_helper_with_plan.sell_rsus("CAKE", 200, date(2021, 8, 2),
                                                   sell_price=28, fees=0, currency="USD")
    assert final_count == 200
    report = stock_helper_with_plan.compute_capital_gain_tax(2021)
    assert True


def test_rsu_example(stock_helper_with_plan):
    final_count = stock_helper_with_plan.sell_rsus("PZZA", 844, date(2021, 2, 12),
                                                   sell_price=31.52, fees=0, currency="USD")
    assert final_count == 844
    report_ag = stock_helper_with_plan.compute_acquisition_gain_tax(2021)
    assert report_ag['taxable_acquisition_gain_1TZ'] == 13556
    report_cg = stock_helper_with_plan.compute_capital_gain_tax(2021)
    report_2042C = report_cg['2042C']
    report_2074 = report_cg['2074']
    assert report_2042C['capital_gain_3VG'] == 8413
    assert len(report_2074) == 3
    assert report_2074[0]['sold_stock_units_515'] == 398
    assert report_2074[0]['global_acquisition_cost_521'] == 6121
    assert report_2074[0]['global_selling_proceeds_516'] == 10360
    assert report_2074[1]['sold_stock_units_515'] == 313
    assert report_2074[1]['global_acquisition_cost_521'] == 5340
    assert report_2074[1]['global_selling_proceeds_516'] == 8147
    assert report_2074[2]['sold_stock_units_515'] == 133
    assert report_2074[2]['global_acquisition_cost_521'] == 2095
    assert report_2074[2]['global_selling_proceeds_516'] == 3462
    stock_helper_with_plan.helper_capital_gain_tax(report_cg)


def test_espp_sale(convert_fn):
    stock_helper = StockHelper()
    stock_helper.add_espp("BUD", 200, date(2019, 1, 15), 22, "USD")
    stock_helper.add_espp("BUD", 300, date(2019, 7, 15), 19, "USD")
    sell_price = 28
    final_count = stock_helper.sell_espp("BUD", 300, date(2021, 8, 2), sell_price=sell_price, fees=0, currency="USD")
    assert final_count == 300

    report_ag = stock_helper.compute_acquisition_gain_tax(2021)
    assert not any(report_ag.values()), "ESPP should not yield acquisition gain (thus no acquisition gain tax)"

    report_cg = stock_helper.compute_capital_gain_tax(2021)
    report_2042C = report_cg['2042C']
    report_2074 = report_cg['2074']

    acq_price_eur_1 = round(convert_fn(22, "USD", "EUR", date(2019, 1, 15)), 2)
    acq_price_eur_2 = round(convert_fn(19, "USD", "EUR", date(2019, 7, 15)), 2)
    sell_price_eur = round(convert_fn(sell_price, "USD", "EUR", date(2021, 8, 2)), 2)
    assert report_2074[0]['sold_stock_units_515'] == 200
    assert report_2074[0]['sell_price_514'] == sell_price_eur
    assert report_2074[1]['sold_stock_units_515'] == 100
    assert report_2074[1]['sell_price_514'] == sell_price_eur
    expected_capital_gain = round(
        200 * (round(sell_price_eur, 2) - round(acq_price_eur_1, 2)) +
        100 * (round(sell_price_eur, 2) - round(acq_price_eur_2, 2)), 2
    )
    assert report_2042C["capital_gain_3VG"] == expected_capital_gain, \
        "Capital gain tax should be compliant"


def test_stockoptions_sale(stock_helper_with_plan, convert_fn):
    sell_price = 40
    final_count = stock_helper_with_plan.sell_stockoptions(1, "PZZA", 50, date(2021, 8, 2), sell_price=sell_price,
                                                                    fees=0, currency="USD")
    agt = stock_helper_with_plan.compute_acquisition_gain_tax(2021)
    cgt = stock_helper_with_plan.compute_capital_gain_tax(2021)

    strike_price = stock_helper_with_plan.stock_options["PZZA"][0].acq_price
    assert final_count == 50
    ex_gain_usd = 50 * (sell_price - strike_price)
    assert agt["exercise_gain_1_1TT"] == round(convert_fn(ex_gain_usd, "USD", "EUR", date(2021, 8, 2))), \
        "Exercise gain tax should be compliant"
    assert agt["exercise_gain_2_1UT"] == 0
    assert not any(cgt["2042C"].values()), \
        "Stock options 'exercise and sell' should not yield capital gain (thus no capital gain tax)"
    assert len(cgt["2074"]) == 0, \
        "Stock options 'exercise and sell' should not yield capital gain (thus no capital gain tax)"


def test_reset_all(stock_helper_with_plan):
    # CAKE=240 ; BUD=200 ; PZZA=150
    stock_helper_with_plan.sell_rsus("CAKE", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.sell_espp("BUD", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.sell_stockoptions(1, "PZZA", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.reset()
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 240
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 200
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 150
    assert len(stock_helper_with_plan.stock_sales[2021]) == 0


def test_reset_by_stocktype(stock_helper_with_plan):
    # CAKE=240 ; BUD=200 ; PZZA=150
    stock_helper_with_plan.sell_rsus("CAKE", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.sell_espp("BUD", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.sell_stockoptions(1, "PZZA", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 190
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 150
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 100
    stock_helper_with_plan.reset(stock_types=["espp"])
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 190
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 200
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 100
    stock_helper_with_plan.reset(stock_types=["stockoption"])
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 190
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 200
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 150
    stock_helper_with_plan.reset(stock_types=["rsu"])
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 240
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 200
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 150


def test_reset_by_symbol(stock_helper_with_plan):
    # CAKE=240 ; BUD=200 ; PZZA=150
    stock_helper_with_plan.sell_rsus("CAKE", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.sell_espp("BUD", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    stock_helper_with_plan.sell_stockoptions(1, "PZZA", 50, date(2021, 8, 2), sell_price=123, fees=0, currency="USD")
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 190
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 150
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 100
    stock_helper_with_plan.reset(symbols=["CAKE", "PZZA"])
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 240
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 150
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 150
    stock_helper_with_plan.reset(symbols=["BUD"])
    assert stock_helper_with_plan.rsus["CAKE"][0].available == 240
    assert stock_helper_with_plan.espp_stocks["BUD"][0].available == 200
    assert stock_helper_with_plan.stock_options["PZZA"][0].available == 150
