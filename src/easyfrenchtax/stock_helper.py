from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional, Tuple

from dateutil.relativedelta import relativedelta
from currency_converter import CurrencyConverter
from collections import defaultdict
import csv
import glob

class RsuTaxScheme(str, Enum):
    NONQUALIFIED_RSU = "Non-qualified RSU"
    QUALIFIED_RSU = "Qualified RSU"
    MACRON_1_RSU = "Macron I"
    MACRON_2_RSU = "Macron II"
    MACRON_3_RSU = "Macron III"

class StockType(Enum):
    RSU = 1
    ESPP = 2
    STOCKOPTIONS = 3

@dataclass
class StockGroup:
    count: int
    available: int
    acq_price: float
    acq_price_eur: float
    acq_date: date
    plan_name: str


@dataclass
class RsuPlan:
    name: str
    approval_date: date
    taxation_scheme: RsuTaxScheme
    stock_symbol: str
    currency: str


@dataclass
class SaleEvent:
    symbol: str
    stock_type: StockType
    nb_stocks_sold: int
    unit_acquisition_price: float # in Euros
    sell_date: date
    sell_price_eur: float
    selling_fees: float
    owner: Optional[int] = None
    rsu_tax_scheme: Optional[RsuTaxScheme] = None
    acq_date: Optional[date] = None

# currency converter (USD/EUR in particular)
cc = CurrencyConverter(fallback_on_wrong_date=True, fallback_on_missing_rate=True)


