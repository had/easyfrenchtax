from collections import defaultdict, namedtuple
from enum import Enum


class TaxInfoFlag(Enum):
    FEE_REBATE_INCOME_1 = "[1] Hit ceiling for fees rebate on income"
    FEE_REBATE_INCOME_2 = "[2] Hit ceiling for fees rebate on income"
    MARGINAL_TAX_RATE = "Marginal tax rate"
    FAMILY_QUOTIENT_CAPPING = "Capped family quotient benefices"
    CHILD_DAYCARE_CREDIT_CAPPING = "Capped child daycare tax credit"
    HOME_SERVICES_CREDIT_CAPPING = "Capped home services tax credit"
    GLOBAL_FISCAL_ADVANTAGES = "Global fiscal advantages"
    CHARITY_75P = "Charity donation resulting in 75% reduction"
    CHARITY_66P = "Charity donation resulting in 66% reduction"
    RENTAL_DEFICIT_CARRYOVER = "Rental income deficit to carry-over next years"

# Lots of parameters evolve year after year (inflation, political decisions, etc.)
# This dictionary gathers all variable parameters.
TaxParameters = namedtuple("TaxParameters", [
    "family_quotient_benefices_capping",   # Source: https://www.economie.gouv.fr/particuliers/quotient-familial
    "slices_thresholds", "slices_rates",   # Source: https://www.service-public.fr/particuliers/vosdroits/F1419
    "fees_10p_deduction_ceiling"           # Source: https://www.impots.gouv.fr/particulier/questions/comment-puis-je-beneficier-de-la-deduction-forfaitaire-de-10
] )
yearly_defined_parameters = {
    2021: TaxParameters(
        family_quotient_benefices_capping=1570,
        slices_thresholds=[10084, 25710, 73516, 158122],
        slices_rates=[0.11, 0.30, 0.41, 0.45],
        fees_10p_deduction_ceiling=12652

    ),
    2022: TaxParameters(
        family_quotient_benefices_capping=1592,
        slices_thresholds=[10225, 26070, 74545, 160336],
        slices_rates=[0.11, 0.30, 0.41, 0.45],
        fees_10p_deduction_ceiling=12829
    ),
}

