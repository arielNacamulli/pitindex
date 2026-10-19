# sp500

# Reconciliation Report

- Window: **2004-12-30 → 2026-10-19**
- Seed roster size: **495**
- Current Wikipedia roster size: **503**
- Roster size after walking events: **503**
- Diff ratio vs. current: **1.19%**
- Synthetic events inserted: **4**
- Renames applied / skipped (other-index no-ops): **29 / 7**
- Fill no-ops (revision-diff events on already-consistent state): **0**

## Invalid 'added' on existing ticker (0)


## Invalid 'removed' on missing ticker (2)

- 2008-09-15  LEHMQ
  - this event: `manual override: Same as above; emitted in both notations so the event no-ops cleanly regardless of which is in the roster.`
  - last applied: `2005-01-03 renamed: Bootstrap-time rename: the upstream seed dataset uses the post-bankruptcy ticker LEHMQ for Lehman Brothers throughout. Rename to the period-correct LEH at start_date so PIT queries return LEH while the company was a member.`
- 2008-09-17  LEHMQ
  - this event: `derived from seed snapshot diff`
  - last applied: `2005-01-03 renamed: Bootstrap-time rename: the upstream seed dataset uses the post-bankruptcy ticker LEHMQ for Lehman Brothers throughout. Rename to the period-correct LEH at start_date so PIT queries return LEH while the company was a member.`

## Missing from event walk (synthetic add at start_date) (2)

SKYD, VMRK

## Extra from event walk (synthetic remove at end_date) (2)

EQR, PSKY


# sp400

# Reconciliation Report

- Window: **2011-11-20 → 2026-10-19**
- Seed roster size: **400**
- Current Wikipedia roster size: **400**
- Roster size after walking events: **400**
- Diff ratio vs. current: **3.75%**
- Synthetic events inserted: **0**
- Renames applied / skipped (other-index no-ops): **4 / 31**
- Fill no-ops (revision-diff events on already-consistent state): **366**

## Invalid 'added' on existing ticker (2)

- 2012-06-29  ALEX
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 611: June 29, 2012 | ALEX | Alexander & Baldwin | PCX | Patriot Coal | Corporate spin-off .`
- 2023-04-04  CR
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 146: April 4, 2023 | CR | Crane (new) |  |  | Crane Holdings completed the corporate spin-off of new Crane. Following the spin-off, the parent Crane Holdings Co. cha`

## Invalid 'removed' on missing ticker (13)

- 2012-09-28  RSH
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 607: September 28, 2012 | LXK | Lexmark | RSH | RadioShack | Corporate spin-off .`
- 2012-12-21  AGP
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 602: December 21, 2012 | UNFI | United Natural Foods | AGP | AMERIGROUP | Acquisition.`
- 2013-04-30  REGN
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 597: April 30, 2013 | EXP | Eagle Materials | REGN | Regeneron Pharmaceuticals | Market capitalization changes.`
- 2013-05-01  NOG
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 596: May 1, 2013 | CST | CST Brands | NOG | Northern Oil & Gas | Corporate spin-off .`
- 2013-06-28  TLAB
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 590: June 28, 2013 | MNK | Mallinckrodt | TLAB | Tellabs | Corporate spin-off .`
- 2014-04-30  UAA
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 564: April 30, 2014 | POL | PolyOne | UAA | Under Armour | Corporate spin-off .`
- 2014-12-09  CNVR
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 534: December 9, 2014 | THS | TreeHouse Foods | CNVR | Conversant | Acquisition.`
- 2016-12-01  AMSG
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 463: December 1, 2016 | LM | Legg Mason | AMSG | AmSurg | AmSurg replaced Legg Mason in the S&P 500, and Legg Mason replaced AmSurg in the S&P MidCap 400. AmSurg acq`
- 2016-12-01  PPS
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 462: December 1, 2016 | PZZA | Papa John's Pizza | PPS | Post Properties | Papa John's International replaced Post Properties in the S&P MidCap 400, and Wingstop rep`
- 2019-09-18  INGN
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 325: September 18, 2019 | PK | Park Hotels & Resorts | INGN | Inogen] | Market capitalization changes.`
- 2020-05-27  DHC
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 294: May 27, 2020 | HPP | Hudson Pacific Properties | DHC | Diversified Healthcare Trust | Market capitalization changes. | `
- 2020-06-22  REZI
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 290: June 22, 2020 | UNVR | Univar Solutions | REZI | Resideo Technologies | Market capitalization changes. | `
- 2021-03-22  CZR
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 252: March 22, 2021 | VNT | Vontier | CZR | Caesars Entertainment | Market capitalization changes.`
  - last applied: `2020-07-24 removed: Historical_components_of_the_S&P_400 · table 1 · row 281: July 24, 2020 | EBS | Emergent BioSolutions | CZR | Caesars Entertainment | Eldorado Resorts acquired Caesars Entertainment.`

## Missing from event walk (synthetic add at start_date) (0)

_none_

## Extra from event walk (synthetic remove at end_date) (0)

_none_


# sp600

# Reconciliation Report

- Window: **2021-03-31 → 2026-10-19**
- Seed roster size: **601**
- Current Wikipedia roster size: **603**
- Roster size after walking events: **604**
- Diff ratio vs. current: **1.00%**
- Synthetic events inserted: **1**
- Renames applied / skipped (other-index no-ops): **0 / 20**
- Fill no-ops (revision-diff events on already-consistent state): **7**

## Invalid 'added' on existing ticker (2)

- 2022-10-03  XPER
  - this event: `Historical_components_of_the_S&P_600 · table 1 · row 332: October 3, 2022 | XPER | Xperi | SLQT | SelectQuote | Xperi Holding Corporation completed the corporate spin-off of Xperi Incorporated. Post spin off both compa`
- 2025-09-02  BHLB
  - this event: `Historical_components_of_the_S&P_600 · table 1 · row 114: September 2, 2025 | BHLB | Berkshire Hills Bancorp | BBT | Beacon Financial Corp. | BHLB acquired Brookline Bancorp. Post merger, BHLB remained in the S&P 600 w`

## Invalid 'removed' on missing ticker (3)

- 2025-01-02  GEAR
  - this event: `Historical_components_of_the_S&P_600 · table 1 · row 147: January 2, 2025 | GDYN | Grid Dynamics Holdings | GEAR | Revelyst | GDYN replaced GEAR after it was acquired by Strategic Value Partners.`
- 2025-09-02  BBT
  - this event: `Historical_components_of_the_S&P_600 · table 1 · row 114: September 2, 2025 | BHLB | Berkshire Hills Bancorp | BBT | Beacon Financial Corp. | BHLB acquired Brookline Bancorp. Post merger, BHLB remained in the S&P 600 w`
- 2026-03-23  AHRT
  - this event: `Historical_components_of_the_S&P_600 · table 1 · row 58: March 23, 2026 | LAUR | Laureate Education | AHRT | AH Realty Trust | Market capitalization changes. | `

## Missing from event walk (synthetic add at start_date) (0)

_none_

## Extra from event walk (synthetic remove at end_date) (1)

ALSK
