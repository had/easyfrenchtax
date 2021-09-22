from datetime import date,datetime
from dateutil.relativedelta import relativedelta
from currency_converter import CurrencyConverter
from collections import defaultdict
import csv
import glob


# currency converter (USD/EUR in particular)
cc = CurrencyConverter()

class RsuHelper:
    def __init__(self):
        self.rsu_plans = {}
        self.rsus = []
        self.rsu_sales = defaultdict(list)

####### RSU related load functions #######
    def _determine_rsu_plans_type(gdate):
        if gdate <= date(2012,9,27):
            return "2007"
        elif gdate <= date(2015,8,8):
            return "2012"
        elif gdate <= date(2017,1,1):
            return "2015"
        elif gdate <= date(2018,1,1):
            return "2017"
        else:
            return "2018"

    def rsu_plan(self, name, date, symbol, currency):
        if name not in self.rsu_plans:
            self.rsu_plans[name] = {
                "grant_date": date,
                "taxation_scheme": RsuHelper._determine_rsu_plans_type(date),
                "stock_symbol": symbol,
                "price_currency": currency
            }        

    def rsu_vesting(self, plan_name, acq_count, acq_date, acq_price, currency = None):
        if not currency:
            currency = self.rsu_plans[plan_name]["price_currency"]
        self.rsus.append({
            "plan_name": plan_name,
            "count": acq_count,
            "available": acq_count, # new acquisition, so everything available
            "price": acq_price,
            "price_eur": cc.convert(acq_price, currency, "EUR", date = acq_date),
            "date": acq_date
        })
        
    def parse_rsu_tsv(self, tsv_files='personal_data/rsu_*.tsv'):
        # read all files found in tsv_files (glob format)
        rsu_data = []
        for tsv_name in glob.glob(tsv_files):    
            print("Opening ", tsv_name)
            with open(tsv_name) as tsv_file:
                tsv_data = csv.DictReader(tsv_file, delimiter="\t")
                for row in tsv_data:
                    plan_name = row["Plan name"]
                    if plan_name in self.rsu_plans:
                        currency = self.rsu_plans[plan_name]["price_currency"]
                    else:
                        plan_date = datetime.strptime(row["Plan date"], "%d %b %Y").date()
                        symbol = row["Stock"]
                        currency = row["Currency"]
                        self.rsu_plan(plan_name, plan_date, symbol, currency)
                    acq_count = int(row["Count"].replace('\u202f', ''))
                    acq_price = float(row["Acquisition value"])
                    acq_date = datetime.strptime(row["Vesting date"], "%d %b %Y").date()
                    self.rsu_vesting(plan_name, acq_count, acq_date, acq_price, currency)
        self.rsus.sort(key=lambda a: a["date"])

####### stock selling related load functions #######
    def compute_weighted_average_prices(self, up_to):
        # There are complex rules of computing weighted average price (WAP, or PMP in French), see:
        # https://bofip.impots.gouv.fr/bofip/3619-PGP.html/identifiant=BOI-RPPM-PVBMI-20-10-20-40-20191220#Regle_du_prix_moyen_pondere_10
        # Basically, we need to compute a weighted average of all *available* stock, up to the provided date (sell date).
        # When some stocks have already been part of a computation for a previous sell event, we re-use the then computed WAP (aka PMP), and update it.    
        total = 0
        count = 0
        rsu_up_to_date = [r for r in self.rsus if r["date"] < up_to]
        for acq in rsu_up_to_date:
            price = acq.get("weight_averaged_price", acq["price_eur"]) # get WAP, fallback on price_eur if it's the first time we're computing it
            acq_count = acq["available"]
            total += acq_count * price
            count += acq_count
        weight_averaged_price = total / count
        for acq in rsu_up_to_date:
            acq["weight_averaged_price"] = weight_averaged_price
        
    # TODO differentiate by stock_symbol
    def sell_rsus(self, nb_stocks, sell_date, sell_price, fees, currency="EUR"):
        if nb_stocks == 0:
            return
        sell_details = []
        sell_price_eur = round(cc.convert(sell_price, currency, "EUR", date = sell_date),2) # TODO: generalize the USD
        to_sell = nb_stocks
        # we need to compute weighted average prices of our stocks up to the sell date, for future tax accounting
        self.compute_weighted_average_prices(up_to = sell_date)
        # we keep track of weighted average price, there should be only one - this is probably a useless check...
        wap_prices = set()
        # acquisitions are sorted by date, this is the rule set by the tax office (FIFO, or PEPS="premier entré premier sorti")
        # we only keep stocks acquired *before* the sell date, in case we input a sell event in the middle of acquisitions
        for acq in [r for r in self.rsus if r["date"] < sell_date]:
            if acq["available"] == 0:
                continue
            sell_from_acq = min(to_sell, acq["count"])
            plan = self.rsu_plans[acq["plan_name"]]
            sell_details.append({
                "taxation_scheme": plan["taxation_scheme"],
                "count": sell_from_acq,
                "acq_price": acq["price"],
                "acq_date": acq["date"]
            })
            wap_prices.add(acq["weight_averaged_price"])
            acq["available"] -= sell_from_acq
            to_sell -= sell_from_acq
            if to_sell == 0:
                break
        assert(len(wap_prices)==1) # sanity check
        if to_sell > 0:
            print(f"WARNING: You are trying to sell more stocks ({nb_stocks}) than you have ({to_sell})")
        weight_averaged_price = wap_prices.pop()        
        self.rsu_sales[sell_date.year].append({
            "nb_stocks_sold": nb_stocks-to_sell,
            "weight_averaged_price": round(weight_averaged_price,2),
            "sell_date": sell_date,
            "sell_price_eur": sell_price_eur,
            "sell_details": sell_details,
            "selling_fees": round(cc.convert(fees, currency, "EUR", date = sell_date),2)
        })
        return ((nb_stocks-to_sell), weight_averaged_price, sell_details)

