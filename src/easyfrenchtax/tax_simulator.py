from collections import defaultdict, namedtuple
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


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


class TaxField(Enum):
    # Input fields
    MARRIED = "married"
    NB_CHILDREN = "nb_children"
    CHILD_1_BIRTHYEAR = "child_1_birthyear"
    CHILD_2_BIRTHYEAR = "child_2_birthyear"
    CHILD_3_BIRTHYEAR = "child_3_birthyear"
    CHILD_4_BIRTHYEAR = "child_4_birthyear"
    CHILD_5_BIRTHYEAR = "child_5_birthyear"
    CHILD_6_BIRTHYEAR = "child_6_birthyear"
    SALARY_1_1AJ = "salary_1_1AJ"
    SALARY_2_1BJ = "salary_2_1BJ"
    EXERCISE_GAIN_1_1TT = "exercise_gain_1_1TT"
    EXERCISE_GAIN_2_1UT = "exercise_gain_2_1UT"
    TAXABLE_ACQUISITION_GAIN_1TZ = "taxable_acquisition_gain_1TZ"
    ACQUISITION_GAIN_REBATES_1UZ = "acquisition_gain_rebates_1UZ"
    ACQUISITION_GAIN_50P_REBATES_1WZ = "acquisition_gain_50p_rebates_1WZ"
    FIXED_INCOME_INTERESTS_ALREADY_TAXED_2BH = "fixed_income_interests_already_taxed_2BH"
    FIXED_INCOME_INTERESTS_2TR = "fixed_income_interests_2TR"
    INTEREST_TAX_ALREADY_PAID_2CK = "interest_tax_already_paid_2CK"
    CAPITAL_GAIN_3VG = "capital_gain_3VG"
    CAPITAL_LOSS_3VH = "capital_loss_3VH"
    REAL_RENTAL_PROFIT_4BA = "real_rental_profit_4BA"
    REAL_RENTAL_INCOME_DEFICIT_4BB = "real_rental_income_deficit_4BB"
    RENTAL_INCOME_GLOBAL_DEFICIT_4BC = "rental_income_global_deficit_4BC"
    PREVIOUS_RENTAL_INCOME_DEFICIT_4BD = "previous_rental_income_deficit_4BD"
    SIMPLIFIED_RENTAL_INCOME_4BE = "simplified_rental_income_4BE"
    WOODCUT_INCOME_1_5HD = "woodcut_income_1_5HD"
    WOODCUT_INCOME_2_5ID = "woodcut_income_2_5ID"
    WOODCUT_INCOME_3_5JD = "woodcut_income_3_5JD"
    LMNP_MICRO_INCOME_1_5ND = "lmnp_micro_income_1_5nd"
    LMNP_MICRO_INCOME_2_5OD = "lmnp_micro_income_2_5od"
    LMNP_MICRO_INCOME_3_5PD = "lmnp_micro_income_3_5pd"
    PER_TRANSFERS_1_6NS = "per_transfers_1_6NS"
    PER_TRANSFERS_2_6NT = "per_transfers_2_6NT"
    # TODO add PERO contributions (work mandatory retirement plan) 6QS/6QT/6QU
    SME_CAPITAL_SUBSCRIPTION_7CF = "sme_capital_subscription_7CF"
    SME_CAPITAL_SUBSCRIPTION_7CH = "sme_capital_subscription_7CH"
    HOME_SERVICES_7DB = "home_services_7DB"
    CHILDREN_DAYCARE_FEES_7GA = "children_daycare_fees_7GA"
    CHILDREN_DAYCARE_FEES_7GB = "children_daycare_fees_7GB"
    CHILDREN_DAYCARE_FEES_7GC = "children_daycare_fees_7GC"
    CHILDREN_DAYCARE_FEES_7GD = "children_daycare_fees_7GD"
    CHILDREN_DAYCARE_FEES_7GE = "children_daycare_fees_7GE"
    CHILDREN_DAYCARE_FEES_7GF = "children_daycare_fees_7GF"
    CHILDREN_DAYCARE_FEES_7GG = "children_daycare_fees_7GG"
    CHARITY_DONATION_7UD = "charity_donation_7UD"
    CHARITY_DONATION_7UF = "charity_donation_7UF"
    # Intermediate results
    NB_CHILDREN_LT_6YO = "nb_children_lt_6yo"
    RENTAL_INCOME_RESULT = "rental_income_result"
    TAXABLE_LMNP_INCOME = "taxable_lmnp_income"
    AGRICULTURAL_INCOME = "agricultural_income"
    DEDUCTION_10P_1 = "deduction_10p_1"
    DEDUCTION_10P_2 = "deduction_10p_2"
    TAXABLE_INVESTMENT_INCOME = "taxable_investment_income"
    INVESTMENT_INCOME_TAX = "investment_income_tax"
    SIMPLE_TAX_RIGHT = "simple_tax_right"
    TAX_BEFORE_REDUCTIONS = "tax_before_reductions"
    CHARITY_REDUCTION = "charity_reduction"
    SME_SUBSCRIPTION_REDUCTION = "sme_subscription_reduction"
    CHILDREN_DAYCARE_TAXCREDIT = "children_daycare_taxcredit"
    HOME_SERVICES_TAXCREDIT = "home_services_taxcredit"
    CAPITAL_GAIN_TAX = "capital_gain_tax"
    # Output fields
    YEAR = "year"
    HOUSEHOLD_SHARES = "household_shares"
    RENTAL_DEFICIT_CARRYOVER = "rental_deficit_carryover"
    TOTAL_NET_INCOME = "total_net_income"
    TAXABLE_INCOME = "taxable_income"
    REFERENCE_FISCAL_INCOME = "reference_fiscal_income"
    NET_TAXES = "net_taxes"
    NET_SOCIAL_TAXES = "net_social_taxes"


