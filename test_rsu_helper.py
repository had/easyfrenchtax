import pytest
from rsu_helper import RsuHelper
from datetime import date


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
    