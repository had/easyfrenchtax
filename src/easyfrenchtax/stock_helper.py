from dataclasses import dataclass
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from currency_converter import CurrencyConverter
from collections import defaultdict
import csv
import glob


@dataclass
class StockGroup:
    owner: int  # taxpayer 1 or 2, typically, for tax statements
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
    taxation_scheme: str
    stock_symbol: str
    currency: str


@dataclass
class SaleEvent:
    symbol: str
    stock_type: str  # TODO change to enum
    nb_stocks_sold: int
    unit_acquisition_price: float # in Euros
    sell_date: date
    sell_price_eur: float
    sell_details: list[dict[str, any]]  # TODO typing of details
    selling_fees: float
    # plan_name: str
    # owner: int
    # acq_date: date



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
    def reset(self, stock_types: list[str] = ("espp", "stockoption", "rsu"), symbols: list[str] = None) -> None:
        for sales in self.stock_sales.values():
            sales[:] = [s for s in sales if
                        (symbols and s.symbol not in symbols) or (s.stock_type not in stock_types)]
        stock_types_mapping = {
            "espp": self.espp_stocks,
            "stockoption": self.stock_options,
            "rsu": self.rsus
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
    def _determine_rsu_plans_type(approval_date: date) -> str:
        if approval_date <= date(2012, 9, 27):
            return "2007"  # TODO replace with an enum
        elif approval_date <= date(2015, 8, 8):
            return "2012"
        elif approval_date <= date(2017, 1, 1):
            return "2015"
        elif approval_date <= date(2018, 1, 1):
            return "2017"
        else:
            return "2018"

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

    def rsu_vesting(self, owner: int, symbol: str, plan_name: str, count: int, acq_date: date, acq_price: float,
                    currency: str = None) -> None:
        if not currency:
            currency = self.rsu_plans[plan_name].currency
        self.rsus[symbol].append(StockGroup(
            owner=owner,
            count=count,
            available=count,  # new acquisition, so everything available
            acq_price=acq_price,
            acq_price_eur=cc.convert(acq_price, currency, "EUR", date=acq_date),
            acq_date=acq_date,
            plan_name=plan_name
        ))
        self.rsus[symbol].sort(key=lambda a: a.acq_date)

    def add_espp(self, owner: int, symbol: str, count: int, acq_date: date, acq_price: float, currency: str) -> None:
        self.espp_stocks[symbol].append(StockGroup(
            owner=owner,
            count=count,
            available=count,  # new acquisition, so everything available
            acq_price=acq_price,
            acq_price_eur=cc.convert(acq_price, currency, "EUR", date=acq_date),
            acq_date=acq_date,
            plan_name="espp"
        ))
        self.espp_stocks[symbol].sort(key=lambda a: a.acq_date)

    def add_stockoptions(self, owner: int, symbol: str, plan_name: str, count: int, vesting_date: date,
                         strike_price: float, currency: str) -> None:
        self.stock_options[symbol].append(StockGroup(
            owner=owner,
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
                    owner = int(row["Owner"])
                    assert (owner == 1 or owner == 2)
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
                        self.rsu_vesting(owner, symbol, plan_name, acq_count, acq_date, acq_price, currency)
                    elif stock_type == "ESPP":
                        self.add_espp(owner, symbol, acq_count, acq_date, acq_price, currency)
                    elif stock_type == "StockOption":
                        self.add_stockoptions(owner, symbol, plan_name, acq_count, acq_date, acq_price, currency)

    ####### stock selling related load functions #######

    def sell_stockoptions(self, symbol: str, nb_stocks: int, sell_date: date, sell_price: float, fees: float,
                          currency: str = "EUR"):
        if nb_stocks == 0:
            return
        sell_details = []
        sell_price_eur = round(cc.convert(sell_price, currency, "EUR", date=sell_date), 2)
        to_sell = nb_stocks
        stocks_before_sell_date = [r for r in self.stock_options[symbol] if r.acq_date < sell_date]
        for i, acq in enumerate(stocks_before_sell_date):
            if acq.available == 0:
                continue
            sell_from_acq = min(to_sell, acq.available)
            strike_price_eur = acq.acq_price_eur if acq.acq_price_eur else cc.convert(acq.acq_price, currency, "EUR",
                                                                                      date=sell_date)
            sell_details.append({
                "owner": acq.owner,
                "plan_name": acq.plan_name,
                "count": sell_from_acq,
                "strike_price_eur": strike_price_eur,
                "acq_date": acq.acq_date
            })
            # update the rsu data with new availability (tuples are immutable, so replace with new one)
            self.stock_options[symbol][i].available = acq.available - sell_from_acq
            to_sell -= sell_from_acq
            if to_sell == 0:
                break
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have ({to_sell})")
        self.stock_sales[sell_date.year].append(SaleEvent(
            symbol=symbol,
            stock_type="stockoption",
            nb_stocks_sold=nb_stocks - to_sell,
            unit_acquisition_price=None,  # not applicable for stock options when doing "exercise and sell"
            sell_date=sell_date,
            sell_price_eur=sell_price_eur,
            sell_details=sell_details,
            selling_fees=round(cc.convert(fees, currency, "EUR", date=sell_date), 2)
        ))
        return ((nb_stocks - to_sell), None, sell_details)

    def sell_espp(self, symbol: str, nb_stocks: int, sell_date: date, sell_price: float, fees: float,
                  currency: str = "EUR"):
        if nb_stocks == 0:
            return
        sell_price_eur = round(cc.convert(sell_price, currency, "EUR", date=sell_date), 2)
        to_sell = nb_stocks
        stocks_before_sell_date = [r for r in self.espp_stocks[symbol] if r.acq_date < sell_date]
        for i, acq in enumerate(stocks_before_sell_date):
            if acq.available == 0:
                continue
            sell_from_acq = min(to_sell, acq.available)
            self.espp_stocks[symbol][i].available = acq.available - sell_from_acq
            to_sell -= sell_from_acq
            self.stock_sales[sell_date.year].append(SaleEvent(
                symbol=symbol,
                stock_type="espp",
                nb_stocks_sold=sell_from_acq,
                unit_acquisition_price=round(acq.acq_price_eur, 2),
                sell_date=sell_date,
                sell_price_eur=sell_price_eur,
                sell_details=[{
                    "plan_name": acq.plan_name,
                    "count": sell_from_acq,
                    "acq_price": acq.acq_price,  # keep price in original currency here
                    "acq_date": acq.acq_date
                }],
                selling_fees=0  # not sure how to handle this
            ))
            if to_sell == 0:
                break
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have")
            return (0, 0, [])
        return (nb_stocks - to_sell)

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
            self.stock_sales[sell_date.year].append(SaleEvent(
                symbol=symbol,
                stock_type="rsu",
                nb_stocks_sold=sell_from_acq,
                unit_acquisition_price=round(acq.acq_price_eur, 2),
                sell_date=sell_date,
                sell_price_eur=sell_price_eur,
                sell_details=[{
                    "plan_name": acq.plan_name,
                    "count": sell_from_acq,
                    "acq_price": acq.acq_price,  # keep price in original currency here
                    "acq_price_currency": "TODO",  # TODO
                    "acq_date": acq.acq_date
                }],
                selling_fees=0  # not sure how to handle this
            ))
            # update the rsu data with new availability (tuples are immutable, so replace with new one)
            self.rsus[symbol][i].available = acq.available - sell_from_acq
            to_sell -= sell_from_acq
            if to_sell == 0:
                break
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have ({to_sell})")
        return (nb_stocks - to_sell)

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
            if sale.stock_type == "stockoption":
                # exercise gain only applies to Stock Options
                # /!\ only stock options attributed after 28/09/2012 are supported
                for sale_detail in sale.sell_details:
                    exercise_gain_eur = sale_detail["count"] * (sale.sell_price_eur - sale_detail["strike_price_eur"])
                    if sale_detail["owner"] == 1:
                        other_taxable_gain_1 += exercise_gain_eur
                    elif sale_detail["owner"] == 2:
                        other_taxable_gain_2 += exercise_gain_eur
                    else:
                        raise Exception(
                            f"Owner must be 1 or 2, not {sale_detail['owner']} (type={type(sale_detail['owner'])}")
            elif sale.stock_type == "rsu":
                # acquisition gain only applies to RSU
                sell_date = sale.sell_date
                sell_date_minus_2y = sell_date + relativedelta(years=-2)
                sell_date_minus_8y = sell_date + relativedelta(years=-8)
                for sale_detail in sale.sell_details:
                    rsu_plan = self.rsu_plans[sale_detail["plan_name"]]
                    taxation_scheme = rsu_plan.taxation_scheme
                    plan_currency = rsu_plan.currency
                    acq_date = sale_detail["acq_date"]
                    gain_eur = sale_detail["count"] * sale.unit_acquisition_price
                    # gain tax
                    if taxation_scheme == "2015" or taxation_scheme == "2017":
                        # 50% rebates btw 2 and 8y retention, 65% above 8y
                        if acq_date <= sell_date_minus_8y:
                            taxable_gain += gain_eur * 0.35
                            rebates += gain_eur * 0.65
                        elif acq_date <= sell_date_minus_2y:
                            taxable_gain += gain_eur * 0.5
                            rebates += gain_eur * 0.5
                        else:
                            taxable_gain += gain_eur  # too recent to have a rebate
                    elif taxation_scheme == "2018":
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
            if sale.stock_type == "stockoption":
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