class TaxSimulator:
    def __init__(self, statement_year, tax_input, debug=False):
        self.parameters = yearly_defined_parameters[statement_year]
        self.flags = {}
        self.debug = debug
        self.state = defaultdict(int, tax_input)
        self.state["year"] = statement_year
        self.process_family_information()
        self.compute_rental_income()
        self.compute_net_income()
        self.compute_taxable_income()
        self.compute_flat_rate_taxes()
        self.compute_reference_fiscal_income()
        self.compute_tax_before_reductions()
        self.compute_tax_reductions()
        self.compute_tax_credits()
        self.compute_capital_taxes()
        self.compute_net_taxes()
        self.compute_social_taxes()

    def process_family_information(self):
        # See https://www.service-public.fr/particuliers/vosdroits/F2705 and https://www.service-public.fr/particuliers/vosdroits/F2702
        # /!\ extra half-shares and shared custody are not taken into account
        # TODO: single individual taxation is not properly computed right now
        if not self.state["married"]:
            # better raising exception than reporting something wrong
            raise Exception("Non-married situation is buggy for now")
        base_shares = 2 if self.state["married"] else 1
        nb_children_1 = min(self.state["nb_children"], 2)
        nb_children_2 = max(0, self.state["nb_children"] - nb_children_1)
        self.state["household_shares"] = base_shares + nb_children_1 * 0.5 + nb_children_2
        # counting children aged less than 6 years old
        nb_children_lt_6yo = 0
        for i in range(1,6):
            child_birthyear_key = f"child_{i}_birthyear"
            if child_birthyear_key in self.state:
                # counting from year-1, (i.e. if declaring in 2022, checking age on Jan 1st 2021)
                if self.state["year"] - 1 - self.state[child_birthyear_key] <= 6:
                    nb_children_lt_6yo += 1
        self.state["nb_children_lt_6yo"] = nb_children_lt_6yo

    def compute_rental_income(self):
        # French tax system considers only non-furnished apartments to be "rental income". Furnished apartments are
        # part of commercial incomes (BIC in the tax system, for "bénéfices industriels et commerciaux").
        #
        # Net rental income can be determined in 2 ways, a simplified reporting (subject to eligibility criteria) or the
        # default reporting. The simplified tax regime ("micro-foncier") of reporting requires income to be less than a
        # ceiling (15'000€ so far), and having no special deduction plans. Otherwise, by default, the "régime réel"
        # requires to compute the net result and in case it's negative, split charges between what's eligible for global
        # income deduction vs. what is to be deduced from future rental income (can be carried over for 10 years).
        # These 2 ways are mutually exclusive, so the code raises exceptions here.
        # Sources: https://www.impots.gouv.fr/particulier/location-vide-de-meubles
        #          https://www.impots.gouv.fr/particulier/questions/je-mets-en-location-un-logement-vide-comment-declarer-les-loyers-percus
        #          https://www.impots.gouv.fr/sites/default/files/media/3_Documentation/depliants/nid_4009_gp_172.pdf
        # NOT SUPPORTED: income from foreign countries (4BK and 4BL)

        simplified_income_reporting = self.state["simplified_rental_income_4BE"]
        net_profit = self.state["real_rental_profit_4BA"]
        deficit = self.state["real_rental_income_deficit_4BB"]
        global_deficit = self.state["rental_income_global_deficit_4BC"]
        previous_deficit = self.state["previous_rental_income_deficit_4BD"]

        if simplified_income_reporting:
            if net_profit or deficit or global_deficit or previous_deficit:
                raise Exception("The simplified rental income reporting (4BE) cannot be combined with the default rental income reporting (4BA 4BB 4BC)")
            if simplified_income_reporting > 15000:
                raise Exception("Simplified rental income reporting (4BE) cannot exceed 15'000€")
            final_net_profit = simplified_income_reporting * 0.7 # 30% rebate automatically applied
            final_deficit_carryover = 0
        elif net_profit:
            if deficit or global_deficit:
                raise Exception("Rental profit reporting (4BA) cannot be combined with rental deficit reporting(4BB 4BC)")
            final_net_profit = max(net_profit-previous_deficit, 0)
            final_deficit_carryover = max(0, previous_deficit-net_profit)
        else:
            if global_deficit > 10700:
                raise Exception("Rental deficit for global deduction (4BC) cannot exceed 10'700€")
            final_net_profit = -global_deficit
            final_deficit_carryover = deficit + previous_deficit

        self.state["rental_income_result"] = final_net_profit
        if final_deficit_carryover:
            self.state["rental_deficit_carryover"] = final_deficit_carryover
            self.flags[TaxInfoFlag.RENTAL_DEFICIT_CARRYOVER] = f"{final_deficit_carryover}€"

    def compute_net_income(self):
        incomes_1 = self.state["salary_1_1AJ"] + self.state["exercise_gain_1_1TT"]
        incomes_2 = self.state["salary_2_1BJ"] + self.state["exercise_gain_2_1UT"]
        # capped at 12652e (in 2021), see:
        # https://www.impots.gouv.fr/portail/particulier/questions/comment-puis-je-beneficier-de-la-deduction-forfaitaire-de-10
        # TODO: there is a minimum deduction to consider (448e in 2022)
        fees_10p_ceiling = self.parameters.fees_10p_deduction_ceiling
        self.state["deduction_10p_1"] = round(min(incomes_1 * 0.1, fees_10p_ceiling))
        self.state["deduction_10p_2"] = round(min(incomes_2 * 0.1,
                                                  fees_10p_ceiling))
        if incomes_1 * 0.1 > fees_10p_ceiling:
            self.flags[
                TaxInfoFlag.FEE_REBATE_INCOME_1] = f"taxable income += {round(incomes_1 * 0.1 - fees_10p_ceiling)}€"
        if incomes_2 * 0.1 > fees_10p_ceiling:
            self.flags[
                TaxInfoFlag.FEE_REBATE_INCOME_2] = f"taxable income += {round(incomes_2 * 0.1 - fees_10p_ceiling)}€"
        net_income = incomes_1 - self.state["deduction_10p_1"]\
                     + incomes_2 - self.state["deduction_10p_2"]\
                     + self.state["rental_income_result"]
        self.state["total_net_income"] = net_income

    def compute_taxable_income(self):
        total_per = self.state["per_transfers_1_6NS"] + self.state[
            "per_transfers_2_6NT"]  # TODO take capping into account
        # TODO other deductible charges
        self.state["taxable_income"] = self.state["total_net_income"] - total_per
        self.state["taxable_income"] += self.state["taxable_acquisition_gain_1TZ"]  # Taxable part of RSUs

    def maybe_print(self, *args):
        if self.debug:
            print(*args)

    def compute_flat_rate_taxes(self):
        # supporting 2TR only for now
        # TODO: support others (2DC, 2FU, 2TS, 2TT, 2WW, 2ZZ, 2TQ, 2TZ)
        self.state["taxable_investment_income"] = self.state["fixed_income_interests_2TR"]
        self.state["investment_income_tax"] = round(self.state["taxable_investment_income"] * 0.128)

    def compute_reference_fiscal_income(self):
        self.state["reference_fiscal_income"] = self.state["total_net_income"] + self.state["taxable_investment_income"]\
                                                + self.state["capital_gain_3VG"]

    def _compute_income_tax(self, household_shares):
        # https://www.service-public.fr/particuliers/vosdroits/F1419
        slices_thresholds = self.parameters.slices_thresholds
        slices_rates = self.parameters.slices_rates
        taxable_income = self.state["taxable_income"]
        thresholds = [t * household_shares for t in
                      slices_thresholds]  # scale thresholds to the number of people in the household
        self.maybe_print("Thresholds: ", thresholds)
        self.maybe_print("Shares: ", household_shares)
        tax = 0
        income_accounted_for = thresholds[0]
        bucket_n = 0
        marginal_tax_rate = 0
        while ((taxable_income > income_accounted_for) and (bucket_n < len(thresholds) - 1)):
            self.maybe_print("Accounted for: ", income_accounted_for)
            self.maybe_print("In bucket ", bucket_n)
            bucket_amount = thresholds[bucket_n + 1] - thresholds[bucket_n]
            self.maybe_print("Bucket amount: ", bucket_amount)
            bucket_tax = slices_rates[bucket_n] * min(bucket_amount, taxable_income - income_accounted_for)
            marginal_tax_rate = slices_rates[bucket_n]
            self.maybe_print("Bucket tax: ", bucket_tax)
            tax += bucket_tax
            self.maybe_print("Tax now: ", tax)
            income_accounted_for = thresholds[bucket_n + 1]
            bucket_n += 1
        if taxable_income > income_accounted_for:
            self.maybe_print("We're in the last slice")
            # we're in the last bucket, we apply the last rate to the rest of the income
            tax += slices_rates[-1] * (taxable_income - income_accounted_for)
            marginal_tax_rate = slices_rates[-1]
        self.maybe_print("Total tax before reductions: ", tax)
        return tax, marginal_tax_rate

    # computes the actual progressive tax
    def compute_tax_before_reductions(self):
        capping_parameter = self.parameters.family_quotient_benefices_capping
        household_shares = self.state["household_shares"]
        tax_with_family_quotient, marginal_tax_rate = self._compute_income_tax(household_shares)
        self.flags[TaxInfoFlag.MARGINAL_TAX_RATE] = f"{round(marginal_tax_rate * 100)}%"
        household_shares_without_family_quotient = 2 if self.state["married"] else 1
        tax_without_family_quotient, _ = self._compute_income_tax(household_shares_without_family_quotient)
        # apply capping of the family quotient benefices, see
        # https://www.economie.gouv.fr/particuliers/quotient-familial
        family_quotient_benefices = tax_without_family_quotient - tax_with_family_quotient
        # TODO: this doesn't seem right after 2 children, double check
        family_quotient_benefices_capping = capping_parameter * ((household_shares - 2) * 2)
        self.maybe_print("Family quotient benefices: ", family_quotient_benefices, "  ;  Capped to: ",
                         family_quotient_benefices_capping)
        if (family_quotient_benefices > family_quotient_benefices_capping):
            additional_taxes = family_quotient_benefices - family_quotient_benefices_capping
            self.flags[
                TaxInfoFlag.FAMILY_QUOTIENT_CAPPING] = f"tax += {round(additional_taxes, 2)}€"
            final_income_tax = tax_without_family_quotient - family_quotient_benefices_capping
        else:
            final_income_tax = tax_with_family_quotient
        self.state["simple_tax_right"] = round(final_income_tax) # "Droits simples" in French
        self.state["tax_before_reductions"] = self.state["simple_tax_right"] + self.state["investment_income_tax"]

    # Computes all tax reductions. Currently supported:
    # * donations (7UD)
    # * PME capital subscription (7CF, 7CH)
    def compute_tax_reductions(self):
        # See:
        # https://www.impots.gouv.fr/portail/particulier/questions/jai-fait-des-dons-une-association-que-puis-je-deduire
        # 75% reduction for "Dons aux organismes d'aide aux personnes en difficulté", up to a ceiling ...
        charity_donation_7ud = self.state["charity_donation_7UD"]
        capped_or_not = " (capped)" if charity_donation_7ud > 1000 else ""
        charity_donation_75p = min(charity_donation_7ud, 1000)
        self.flags[TaxInfoFlag.CHARITY_75P] = f"{charity_donation_75p}€{capped_or_not}"
        charity_donation_reduction_75p = charity_donation_75p * 0.75
        # ... then 66% for the rest, plus the "Dons aux organismes d'intérêt général", up to 20% of the taxable income
        charity_donation_7uf = self.state["charity_donation_7UF"]
        donation_leftover = charity_donation_7uf + max(charity_donation_7ud - 1000, 0)
        taxable_income = max(self.state["taxable_income"], 0)
        capped_or_not = " (capped)" if donation_leftover > taxable_income * 0.20 else ""
        charity_donation_66p = round(min(donation_leftover, taxable_income * 0.20))
        charity_donation_reduction_66p = charity_donation_66p * 0.66
        self.flags[TaxInfoFlag.CHARITY_66P] = f"{charity_donation_66p}€{capped_or_not}"
        # Total reduction
        self.state["charity_reduction"] = charity_donation_reduction_75p + charity_donation_reduction_66p

        # Subscription to PME capital: in 2020 there are 2 segments: before and after Aug.10th (with different reduction
        # rates). See:
        # https://www.impots.gouv.fr/portail/particulier/questions/si-jinvestis-dans-une-entreprise-ai-je-droit-une-reduction-dimpot
        # Total is capped at 100K (TODO: tune that value depending on marital state)
        pme_capital_subscription_before = min(self.state["pme_capital_subscription_7CF"], 100000)
        pme_capital_subscription_after = min(self.state["pme_capital_subscription_7CH"],
                                                   100000 - pme_capital_subscription_before)
        self.state["pme_subscription_reduction"] = pme_capital_subscription_before * 0.18\
                                                   + pme_capital_subscription_after * 0.25

    def compute_tax_credits(self):
        # Daycare fees, capped & rated at 50%. See:
        # https://www.impots.gouv.fr/portail/particulier/questions/je-fais-garder-mon-jeune-enfant-lexterieur-du-domicile-que-puis-je-deduire
        nb_children_lt_6yo = self.state["nb_children_lt_6yo"]
        nb_children_with_daycare_fees = 0
        total_fees = 0
        fees_capped_out = 0
        for c in "ABCDEFG":
            fees_key = f"children_daycare_fees_7G{c}"
            if fees_key in self.state:
                nb_children_with_daycare_fees += 1
                if nb_children_with_daycare_fees > nb_children_lt_6yo:
                    raise Exception("You are declaring more children daycare fees than you have children below 6y old")
                total_fees += min(self.state[fees_key], 2300)
                fees_capped_out += max(self.state[fees_key]-2300, 0)
        self.flags[TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING] = f"capped to {total_fees}€ (originally {total_fees+fees_capped_out}€)"
        self.state["children_daycare_taxcredit"] = total_fees * 0.5

        # services at home (cleaning etc.)
        # https://www.impots.gouv.fr/portail/particulier/emploi-domicile
        home_services_capping = min(12000 + 1500 * self.state["nb_children"], 15000)
        home_services = self.state["home_services_7DB"]
        if home_services > home_services_capping:
            self.flags[TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING] = f"capped to {home_services_capping}€"\
                                                                   + f" (originally {home_services}€)"
        capped_home_services = min(home_services, home_services_capping)
        self.state["home_services_taxcredit"] = capped_home_services * 0.5

    def compute_capital_taxes(self):
        # simple, flat tax based (opting for progressive tax with box "2OP" is not supported in this simulator)
        self.state["capital_gain_tax"] = self.state["capital_gain_3VG"] * 0.128

    def compute_net_taxes(self):
        # Tax reductions and credits are in part capped ("Plafonnement des niches fiscales")
        # https://www.service-public.fr/particuliers/vosdroits/F31179
        all_taxes_before_capping = self.state["tax_before_reductions"] \
                                   - self.state["charity_reduction"]
        taxes_with_reduction_before_capping = all_taxes_before_capping \
                                              - self.state["pme_subscription_reduction"]
        partial_taxes_2 = max(taxes_with_reduction_before_capping, 0) \
                          - self.state["children_daycare_taxcredit"] \
                          - self.state["home_services_taxcredit"]

        fiscal_advantages = all_taxes_before_capping - partial_taxes_2
        if fiscal_advantages > 10000:
            self.flags[TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES] = f"capped to 10'000€ (originally {fiscal_advantages}€)"
            net_taxes_after_global_capping = all_taxes_before_capping - 10000
        else:
            self.flags[TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES] = f"{fiscal_advantages}€" +\
                                                               f" (uncapped, {10000 - fiscal_advantages}€ from ceiling)"
            net_taxes_after_global_capping = partial_taxes_2

        net_taxes = net_taxes_after_global_capping + self.state["capital_gain_tax"] - self.state["interest_tax_already_paid_2CK"]
        self.state["net_taxes"] = round(net_taxes, 2)

    def compute_social_taxes(self):
        # stock options
        so_exercise_gains = self.state["exercise_gain_1_1TT"] + self.state["exercise_gain_2_1UT"]
        so_salarycontrib_10p = so_exercise_gains * 0.1
        so_csg = so_exercise_gains * 0.092
        so_crds = so_exercise_gains * 0.005
        so_socialtaxes = so_salarycontrib_10p + so_csg + so_crds
        # capital acquisition (RSUs), capital gain (RSUs and normal stocks)
        rsu_socialtax_base = self.state["capital_gain_3VG"] + self.state["taxable_acquisition_gain_1TZ"] \
                             + self.state["acquisition_gain_rebates_1UZ"] + self.state[
                                 "acquisition_gain_50p_rebates_1WZ"]
        rsu_socialtaxes = rsu_socialtax_base * (0.097 + 0.075)
        investments_interests_csgcrds = (self.state["taxable_investment_income"] - self.state["fixed_income_interests_already_taxed_2BH"]) * (0.1 + 0.075)
        rental_income_base = max(self.state["rental_income_result"], 0)  # rental income result can be negative, but it can't reduce social taxes
        rental_income_socialtaxes = rental_income_base * (0.097 + 0.075)
        self.state["net_social_taxes"] = round(so_socialtaxes + rsu_socialtaxes\
                                               + investments_interests_csgcrds + rental_income_socialtaxes)