class StockHelper:
    rsu_plans: dict[str, RsuPlan]
    rsus: dict[str, list[StockGroup]]  # TODO integrate list of RSUs to RsuPlan
    espp_stocks: dict[str, list[StockGroup]]
    stock_sales: dict[int, list[SaleEvent]]

    def __init__(self):
        self.rsu_plans = {}
        self.rsus = defaultdict(list)
        self.espp_stocks = defaultdict(list)
        self.stock_options = defaultdict(list)
        self.stock_sales = defaultdict(list)

    # TODO: this seems unused, consider removing
    def reset(self, stock_types: list[StockType] = (StockType.RSU, StockType.ESPP, StockType.STOCKOPTIONS),
              symbols: list[str] = None) -> None:
        for sales in self.stock_sales.values():
            sales[:] = [s for s in sales if
                        (symbols and s.symbol not in symbols) or (s.stock_type not in stock_types)]
        stock_types_mapping = {
            StockType.ESPP: self.espp_stocks,
            StockType.STOCKOPTIONS: self.stock_options,
            StockType.RSU: self.rsus
        }
        for stock_type in [stock_types_mapping[st] for st in stock_types]:
            if not symbols:
                stocks_subset = stock_type.values()
            else:
                stocks_subset = [stock_type[symbol] for symbol in symbols]
            for stocks in stocks_subset:
                for i, s in enumerate(stocks):
                    stocks[i].available = s.count

    # TODO: this seems unused, consider removing
    def summary(self) -> dict[str, dict[str, int]]:
        summary = defaultdict(lambda: defaultdict(int))
        for symbol, rsus in self.rsus.items():
            for rsu in rsus:
                summary[symbol]["RSU"] += rsu.count
        for symbol, espps in self.espp_stocks.items():
            for espp in espps:
                summary[symbol]["ESPP"] += espp.count
        for symbol, stockoptions in self.stock_options.items():
            for stockoption in stockoptions:
                summary[symbol]["StockOption"] += stockoption.count
        return summary

    # ----- RSU related load functions ------
    @staticmethod
    def _determine_rsu_plans_type(approval_date: date) -> RsuTaxScheme:
        if approval_date <= date(2012, 9, 27):
            return RsuTaxScheme.NONQUALIFIED_RSU
        elif approval_date <= date(2015, 8, 8):
            return RsuTaxScheme.QUALIFIED_RSU
        elif approval_date <= date(2017, 1, 1):
            return RsuTaxScheme.MACRON_1_RSU
        elif approval_date <= date(2018, 1, 1):
            return RsuTaxScheme.MACRON_2_RSU
        else:
            return RsuTaxScheme.MACRON_3_RSU

    ## IMPORTANT! approval_date here is used to determine the taxation scheme
    # (Macron I, Macron II, etc.) so it needs to be the date where the plan was
    # approved by the shareholders, NOT the grant date.
    def rsu_plan(self, name: str, approval_date: date, symbol: str, currency: str) -> None:
        if name not in self.rsu_plans:
            self.rsu_plans[name] = RsuPlan(
                name=name,
                approval_date=approval_date,
                taxation_scheme=StockHelper._determine_rsu_plans_type(approval_date),
                stock_symbol=symbol,
                currency=currency
            )

    def rsu_vesting(self, symbol: str, plan_name: str, count: int, acq_date: date, acq_price: float,
                    currency: str = None) -> None:
        if not currency:
            currency = self.rsu_plans[plan_name].currency
        self.rsus[symbol].append(StockGroup(
            count=count,
            available=count,  # new acquisition, so everything available
            acq_price=acq_price,
            acq_price_eur=cc.convert(acq_price, currency, "EUR", date=acq_date),
            acq_date=acq_date,
            plan_name=plan_name
        ))
        self.rsus[symbol].sort(key=lambda a: a.acq_date)

    def add_espp(self, symbol: str, count: int, acq_date: date, acq_price: float, currency: str) -> None:
        self.espp_stocks[symbol].append(StockGroup(
            count=count,
            available=count,  # new acquisition, so everything available
            acq_price=acq_price,
            acq_price_eur=cc.convert(acq_price, currency, "EUR", date=acq_date),
            acq_date=acq_date,
            plan_name="espp"
        ))
        self.espp_stocks[symbol].sort(key=lambda a: a.acq_date)

    def add_stockoptions(self, symbol: str, plan_name: str, count: int, vesting_date: date,
                         strike_price: float, currency: str) -> None:
        self.stock_options[symbol].append(StockGroup(
            count=count,
            available=count,  # new acquisition, so everything available
            acq_price=strike_price if currency != "EUR" else None,  # only set one of the two acquisition prices...
            acq_price_eur=strike_price if currency == "EUR" else None,
            # ...if conversion is needed, it will happen at sale time
            acq_date=vesting_date,
            plan_name=plan_name
        ))
        self.stock_options[symbol].sort(key=lambda a: a.acq_date)

    # turn into static constructor?
    def parse_tsv_info(self, tsv_files: str = 'personal_data/*.tsv') -> None:
        def parse_date(some_date):
            try:
                return datetime.strptime(some_date, "%d %b %Y").date()
            except ValueError:
                return datetime.strptime(some_date, "%Y-%m-%d").date()

        # read all files found in tsv_files (glob format)
        rsu_data = []
        for tsv_name in glob.glob(tsv_files):
            print("Opening ", tsv_name)
            with open(tsv_name) as tsv_file:
                tsv_data = csv.DictReader(tsv_file, delimiter="\t")
                for row in tsv_data:
                    plan_name = row["Plan name"]
                    stock_type = row["Stock type"]
                    currency = row["Currency"]
                    symbol = row["Symbol"]
                    acq_count = int(float(row["Count"].replace('\u202f', '')))
                    acq_price = float(row["Acquisition price"])
                    acq_date = parse_date(row["Acquisition date"])
                    if stock_type == "RSU":
                        if plan_name not in self.rsu_plans:
                            plan_date = parse_date(row["Plan date"])
                            self.rsu_plan(plan_name, plan_date, symbol, currency)
                        self.rsu_vesting(symbol, plan_name, acq_count, acq_date, acq_price, currency)
                    elif stock_type == "ESPP":
                        self.add_espp(symbol, acq_count, acq_date, acq_price, currency)
                    elif stock_type == "StockOption":
                        self.add_stockoptions(symbol, plan_name, acq_count, acq_date, acq_price, currency)

    ####### stock selling related load functions #######

    def sell_stockoptions(self, owner: int, symbol: str, nb_stocks: int, sell_date: date, sell_price: float, fees: float,
                          currency: str = "EUR") -> int:
        if nb_stocks == 0:
            return 0
        sell_price_eur = round(cc.convert(sell_price, currency, "EUR", date=sell_date), 2)
        to_sell = nb_stocks
        stocks_before_sell_date = [r for r in self.stock_options[symbol] if r.acq_date < sell_date]
        for i, acq in enumerate(stocks_before_sell_date):
            if acq.available == 0:
                continue
            sell_from_acq = min(to_sell, acq.available)
            strike_price_eur = acq.acq_price_eur if acq.acq_price_eur else cc.convert(acq.acq_price, currency, "EUR",
                                                                                      date=sell_date)
            self.sell_stockoptions_2(
                symbol=symbol,
                nb_stocks_sold=sell_from_acq,
                unit_acquisition_price=strike_price_eur,  # re-using this field to store the strike price
                sell_date=sell_date,
                sell_price_eur=sell_price_eur,
                owner=owner
            )
            # update the stock options data with new availability
            self.stock_options[symbol][i].available = acq.available - sell_from_acq
            to_sell -= sell_from_acq
            if to_sell == 0:
                break
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have ({to_sell})")
        return nb_stocks - to_sell

    def sell_stockoptions_2(self, symbol: str, nb_stocks_sold: int, unit_acquisition_price: float,
                sell_date: date, sell_price_eur: float, owner: int):
        self.stock_sales[sell_date.year].append(SaleEvent(
            symbol=symbol,
            stock_type=StockType.STOCKOPTIONS,
            nb_stocks_sold=nb_stocks_sold,
            unit_acquisition_price=round(unit_acquisition_price, 2),
            sell_date=sell_date,
            sell_price_eur=sell_price_eur,
            selling_fees=0,
            owner=owner,
        ))
    def sell_espp(self, symbol: str, nb_stocks: int, sell_date: date, sell_price: float, fees: float,
                  currency: str = "EUR") -> int:
        if nb_stocks == 0:
            return 0
        sell_price_eur = round(cc.convert(sell_price, currency, "EUR", date=sell_date), 2)
        to_sell = nb_stocks
        stocks_before_sell_date = [r for r in self.espp_stocks[symbol] if r.acq_date < sell_date]
        for i, acq in enumerate(stocks_before_sell_date):
            if acq.available == 0:
                continue
            sell_from_acq = min(to_sell, acq.available)
            self.espp_stocks[symbol][i].available = acq.available - sell_from_acq
            to_sell -= sell_from_acq
            self.sell_espp_2(
                symbol=symbol,
                nb_stocks_sold=sell_from_acq,
                unit_acquisition_price=acq.acq_price_eur,
                sell_date=sell_date,
                sell_price_eur=sell_price_eur
            )
            if to_sell == 0:
                break
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have")
        return nb_stocks - to_sell

    def sell_espp_2(self, symbol: str, nb_stocks_sold: int, unit_acquisition_price: float,
                sell_date: date, sell_price_eur: float):
        self.stock_sales[sell_date.year].append(SaleEvent(
            symbol=symbol,
            stock_type=StockType.ESPP,
            nb_stocks_sold=nb_stocks_sold,
            unit_acquisition_price=round(unit_acquisition_price, 2),
            sell_date=sell_date,
            sell_price_eur=sell_price_eur,
            selling_fees=0,
        ))


    def sell_rsus(self, symbol: str, nb_stocks: int, sell_date: date, sell_price: float, fees: float,
                  currency: str = "EUR") -> int:
        if nb_stocks == 0:
            return 0
        sell_price_eur = round(cc.convert(sell_price, currency, "EUR", date=sell_date), 2)
        to_sell = nb_stocks

        # Acquisitions are sorted by date, this is the rule set by the tax office (FIFO, or PEPS="premier entré premier
        # sorti"); we only keep stocks acquired *before* the sell date, in case we input a sell event in the middle of
        # acquisitions.
        rsu_before_sell_date = [r for r in self.rsus[symbol] if r.acq_date < sell_date]
        if not rsu_before_sell_date:
            # no rsu for that date
            return 0
        for i, acq in enumerate(rsu_before_sell_date):
            if acq.available == 0:
                continue
            sell_from_acq = min(to_sell, acq.available)
            tax_scheme = self.rsu_plans[acq.plan_name].taxation_scheme
            self.sell_rsus_2(
                symbol=symbol,
                nb_stocks_sold=sell_from_acq,
                acq_date=acq.acq_date,
                unit_acquisition_price=acq.acq_price_eur,
                sell_date = sell_date,
                sell_price_eur=sell_price_eur,
                tax_scheme=tax_scheme
            )
            # update the rsu data with new availability (tuples are immutable, so replace with new one)
            self.rsus[symbol][i].available = acq.available - sell_from_acq
            to_sell -= sell_from_acq
            if to_sell == 0:
                break
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have ({to_sell})")
        return (nb_stocks - to_sell)

    def sell_rsus_2(self, symbol: str, nb_stocks_sold: int, acq_date: date, unit_acquisition_price: float,
                sell_date: date, sell_price_eur: float, tax_scheme: RsuTaxScheme):
        self.stock_sales[sell_date.year].append(SaleEvent(
            symbol=symbol,
            stock_type=StockType.RSU,
            nb_stocks_sold=nb_stocks_sold,
            unit_acquisition_price=round(unit_acquisition_price, 2),
            sell_date=sell_date,
            sell_price_eur=sell_price_eur,
            selling_fees=0,
            owner=None,
            rsu_tax_scheme=tax_scheme,
            acq_date=acq_date
        ))


    ####### tax computation functions #######

    # the bible of acquisition and capital gain tax (version 2021):
    # https://www.impots.gouv.fr/portail/www2/fichiers/documentation/brochure/ir_2021/pdf_som/09-plus_values_141a158.pdf
    def compute_acquisition_gain_tax(self, year: int):
        sell_events = self.stock_sales[year]
        taxable_gain = 0  # this would contribute to box 1TZ
        rebates = 0  # this would contribute to box 1UZ
        rebates_50p = 0  # this would contribute to box 1WZ
        other_taxable_gain_1 = 0  # this would contribute to box 1TT
        other_taxable_gain_2 = 0  # this would contribute to box 1UT

        for sale in sell_events:
            if sale.stock_type == StockType.STOCKOPTIONS:
                # exercise gain only applies to Stock Options
                # /!\ only stock options attributed after 28/09/2012 are supported

                # Note: strike price is stored in unit_acquisition_price
                exercise_gain_eur = sale.nb_stocks_sold * (sale.sell_price_eur - sale.unit_acquisition_price)
                if sale.owner == 1:
                    other_taxable_gain_1 += exercise_gain_eur
                elif sale.owner == 2:
                    other_taxable_gain_2 += exercise_gain_eur
                else:
                    raise Exception(
                        f"Owner must be 1 or 2, not {sale.owner} (type={type(sale.owner)}")
            elif sale.stock_type == StockType.RSU:
                # acquisition gain only applies to RSU
                sell_date = sale.sell_date
                sell_date_minus_2y = sell_date + relativedelta(years=-2)
                sell_date_minus_8y = sell_date + relativedelta(years=-8)
                taxation_scheme = sale.rsu_tax_scheme
                acq_date = sale.acq_date
                gain_eur = sale.nb_stocks_sold * sale.unit_acquisition_price
                # gain tax
                if taxation_scheme in (RsuTaxScheme.MACRON_1_RSU, RsuTaxScheme.MACRON_2_RSU):
                    # 50% rebates btw 2 and 8y retention, 65% above 8y
                    if acq_date <= sell_date_minus_8y:
                        taxable_gain += gain_eur * 0.35
                        rebates += gain_eur * 0.65
                    elif acq_date <= sell_date_minus_2y:
                        taxable_gain += gain_eur * 0.5
                        rebates += gain_eur * 0.5
                    else:
                        taxable_gain += gain_eur  # too recent to have a rebate
                elif taxation_scheme == RsuTaxScheme.MACRON_3_RSU:
                    # 50% rebate
                    taxable_gain += gain_eur * 0.5
                    rebates_50p += gain_eur * 0.5
                else:
                    raise Exception(f"Unsupported tax scheme: {taxation_scheme}")

        return {
            "taxable_acquisition_gain_1TZ": round(taxable_gain),
            "acquisition_gain_rebates_1UZ": round(rebates),
            "acquisition_gain_50p_rebates_1WZ": round(rebates_50p),
            "exercise_gain_1_1TT": round(other_taxable_gain_1),
            "exercise_gain_2_1UT": round(other_taxable_gain_2)
        }

    # the other bible of capital gain tax (aka notice for form 2074):
    # # https://www.impots.gouv.fr/portail/files/formulaires/2074/2021/2074_3442.pdf
    def compute_capital_gain_tax(self, year: int):
        tax_report = {
            "2074": [],
            "2042C": {}
        }
        sell_events = self.stock_sales[year]
        total_capital_gain = 0
        for sale in sell_events:
            if sale.stock_type == StockType.STOCKOPTIONS:
                # stock option is "exercise and sold" immediately so there is no capital gain
                continue
            sell_event_report = {}
            sell_event_report["selling_date_512"] = sale.sell_date
            sell_event_report["sell_price_514"] = sale.sell_price_eur
            sell_event_report["sold_stock_units_515"] = sale.nb_stocks_sold
            global_selling_proceeds = sale.sell_price_eur * sale.nb_stocks_sold
            sell_event_report["global_selling_proceeds_516"] = round(global_selling_proceeds)
            sell_event_report["selling_fees_517"] = round(sale.selling_fees)
            net_selling_proceeds = round(global_selling_proceeds - sale.selling_fees)
            sell_event_report["net_selling_proceeds_518"] = net_selling_proceeds
            sell_event_report["unit_acquisition_price_520"] = sale.unit_acquisition_price
            global_acquisition_cost = round(sale.unit_acquisition_price * sale.nb_stocks_sold)
            sell_event_report["global_acquisition_cost_521"] = global_acquisition_cost
            sell_event_report["acquisition_fees_522"] = 0  # TODO: check how to report this, if we need to support it
            total_acquisition_cost = global_acquisition_cost + sell_event_report["acquisition_fees_522"]
            sell_event_report["total_acquisition_cost_523"] = total_acquisition_cost
            result = round(net_selling_proceeds - total_acquisition_cost)
            sell_event_report["result_524"] = result
            tax_report["2074"].append(sell_event_report)
            total_capital_gain += result
        if total_capital_gain >= 0:
            tax_report["2042C"]["capital_gain_3VG"] = total_capital_gain
        else:
            tax_report["2042C"]["capital_loss_3VH"] = -total_capital_gain
        return tax_report

    def estimate_tax(self, acquisition_gain_info, capital_gain_info, marginal_tax_rate) -> Tuple[int, int]:
        exercise_gain_1_1TT = acquisition_gain_info.get("exercise_gain_1_1TT", 0)
        exercise_gain_2_1UT = acquisition_gain_info.get("exercise_gain_2_1UT", 0)
        acquisition_gain_rebates_1UZ = acquisition_gain_info.get("acquisition_gain_rebates_1UZ", 0)
        acquisition_gain_50p_rebates_1WZ = acquisition_gain_info.get("acquisition_gain_50p_rebates_1WZ", 0)
        taxable_acquisition_gain_1TZ = acquisition_gain_info.get("taxable_acquisition_gain_1TZ", 0)
        capital_gain_3VG = capital_gain_info.get("2042C", {}).get("capital_gain_3VG", 0)

        taxable_income = (exercise_gain_1_1TT + exercise_gain_2_1UT) * 0.9 + taxable_acquisition_gain_1TZ
        csgcrds_base = taxable_acquisition_gain_1TZ + acquisition_gain_rebates_1UZ + acquisition_gain_50p_rebates_1WZ + capital_gain_3VG
        activity_income_crds_base = exercise_gain_1_1TT + exercise_gain_2_1UT
        salary_contrib_10p_base = exercise_gain_1_1TT + exercise_gain_2_1UT

        incremental_income_tax = round(taxable_income * marginal_tax_rate)
        incremental_capital_tax = round(capital_gain_3VG * 0.128)
        incremental_social_tax = round(
            (csgcrds_base + activity_income_crds_base) * 0.097 +
            csgcrds_base * 0.075 +
            salary_contrib_10p_base * 0.1
        )
        return incremental_income_tax + incremental_capital_tax, incremental_social_tax

    @staticmethod
    def helper_capital_gain_tax(tax_report):
        form_2042c = tax_report["2042C"]
        print(f"Form 2042C:")
        if "capital_loss_3VH" in form_2042c:
            print(f" * 3VH: {form_2042c['capital_loss_3VH']}")
            print(f"(no need for form 2074)")
            return

        capital_gain = form_2042c["capital_gain_3VG"]
        print(f" * 3VG: {capital_gain}")

        print(f"Form 2074:")
        for i, sell_event_report in enumerate(tax_report["2074"]):
            print(f" Selling event #{i + 1}:")
            print(f" * 512: {sell_event_report['selling_date_512']}")
            print(f" * 514: {sell_event_report['sell_price_514']}")
            print(f" * 515: {sell_event_report['sold_stock_units_515']}")
            print(f" * 516: {sell_event_report['global_selling_proceeds_516']}")
            print(f" * 517: {sell_event_report['selling_fees_517']}")
            print(f" * 518: {sell_event_report['net_selling_proceeds_518']}")
            print(f" * 520: {sell_event_report['unit_acquisition_price_520']}")
            print(f" * 521: {sell_event_report['global_acquisition_cost_521']}")
            print(f" * 522: {sell_event_report['acquisition_fees_522']}")
            print(f" * 523: {sell_event_report['total_acquisition_cost_523']}")
            print(f" * 524: {sell_event_report['result_524']}")
            print("-----------")
        print(f" * 903: {capital_gain}")
        print(f" * 913: {capital_gain}")
