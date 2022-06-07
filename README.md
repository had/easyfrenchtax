# easyfrenchtax
This project helps me understanding and projecting French taxes, especially wrt. stock, stock options, RSUs and other systems. It doesn't replace a tax advisor, I am not a lawyer, you should not rely blindly on this software for filling your tax return.

# Tax simulator
The following are supported:
- Progressive income tax
- Rental income (unfurnished)
- Family quotient (incl. capping, but excl. shared custody situations)
- Some deductions/reductions (PER, child care, home services, charity donations)
- Capping of fiscal advantages ("plafonnement des niches fiscales" in French)
- Exercising stock options, RSU acquisition gain, capital gain (but not capital loss - yet)
- Fixed interest income, incl. when tax has been partially withheld by a bank
- Social taxes

These elements of taxation have been tested against the tax simulator of the French government. I invite you to read and understand these tests, this will give you a feeling of whether you want to trust this project or not.

# Stock helper

This module helps filling the tax statement regarding stock acquisition or capital gain. It takes as input the stocks received (RSU, Stock Options) or bought (ESPP, direct buying) and what has been exercised/sold; it outputs the fields to fill a form 2074 and parts of 2042C. More precisely, it supports the following:
- Typical retention plans like RSU or Stock Options, direct stocks
- Currency conversion at acquisition/exercise/buying/selling dates
- Weighted average price ("Prix moyen pondéré" or PMP in French tax lingo)
- Outputs fields 3VG/3VH for form 2042C, and frame 5 (512-524) + fields 903/913 for form 2074

# Contact and contributions
If you want to chat about this project, don't hesitate to shoot an email at hadrien.hamel@gmail.com. Contributions and bug reports are welcome!