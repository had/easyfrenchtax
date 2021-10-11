from collections import defaultdict
from enum import Enum

class TaxInfoFlag(Enum):
    FEE_REBATE_INCOME_1 = "[1] Hit ceiling for fees rebate on income"
    FEE_REBATE_INCOME_2 = "[2] Hit ceiling for fees rebate on income"
    MARGINAL_TAX_RATE = "Marginal tax rate"
    FAMILY_QUOTIENT_CAPPING = "Capped family quotient benefices"
    CHILD_DAYCARE_CREDIT_CAPPING = "Capped child daycare tax credit"
    HOME_SERVICES_CREDIT_CAPPING = "Capped home services tax credit"
    GLOBAL_FISCAL_ADVANTAGES = "Global fiscal advantages"
    CHARITY_75P = "Charity donation giving 75% reduction"
    CHARITY_66P = "Charity donation giving 66% reduction"

class TaxSimulator:
    def __init__(self, tax_input, debug = False):
        self.flags = {}
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
        incomes_1 = self.state["salary_1_1AJ"] + self.state["exercise_gain_1_1TT"]
        incomes_2 = self.state["salary_2_1BJ"] + self.state["exercise_gain_2_1UT"]
        fees_10p_ceiling = 12652
        self.state["deduction_10p_1"] = round(min(incomes_1 * 0.1, fees_10p_ceiling)) # capped at 12652, see:
        self.state["deduction_10p_2"] = round(min(incomes_2 * 0.1, fees_10p_ceiling)) # https://www.impots.gouv.fr/portail/particulier/questions/comment-puis-je-beneficier-de-la-deduction-forfaitaire-de-10
        if incomes_1 * 0.1 > fees_10p_ceiling:
            self.flags[TaxInfoFlag.FEE_REBATE_INCOME_1] = f"taxable income += {round(incomes_1 * 0.1 - fees_10p_ceiling)}€"
        if incomes_2 * 0.1 > fees_10p_ceiling:
            self.flags[TaxInfoFlag.FEE_REBATE_INCOME_2] = f"taxable income += {round(incomes_2 * 0.1 - fees_10p_ceiling)}€"
        self.state["total_net_salaries"] = incomes_1 - self.state["deduction_10p_1"] + incomes_2 - self.state["deduction_10p_2"]

    def compute_taxable_income(self):
        total_per = self.state["per_transfers_1_6NS"] + self.state["per_transfers_2_6NT"] # TODO take capping into account
        # TODO other deductible charges
        self.state["taxable_income"] = self.state["total_net_salaries"] - total_per
        self.state["taxable_income"] += self.state["taxable_acquisition_gain_1TZ"] # Taxable part of RSUs

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
        marginal_tax_rate = 0
        while ((taxable_income > income_accounted_for) and (bucket_n < len(thresholds)-1)):
            self.maybe_print("Accounted for: ", income_accounted_for)
            self.maybe_print("In bucket ",bucket_n)
            bucket_amount = thresholds[bucket_n+1]-thresholds[bucket_n]
            self.maybe_print("Bucket amount: ", bucket_amount)
            bucket_tax = slices_rates[bucket_n] * min(bucket_amount, taxable_income-income_accounted_for)
            marginal_tax_rate = slices_rates[bucket_n]
            self.maybe_print("Bucket tax: ", bucket_tax)
            tax += bucket_tax
            self.maybe_print("Tax now: ", tax)
            income_accounted_for = thresholds[bucket_n+1]
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
        household_shares = self.state["household_shares"]
        tax_with_family_quotient, marginal_tax_rate = self._compute_income_tax(household_shares)
        tax_without_family_quotient, _ = self._compute_income_tax(2) # TODO: don't hardcode "2", make that depend on marital state
        self.flags[TaxInfoFlag.MARGINAL_TAX_RATE] = f"{round(marginal_tax_rate*100)}%"
        # apply capping of the family quotient benefices, see
        # https://www.economie.gouv.fr/particuliers/quotient-familial
        family_quotient_benefices = tax_without_family_quotient - tax_with_family_quotient
        family_quotient_benefices_capping = 1570 * ((household_shares-2) * 2)
        self.maybe_print("Family quotient benefices: ", family_quotient_benefices, "  ;  Capped to: ", family_quotient_benefices_capping)
        if (family_quotient_benefices > family_quotient_benefices_capping):
            self.flags[TaxInfoFlag.FAMILY_QUOTIENT_CAPPING] = f"tax += {round(family_quotient_benefices - family_quotient_benefices_capping,2)}€"
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
        charity_donation = self.state["charity_donation_7UD"]
        capped_or_not = " (capped)" if charity_donation > 1000 else ""
        charity_donation_75p = min(charity_donation, 1000)
        self.flags[TaxInfoFlag.CHARITY_75P] = f"{charity_donation_75p}€{capped_or_not}"
        charity_donation_reduction_75p = charity_donation_75p * 0.75
        # ... then 66% for the rest, up to 20% of the taxable income
        donation_leftover = max(charity_donation-1000, 0)
        capped_or_not = " (capped)" if donation_leftover > self.state["taxable_income"]*0.20 else ""
        charity_donation_66p = round(min(donation_leftover, self.state["taxable_income"]*0.20))
        charity_donation_reduction_66p = charity_donation_66p * 0.66
        self.flags[TaxInfoFlag.CHARITY_66P] = f"{charity_donation_66p}€{capped_or_not}"
        # Total reduction
        self.state["charity_reduction"] = charity_donation_reduction_75p + charity_donation_reduction_66p

        # Subscription to PME capital: in 2020 there are 2 segments: before and after Aug.10th (with different reduction rates)
        # See https://www.impots.gouv.fr/portail/particulier/questions/si-jinvestis-dans-une-entreprise-ai-je-droit-une-reduction-dimpot
        # Total is capped at 100K (TODO: tune that value depending on marital state)
        pme_capital_subscription_before_aug10 = min(self.state["pme_capital_subscription_7CF"], 100000)
        pme_capital_subscription_after_aug10 = min(self.state["pme_capital_subscription_7CH"], 100000-pme_capital_subscription_before_aug10)
        self.state["pme_capital_reduction"] = pme_capital_subscription_before_aug10 * 0.18 + pme_capital_subscription_after_aug10 * 0.25

    def compute_tax_credits(self):
        # Daycare fees, capped & rated at 50%
        # https://www.impots.gouv.fr/portail/particulier/questions/je-fais-garder-mon-jeune-enfant-lexterieur-du-domicile-que-puis-je-deduire
        if self.state["children_daycare_fees_7GA"] > 2300:
            self.flags[TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING] = f"capped to 2'300€ (originally {self.state['children_daycare_fees_7GA']}€)"
        capped_daycare_fees = min(self.state["children_daycare_fees_7GA"], 2300)
        self.state["children_daycare_taxcredit"] = capped_daycare_fees * 0.5

        # services at home (cleaning etc.)
        # https://www.impots.gouv.fr/portail/particulier/emploi-domicile
        home_services_capping = min(12000 + 1500 * self.state["nb_kids"], 15000)
        if self.state["home_services_7DB"] > home_services_capping:
            self.flags[TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING] = f"capped to {home_services_capping}€ (originally {self.state['home_services_7DB']}€)"
        capped_home_services = min(self.state["home_services_7DB"], home_services_capping)
        self.state["home_services_taxcredit"] = capped_home_services * 0.5

    def compute_capital_taxes(self):
        # simple, flat tax based (opting for progressive tax with box "2OP" is not supported in this simulator)
        self.state["capital_gain_tax"] = self.state["capital_gain_3VG"] * 0.128

    def compute_net_taxes(self):
        # Tax reductions and credits are in part capped ("Plafonnement des niches fiscales")
        # https://www.service-public.fr/particuliers/vosdroits/F31179
        all_taxes_before_capping = self.state["tax_before_reductions"]\
                                      - self.state["charity_reduction"]
        taxes_with_reduction_before_capping = all_taxes_before_capping\
                                              - self.state["pme_capital_reduction"]
        partial_taxes_2 = max(taxes_with_reduction_before_capping, 0)\
                          - self.state["children_daycare_taxcredit"]\
                          - self.state["home_services_taxcredit"]

        fiscal_advantages = all_taxes_before_capping - partial_taxes_2
        if fiscal_advantages > 10000:
            self.flags[TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES] = f"capped to 10'000€ (originally {fiscal_advantages}€)"
            net_taxes_after_global_capping = all_taxes_before_capping - 10000
        else:
            self.flags[
                TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES] = f"{fiscal_advantages}€ (uncapped, {10000 - fiscal_advantages}€ from ceiling)"
            net_taxes_after_global_capping = partial_taxes_2

        self.state["net_taxes"] = net_taxes_after_global_capping + self.state["capital_gain_tax"]


    def compute_social_taxes(self):
        # stock options
        so_exercise_gains = self.state["exercise_gain_1_1TT"] + self.state["exercise_gain_2_1UT"]
        so_salarycontrib_10p = so_exercise_gains * 0.1
        so_csg = so_exercise_gains * 0.092
        so_crds = so_exercise_gains * 0.005
        # capital acquisition (RSUs), capital gain (RSUs and normal stocks)
        rsu_socialtax_base = self.state["capital_gain_3VG"] + self.state["taxable_acquisition_gain_1TZ"]\
            + self.state["acquisition_gain_rebates_1UZ"] + self.state["acquisition_gain_50p_rebates_1WZ"]
        rsu_csgcrds = rsu_socialtax_base * 0.097
        rsu_social_contrib = rsu_socialtax_base * 0.075
        self.state["net_social_taxes"] = round(so_salarycontrib_10p + so_csg + so_crds + rsu_csgcrds + rsu_social_contrib)

    