# Lots of parameters evolve year after year (inflation, political decisions, etc.)
# This dictionary gathers all variable parameters.
TaxParameters = namedtuple("TaxParameters", [
    # Source: https://www.economie.gouv.fr/particuliers/quotient-familial
    "family_quotient_benefices_capping",
    # https://www.service-public.fr/particuliers/vosdroits/F1419
    "slices_thresholds", "slices_rates",
    # https://www.impots.gouv.fr/particulier/questions/comment-puis-je-beneficier-de-la-deduction-forfaitaire-de-10
    "fees_10p_deduction_ceiling", "fees_10p_deduction_floor"
])
year_tax_parameters: dict[int, TaxParameters] = {
    2021: TaxParameters(
        family_quotient_benefices_capping=1570,
        slices_thresholds=[10084, 25710, 73516, 158122],
        slices_rates=[0.11, 0.30, 0.41, 0.45],
        fees_10p_deduction_ceiling=12652,
        fees_10p_deduction_floor=442

    ),
    2022: TaxParameters(
        family_quotient_benefices_capping=1592,
        slices_thresholds=[10225, 26070, 74545, 160336],
        slices_rates=[0.11, 0.30, 0.41, 0.45],
        fees_10p_deduction_ceiling=12829,
        fees_10p_deduction_floor=448
    ),
    2023: TaxParameters(
        family_quotient_benefices_capping=1678,
        slices_thresholds=[10777, 27478, 78570, 168994],
        slices_rates=[0.11, 0.30, 0.41, 0.45],
        fees_10p_deduction_ceiling=13522,
        fees_10p_deduction_floor=472
    ),

}


def tax_round(v: float, places: int = 0) -> float:
    # python rounds half to even (bankers rounding), we need to tax_round half up
    q = Decimal(10) ** (-places)
    return float(Decimal(v).quantize(q, rounding=ROUND_HALF_UP))