####### tax computation functions #######
    
    # the bible of acquisition and capital gain tax (version 2021):
    # https://www.impots.gouv.fr/portail/www2/fichiers/documentation/brochure/ir_2021/pdf_som/09-plus_values_141a158.pdf
    def compute_acquisition_gain_tax(self, year):
        sell_events = self.rsu_sales[year]
        taxable_gain = 0       # this would contribute to box 1TZ
        rebates = 0            # this would contribute to box 1UZ
        rebates_50p = 0        # this would contribute to box 1WZ
        other_taxable_gain = 0 # this would contribute to boxes 1TT/1UT

        for sale in sell_events:
            sell_date = sale["sell_date"]
            sell_date_minus_2y = sell_date + relativedelta(years=-2)
            sell_date_minus_8y = sell_date + relativedelta(years=-8)
            for sale_detail in sale["sell_details"]:
                tax_scheme = sale_detail["taxation_scheme"]
                acq_date = sale_detail["acq_date"]
                usd_eur = cc.convert(1, "USD", "EUR", date = acq_date)
                gain_eur = sale_detail["count"] * sale_detail["acq_price"] * usd_eur
                # gain tax
                if tax_scheme == "2015" or tax_scheme == "2017":
                    # 50% rebates btw 2 and 8y retention, 65% above 8y
                    if acq_date <= sell_date_minus_8y:
                        taxable_gain += gain_eur * 0.65
                        rebates += gain_eur * 0.35
                    elif acq_date <= sell_date_minus_2y:
                        taxable_gain += gain_eur * 0.5
                        rebates += gain_eur * 0.5
                    else:
                        taxable_gain += gain_eur #too recent to have a rebate
                elif tax_scheme == "2018":
                    # 50% rebate
                    taxable_gain += gain_eur * 0.5
                    rebates_50p += gain_eur * 0.5
                else:
                    raise Exception(f"Unsupported tax scheme: {tax_scheme}")  

        return {
            "taxable_acquisition_gain_1TZ": round(taxable_gain),
            "acquisition_gain_rebates_1UZ": round(rebates),
            "acquisition_gain_50p_rebates_1WZ": round(rebates_50p),
            "other_taxable_gain_1TT_1UT": other_taxable_gain
        }
    
    # the other bible of capital gain tax (aka notice for form 2074):
    # # https://www.impots.gouv.fr/portail/files/formulaires/2074/2021/2074_3442.pdf
    def compute_capital_gain_tax(self, year):
        tax_report = {
            "2074": [],
            "2042C": {}
        }
        sell_events = self.rsu_sales[year]
        total_capital_gain = 0
        for sale in sell_events:
            sell_event_report = {}
            sell_event_report["selling_date_512"] = sale['sell_date']
            sell_event_report["sell_price_514"] = sale['sell_price_eur']
            sell_event_report["sold_stock_units_515"] = sale['nb_stocks_sold']
            global_selling_proceeds = sale['sell_price_eur'] * sale['nb_stocks_sold']
            sell_event_report["global_selling_proceeds_516"] = global_selling_proceeds
            sell_event_report["selling_fees_517"] = sale['selling_fees']
            net_selling_proceeds = global_selling_proceeds - sale['selling_fees']
            sell_event_report["net_selling_proceeds_518"] = net_selling_proceeds
            sell_event_report["unit_acquisition_price_520"] = sale['weight_averaged_price']
            global_acquisition_cost = round(sale['weight_averaged_price'] * sale['nb_stocks_sold'])
            sell_event_report["global_acquisition_cost_521"] = global_acquisition_cost
            sell_event_report["acquisition_fees_522"] = 0 # TODO: check how to report this, if we need to support it
            total_acquisition_cost = global_acquisition_cost + sell_event_report["acquisition_fees_522"]
            sell_event_report["total_acquisition_cost_523"] = total_acquisition_cost
            result = net_selling_proceeds - total_acquisition_cost
            sell_event_report["result_524"] = result
            tax_report["2074"].append(sell_event_report)
            total_capital_gain += result
        if total_capital_gain > 0:
            tax_report["2042C"]["capital_gain_3VG"] = total_capital_gain
        else:
            tax_report["2042C"]["capital_loss_3VH"] = -total_capital_gain
        return tax_report
    
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
            print(f" Selling event #{i+1}:")
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

        