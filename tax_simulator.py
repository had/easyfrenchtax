import math
from collections import defaultdict
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
from currency_converter import CurrencyConverter
import csv
import glob

# currency converter (USD/EUR in particular)
cc = CurrencyConverter()

class TaxSimulator:
    def __init__(self, tax_input, debug = False):
        self.debug = debug
        self.state = defaultdict(int, tax_input)
        self.compute_net_salaries()
        self.compute_taxable_income()
        self.compute_tax_before_reductions()
        self.compute_tax_reductions()
        self.compute_tax_credits()
        self.compute_capital_taxes()
        self.compute_net_taxes()
        self.compute_social_taxes()

    def compute_net_salaries(self):
        incomes_1 = self.state["salary_1_1AJ"] + self.state["so_exercise_gain_1_1TT"]
        incomes_2 = self.state["salary_2_1BJ"] + self.state["so_exercise_gain_2_1UT"]
        self.state["deduction_10p_1"] = round(min(incomes_1 * 0.1, 12652)) # capped at 12652, see:
        self.state["deduction_10p_2"] = round(min(incomes_2 * 0.1, 12652)) # https://www.impots.gouv.fr/portail/particulier/questions/comment-puis-je-beneficier-de-la-deduction-forfaitaire-de-10
        self.state["total_net_salaries"] = incomes_1 - self.state["deduction_10p_1"] + incomes_2 - self.state["deduction_10p_2"]

    def compute_taxable_income(self):
        total_per = self.state["per_transfers_1_6NS"] + self.state["per_transfers_2_6NT"] # TODO take capping into account
        # TODO other deductible charges
        self.state["taxable_income"] = self.state["total_net_salaries"] - total_per
        self.state["taxable_income"] += self.state["acquisition_gain_after_discount_1TZ"] # Taxable part of RSUs

    def maybe_print(self, *args):
        if self.debug:
            print(*args)

    def _compute_income_tax(self, household_shares):
        # https://www.service-public.fr/particuliers/vosdroits/F1419
        slices_thresholds = [10084, 25710, 73516, 158122]
        slices_rates      = [ 0.11,  0.30,  0.41,   0.45]
        taxable_income = self.state["taxable_income"]
        thresholds = [t * household_shares for t in slices_thresholds] # scale thresholds to the number of people in the household
        self.maybe_print("Thresholds: ", thresholds)
        self.maybe_print("Shares: ", household_shares)
        # TODO: improve
        tax = 0
        income_accounted_for = thresholds[0]
        bucket_n = 0
        while ((taxable_income > income_accounted_for) and (bucket_n < len(thresholds)-1)):
            self.maybe_print("Accounted for: ", income_accounted_for)
            self.maybe_print("In bucket ",bucket_n)
            bucket_amount = thresholds[bucket_n+1]-thresholds[bucket_n]
            self.maybe_print("Bucket amount: ", bucket_amount)
            bucket_tax = slices_rates[bucket_n] * min(bucket_amount, taxable_income-income_accounted_for)
            self.maybe_print("Bucket tax: ", bucket_tax)
            tax += bucket_tax
            self.maybe_print("Tax now: ", tax)
            income_accounted_for = thresholds[bucket_n+1]
            bucket_n += 1
        if taxable_income > income_accounted_for:
            self.maybe_print("We're in the last slice")
            # we're in the last bucket, we apply the last rate to the rest of the income
            tax += slices_rates[-1] * (taxable_income - income_accounted_for)
        self.maybe_print("Total tax before reductions: ", tax)
        return tax

    # computes the actual progressive tax
    def compute_tax_before_reductions(self):
        household_shares = self.state["household_shares"]
        tax_with_family_quotient = self._compute_income_tax(household_shares)
        tax_without_family_quotient = self._compute_income_tax(2)
        # apply capping of the family quotient benefices, see
        # https://www.economie.gouv.fr/particuliers/quotient-familial
        family_quotient_benefices = tax_without_family_quotient - tax_with_family_quotient
        family_quotient_benefices_capping = 1570 * ((household_shares-2) * 2)
        self.maybe_print("Family quotient benefices: ", family_quotient_benefices, "  ;  Capped to: ", family_quotient_benefices_capping)
        if (family_quotient_benefices > family_quotient_benefices_capping):
            final_income_tax = tax_without_family_quotient - family_quotient_benefices_capping
        else:
            final_income_tax = tax_with_family_quotient
        self.state["tax_before_reductions"] = round(final_income_tax)

    # Computes all tax reductions. Currently supported:
    # * donations (7UD)
    # * PME capital subscription (7CF, 7CH)
    def compute_tax_reductions(self):
        # See https://www.impots.gouv.fr/portail/particulier/questions/jai-fait-des-dons-une-association-que-puis-je-deduire
        # 75% reduction up to 1000e ...
        donation = self.state["charity_donation_7UD"]
        donation_reduction_75p = min(donation, 1000) * 0.75
        # ... then 66% for the rest, up to 20% of the taxable income
        # TODO check if the 20% capping applies to the donation or the reduction (here it's assumed on the reduction)
        donation_reduction_66p = min(max(donation-1000, 0) * 0.75,self.state["taxable_income"]*0.20)
        self.state["donations_reduction"] = donation_reduction_75p + donation_reduction_66p

        # Subscription to PME capital: in 2020 there are 2 segments: before and after Aug.10th (with different reduction rates)
        # See https://www.impots.gouv.fr/portail/particulier/questions/si-jinvestis-dans-une-entreprise-ai-je-droit-une-reduction-dimpot
        # Total is capped at 100K (TODO: tune that value depending on marital state)
        pme_capital_subscription_before_aug10 = min(self.state["pme_capital_subscription_7CF"], 100000)
        pme_capital_subscription_after_aug10 = min(self.state["pme_capital_subscription_7CH"], 100000-pme_capital_subscription_before_aug10)
        self.state["pme_capital_reduction"] = pme_capital_subscription_before_aug10 * 0.18 + pme_capital_subscription_after_aug10 * 0.25

    def compute_tax_credits(self):
        # Daycare fees, capped & rated at 50%
        # https://www.impots.gouv.fr/portail/particulier/questions/je-fais-garder-mon-jeune-enfant-lexterieur-du-domicile-que-puis-je-deduire
        capped_daycare_fees = min(self.state["children_daycare_fees_7GA"], 2300)
        self.state["children_daycare_taxcredit"] = capped_daycare_fees * 0.5

        # services at home (cleaning etc.)
        # https://www.impots.gouv.fr/portail/particulier/emploi-domicile
        home_services_capping = min(12000 + 1500 * self.state["nb_kids"], 15000)
        capped_home_services = min(self.state["home_services_7DB"], home_services_capping)
        self.state["home_services_taxcredit"] = capped_home_services * 0.5

    def compute_capital_taxes(self):
        self.state["capital_gain_tax"] = self.state["capital_gain_3VG"] * 0.128

    def compute_net_taxes(self):
        # Tax reductions and credits are in part capped ("Plafonnement des niches fiscales")
        # https://www.service-public.fr/particuliers/vosdroits/F31179
        fiscal_advantages = self.state["pme_capital_reduction"] + self.state["children_daycare_taxcredit"] + self.state["home_services_taxcredit"]
        self.state["fiscal_advantages_capping"] = max(fiscal_advantages-10000,0)
        self.state["net_taxes"] = self.state["tax_before_reductions"]\
                                - self.state["donations_reduction"]\
                                - fiscal_advantages\
                                + self.state["fiscal_advantages_capping"]\
                                + self.state["capital_gain_tax"]

    def compute_social_taxes(self):
        # stock options
        so_exercise_gains = self.state["so_exercise_gain_1_1TT"] + self.state["so_exercise_gain_2_1UT"]
        so_salarycontrib_10p = so_exercise_gains * 0.1
        so_csg = so_exercise_gains * 0.092
        so_crds = so_exercise_gains * 0.005
        # capital acquisition, capital gain (RSUs)
        rsu_socialtax_base = self.state["capital_gain_3VG"] + self.state["acquisition_gain_after_discount_1TZ"] + self.state["acquisition_gain_50p_1WZ"]
        rsu_csgcrds = rsu_socialtax_base * 0.097
        rsu_social_contrib = rsu_socialtax_base * 0.075
        self.state["net_social_taxes"] = round(so_salarycontrib_10p + so_csg + so_crds + rsu_csgcrds + rsu_social_contrib)

        
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

        