class TaxSimulator:
    parameters: TaxParameters
    flags: dict[TaxInfoFlag, str]
    debug: bool
    state: dict[TaxField, Any]

    def __init__(self, statement_year: int, tax_input: dict[TaxField, Any], debug: bool = False):
        if statement_year in year_tax_parameters:
            self.parameters = year_tax_parameters[statement_year]
        else:
            # TODO FIXME
            self.parameters = year_tax_parameters[2022]
        self.flags = {}
        self.debug = debug
        self.state = defaultdict(int, tax_input)
        self.state[TaxField.YEAR] = statement_year
        self.process_family_information()
        self.compute_rental_income()
        self.compute_furnished_rentals()
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
        # See https://www.service-public.fr/particuliers/vosdroits/F2705 and
        # https://www.service-public.fr/particuliers/vosdroits/F2702
        # /!\ extra half-shares and shared custody are not taken into account
        base_shares = 2 if self.state[TaxField.MARRIED] else 1
        nb_children_1 = min(self.state[TaxField.NB_CHILDREN], 2)
        nb_children_2 = max(0, self.state[TaxField.NB_CHILDREN] - nb_children_1)
        self.state[TaxField.HOUSEHOLD_SHARES] = base_shares + nb_children_1 * 0.5 + nb_children_2
        # counting children aged less than 6 years old, if not provided
        if TaxField.NB_CHILDREN_LT_6YO not in self.state:
            nb_children_lt_6yo = 0
            for child_birthyear_key in [TaxField.CHILD_1_BIRTHYEAR,
                                        TaxField.CHILD_2_BIRTHYEAR,
                                        TaxField.CHILD_3_BIRTHYEAR,
                                        TaxField.CHILD_4_BIRTHYEAR,
                                        TaxField.CHILD_5_BIRTHYEAR,
                                        TaxField.CHILD_6_BIRTHYEAR]:
                if child_birthyear_key in self.state:
                    # counting from year-1, (i.e. if declaring in 2022, checking age on Jan 1st 2021)
                    if self.state[TaxField.YEAR] - 1 - self.state[child_birthyear_key] <= 6:
                        nb_children_lt_6yo += 1
            self.state[TaxField.NB_CHILDREN_LT_6YO] = nb_children_lt_6yo

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

        simplified_income_reporting = self.state[TaxField.SIMPLIFIED_RENTAL_INCOME_4BE]
        net_profit = self.state[TaxField.REAL_RENTAL_PROFIT_4BA]
        deficit = self.state[TaxField.REAL_RENTAL_INCOME_DEFICIT_4BB]
        global_deficit = self.state[TaxField.RENTAL_INCOME_GLOBAL_DEFICIT_4BC]
        previous_deficit = self.state[TaxField.PREVIOUS_RENTAL_INCOME_DEFICIT_4BD]

        if simplified_income_reporting:
            if net_profit or deficit or global_deficit or previous_deficit:
                raise Exception("The simplified rental income reporting (4BE) cannot be combined with the default "
                                "rental income reporting (4BA 4BB 4BC)")
            if simplified_income_reporting > 15000:
                raise Exception("Simplified rental income reporting (4BE) cannot exceed 15'000€")
            final_net_profit = simplified_income_reporting * 0.7  # 30% rebate automatically applied
            final_deficit_carryover = 0
        elif net_profit:
            if deficit or global_deficit:
                raise Exception(
                    "Rental profit reporting (4BA) cannot be combined with rental deficit reporting(4BB 4BC)")
            final_net_profit = max(net_profit - previous_deficit, 0)
            final_deficit_carryover = max(0, previous_deficit - net_profit)
        else:
            if global_deficit > 10700:
                raise Exception("Rental deficit for global deduction (4BC) cannot exceed 10'700€")
            final_net_profit = -global_deficit
            final_deficit_carryover = deficit + previous_deficit

        self.state[TaxField.RENTAL_INCOME_RESULT] = final_net_profit
        if final_deficit_carryover:
            self.state[TaxField.RENTAL_DEFICIT_CARRYOVER] = final_deficit_carryover
            self.flags[TaxInfoFlag.RENTAL_DEFICIT_CARRYOVER] = f"{final_deficit_carryover}€"

    def compute_furnished_rentals(self):
        # This corresponds to "Non-professional furnished rentals" (LMNP in French, for "Location meublées non
        # professionnelles"). Only "micro" incomes are supported (i.e. less than 72'600€ income per year). More details:
        # https://www.impots.gouv.fr/sites/default/files/media/1_metier/1_particulier/EV/1_declarer/141_autres_revenus/eco-collabo-fiscal-logement-meuble.pdf
        incomes = self.state[TaxField.LMNP_MICRO_INCOME_1_5ND] \
                  + self.state[TaxField.LMNP_MICRO_INCOME_2_5OD] \
                  + self.state[TaxField.LMNP_MICRO_INCOME_3_5PD]
        incomes_rebate = max(incomes * 0.5, 305)  # minimum rebate is 305e
        self.state[TaxField.TAXABLE_LMNP_INCOME] = max(incomes - incomes_rebate, 0)

    def compute_agricultural_income(self):
        # IMPORTANT: these 3 fields about woodcut income (5HD/5ID/5JD) are very poory explained. The decision to gather
        # them into an "agricultural income" that is taxed progressively like an income tax comes from checking the
        # official french tax simulator. THIS MIGHT BE COMPLETELY WRONG.
        incomes = self.state[TaxField.WOODCUT_INCOME_1_5HD] \
                  + self.state[TaxField.WOODCUT_INCOME_2_5ID] \
                  + self.state[TaxField.WOODCUT_INCOME_3_5JD]
        self.state[TaxField.AGRICULTURAL_INCOME] = incomes

    def compute_net_income(self):
        incomes_1 = self.state[TaxField.SALARY_1_1AJ] + self.state[TaxField.EXERCISE_GAIN_1_1TT]
        incomes_2 = self.state[TaxField.SALARY_2_1BJ] + self.state[TaxField.EXERCISE_GAIN_2_1UT]
        # capped at 12652e (in 2021), see:
        # https://www.impots.gouv.fr/portail/particulier/questions/comment-puis-je-beneficier-de-la-deduction-forfaitaire-de-10
        fees_10p_floor = self.parameters.fees_10p_deduction_floor
        fees_10p_ceiling = self.parameters.fees_10p_deduction_ceiling
        incomes_1_10p = tax_round(incomes_1 * 0.1)
        fee_deduction_1 = max(min(incomes_1_10p, fees_10p_ceiling), fees_10p_floor)
        self.state[TaxField.DEDUCTION_10P_1] = fee_deduction_1
        if incomes_1_10p > fees_10p_ceiling:
            tax_increment = round(incomes_1_10p - fees_10p_ceiling)
            self.flags[TaxInfoFlag.FEE_REBATE_INCOME_1] = f"taxable income += {tax_increment}€"
        net_income = incomes_1 - fee_deduction_1
        if self.state[TaxField.MARRIED]:
            incomes_2_10p = tax_round(incomes_2 * 0.1)
            fee_deduction_2 = max(min(incomes_2_10p, fees_10p_ceiling), fees_10p_floor)
            self.state[TaxField.DEDUCTION_10P_2] = fee_deduction_2
            if incomes_2_10p > fees_10p_ceiling:
                tax_increment = round(incomes_2_10p - fees_10p_ceiling)
                self.flags[TaxInfoFlag.FEE_REBATE_INCOME_2] = f"taxable income += {tax_increment}€"
            net_income += incomes_2 - fee_deduction_2
        self.state[TaxField.TOTAL_NET_INCOME] = net_income + self.state[TaxField.RENTAL_INCOME_RESULT] \
            + self.state[TaxField.TAXABLE_LMNP_INCOME] + self.state[TaxField.AGRICULTURAL_INCOME]

    def compute_taxable_income(self):
        # TODO take capping into account
        total_per = self.state[TaxField.PER_TRANSFERS_1_6NS] + self.state[TaxField.PER_TRANSFERS_2_6NT]
        self.state[TaxField.TAXABLE_INCOME] = self.state[TaxField.TOTAL_NET_INCOME] - total_per
        self.state[TaxField.TAXABLE_INCOME] += self.state[TaxField.TAXABLE_ACQUISITION_GAIN_1TZ]  # Taxable part of RSUs

    def maybe_print(self, *args):
        if self.debug:
            print(*args)

    def compute_flat_rate_taxes(self):
        # supporting 2TR only for now
        # TODO: support others (2DC, 2FU, 2TS, 2TT, 2WW, 2ZZ, 2TQ, 2TZ)
        self.state[TaxField.TAXABLE_INVESTMENT_INCOME] = self.state[TaxField.FIXED_INCOME_INTERESTS_2TR]
        self.state[TaxField.INVESTMENT_INCOME_TAX] = tax_round(self.state[TaxField.TAXABLE_INVESTMENT_INCOME] * 0.128)

    def compute_reference_fiscal_income(self):
        self.state[TaxField.REFERENCE_FISCAL_INCOME] = max(self.state[TaxField.TOTAL_NET_INCOME] \
                                                           + self.state[TaxField.TAXABLE_INVESTMENT_INCOME] \
                                                           + self.state[TaxField.CAPITAL_GAIN_3VG],
                                                           0)

    def _compute_income_tax(self, household_shares):
        # https://www.service-public.fr/particuliers/vosdroits/F1419
        slices_thresholds = self.parameters.slices_thresholds
        slices_rates = self.parameters.slices_rates
        taxable_income = self.state[TaxField.TAXABLE_INCOME]
        thresholds = [t * household_shares for t in
                      slices_thresholds]  # scale thresholds to the number of people in the household
        self.maybe_print("Thresholds: ", thresholds)
        self.maybe_print("Shares: ", household_shares)
        tax = 0
        income_accounted_for = thresholds[0]
        bucket_n = 0
        marginal_tax_rate = 0
        while (taxable_income > income_accounted_for) and (bucket_n < len(thresholds) - 1):
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
        household_shares = self.state[TaxField.HOUSEHOLD_SHARES]
        tax_with_family_quotient, marginal_tax_rate = self._compute_income_tax(household_shares)
        self.flags[TaxInfoFlag.MARGINAL_TAX_RATE] = f"{round(marginal_tax_rate * 100)}%"
        household_shares_without_family_quotient = 2 if self.state[TaxField.MARRIED] else 1
        tax_without_family_quotient, _ = self._compute_income_tax(household_shares_without_family_quotient)
        # apply capping of the family quotient benefices, see
        # https://www.economie.gouv.fr/particuliers/quotient-familial
        family_quotient_benefices = tax_without_family_quotient - tax_with_family_quotient
        family_quotient_benefices_capping = capping_parameter * (
                (household_shares - household_shares_without_family_quotient) * 2)
        self.maybe_print("Family quotient benefices: ", family_quotient_benefices, "  ;  Capped to: ",
                         family_quotient_benefices_capping)
        if family_quotient_benefices > family_quotient_benefices_capping:
            additional_taxes = family_quotient_benefices - family_quotient_benefices_capping
            self.flags[
                TaxInfoFlag.FAMILY_QUOTIENT_CAPPING] = f"tax += {tax_round(additional_taxes, 2)}€"
            final_income_tax = tax_without_family_quotient - family_quotient_benefices_capping
        else:
            final_income_tax = tax_with_family_quotient
        self.state[TaxField.SIMPLE_TAX_RIGHT] = tax_round(final_income_tax)  # "Droits simples" in French
        self.state[TaxField.TAX_BEFORE_REDUCTIONS] = self.state[TaxField.SIMPLE_TAX_RIGHT] + self.state[
            TaxField.INVESTMENT_INCOME_TAX]

    # Computes all tax reductions. Currently supported:
    # * donations (7UD)
    # * PME capital subscription (7CF, 7CH)
    def compute_tax_reductions(self):
        # See:
        # https://www.impots.gouv.fr/portail/particulier/questions/jai-fait-des-dons-une-association-que-puis-je-deduire
        # 75% reduction for "Dons aux organismes d'aide aux personnes en difficulté", up to a ceiling ...
        charity_donation_7ud = self.state[TaxField.CHARITY_DONATION_7UD]
        capped_or_not = " (capped)" if charity_donation_7ud > 1000 else ""
        charity_donation_75p = min(charity_donation_7ud, 1000)
        self.flags[TaxInfoFlag.CHARITY_75P] = f"{charity_donation_75p}€{capped_or_not}"
        charity_donation_reduction_75p = charity_donation_75p * 0.75
        # ... then 66% for the rest, plus the "Dons aux organismes d'intérêt général", up to 20% of the taxable income
        charity_donation_7uf = self.state[TaxField.CHARITY_DONATION_7UF]
        donation_leftover = charity_donation_7uf + max(charity_donation_7ud - 1000, 0)
        taxable_income = max(self.state[TaxField.TAXABLE_INCOME], 0)
        capped_or_not = " (capped)" if donation_leftover > taxable_income * 0.20 else ""
        charity_donation_66p = tax_round(min(donation_leftover, taxable_income * 0.20))
        charity_donation_reduction_66p = charity_donation_66p * 0.66
        self.flags[TaxInfoFlag.CHARITY_66P] = f"{int(charity_donation_66p)}€{capped_or_not}"
        # Total reduction
        self.state[TaxField.CHARITY_REDUCTION] = charity_donation_reduction_75p + charity_donation_reduction_66p

        # Subscription to PME capital: in 2020 there are 2 segments: before and after Aug.10th (with different reduction
        # rates). See:
        # https://www.impots.gouv.fr/portail/particulier/questions/si-jinvestis-dans-une-entreprise-ai-je-droit-une-reduction-dimpot
        subscription_capping = 100000 if self.state[TaxField.MARRIED] else 50000
        pme_capital_subscription_before = min(self.state[TaxField.SME_CAPITAL_SUBSCRIPTION_7CF], subscription_capping)
        pme_capital_subscription_after = min(self.state[TaxField.SME_CAPITAL_SUBSCRIPTION_7CH],
                                             subscription_capping - pme_capital_subscription_before)
        self.state[TaxField.SME_SUBSCRIPTION_REDUCTION] = pme_capital_subscription_before * 0.18 \
            + pme_capital_subscription_after * 0.25

    def compute_tax_credits(self):
        # Daycare fees, capped & rated at 50%. See:
        # https://www.impots.gouv.fr/portail/particulier/questions/je-fais-garder-mon-jeune-enfant-lexterieur-du-domicile-que-puis-je-deduire
        nb_children_lt_6yo = self.state[TaxField.NB_CHILDREN_LT_6YO]

        nb_children_with_daycare_fees = 0
        total_fees = 0
        fees_capped_out = 0
        for fees_key in [
            TaxField.CHILDREN_DAYCARE_FEES_7GA,
            TaxField.CHILDREN_DAYCARE_FEES_7GB,
            TaxField.CHILDREN_DAYCARE_FEES_7GC,
            TaxField.CHILDREN_DAYCARE_FEES_7GD,
            TaxField.CHILDREN_DAYCARE_FEES_7GE,
            TaxField.CHILDREN_DAYCARE_FEES_7GF,
            TaxField.CHILDREN_DAYCARE_FEES_7GG
        ]:
            if fees_key in self.state:
                nb_children_with_daycare_fees += 1
                if nb_children_with_daycare_fees > nb_children_lt_6yo:
                    raise Exception(f"You are declaring more children daycare fees ({nb_children_with_daycare_fees}) "
                                    f"than you have children below 6y old ({nb_children_lt_6yo})")
                total_fees += min(self.state[fees_key], 2300)
                fees_capped_out += max(self.state[fees_key] - 2300, 0)
        self.flags[
            TaxInfoFlag.CHILD_DAYCARE_CREDIT_CAPPING] = f"capped to {total_fees}€ (originally " \
                                                        f"{total_fees + fees_capped_out}€)"
        self.state[TaxField.CHILDREN_DAYCARE_TAXCREDIT] = total_fees * 0.5

        # services at home (cleaning etc.)
        # https://www.impots.gouv.fr/portail/particulier/emploi-domicile
        home_services_capping = min(12000 + 1500 * self.state[TaxField.NB_CHILDREN], 15000)
        home_services = self.state[TaxField.HOME_SERVICES_7DB]
        if home_services > home_services_capping:
            self.flags[TaxInfoFlag.HOME_SERVICES_CREDIT_CAPPING] = f"capped to {home_services_capping}€" \
                                                                   + f" (originally {home_services}€)"
        capped_home_services = min(home_services, home_services_capping)
        self.state[TaxField.HOME_SERVICES_TAXCREDIT] = capped_home_services * 0.5

    def compute_capital_taxes(self):
        # simple, flat tax based (opting for progressive tax with box "2OP" is not supported in this simulator)
        self.state[TaxField.CAPITAL_GAIN_TAX] = self.state[TaxField.CAPITAL_GAIN_3VG] * 0.128

    def compute_net_taxes(self):
        # Tax reductions and credits are in part capped ("Plafonnement des niches fiscales")
        # https://www.service-public.fr/particuliers/vosdroits/F31179
        all_taxes_before_capping = self.state[TaxField.TAX_BEFORE_REDUCTIONS] \
                                   - self.state[TaxField.CHARITY_REDUCTION]
        taxes_with_reduction_before_capping = all_taxes_before_capping - self.state[TaxField.SME_SUBSCRIPTION_REDUCTION]
        partial_taxes_2 = max(taxes_with_reduction_before_capping, 0) - self.state[TaxField.CHILDREN_DAYCARE_TAXCREDIT]\
            - self.state[TaxField.HOME_SERVICES_TAXCREDIT]

        fiscal_advantages = all_taxes_before_capping - partial_taxes_2
        if fiscal_advantages > 10000:
            self.flags[TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES] = f"capped to 10'000€ (originally {fiscal_advantages}€)"
            net_taxes_after_global_capping = all_taxes_before_capping - 10000
        else:
            self.flags[TaxInfoFlag.GLOBAL_FISCAL_ADVANTAGES] = f"{fiscal_advantages}€" + \
                                                               f" (uncapped, {10000 - fiscal_advantages}€ from ceiling)"
            net_taxes_after_global_capping = partial_taxes_2

        net_taxes = net_taxes_after_global_capping + self.state[TaxField.CAPITAL_GAIN_TAX] - self.state[
            TaxField.INTEREST_TAX_ALREADY_PAID_2CK]
        self.state[TaxField.NET_TAXES] = tax_round(net_taxes, 2)

    def compute_social_taxes(self):
        csg_crds_base = self.state[TaxField.CAPITAL_GAIN_3VG] \
                        + self.state[TaxField.TAXABLE_ACQUISITION_GAIN_1TZ] \
                        + self.state[TaxField.ACQUISITION_GAIN_REBATES_1UZ] \
                        + self.state[TaxField.ACQUISITION_GAIN_50P_REBATES_1WZ] \
                        + (self.state[TaxField.TAXABLE_INVESTMENT_INCOME]
                           - self.state[TaxField.FIXED_INCOME_INTERESTS_ALREADY_TAXED_2BH]) \
                        + max(self.state[TaxField.RENTAL_INCOME_RESULT], 0) \
                        + self.state[TaxField.TAXABLE_LMNP_INCOME]
        activity_income_crds_base = self.state[TaxField.EXERCISE_GAIN_1_1TT] + self.state[TaxField.EXERCISE_GAIN_2_1UT]
        salary_contrib_10p_base = self.state[TaxField.EXERCISE_GAIN_1_1TT] + self.state[TaxField.EXERCISE_GAIN_2_1UT]

        csg_crds_taxes = tax_round((csg_crds_base + activity_income_crds_base) * 0.097)
        solidarity_75_taxes = tax_round(csg_crds_base * 0.075)
        salary_contrib_10p = salary_contrib_10p_base * 0.1
        self.state[TaxField.NET_SOCIAL_TAXES] = csg_crds_taxes + solidarity_75_taxes + salary_contrib_10p
