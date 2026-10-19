# sp500

Build failed before reconciliation: `HTTPError('403 Client Error: rate limit exceeded for url: https://api.github.com/repos/fja05680/sp500/contents')`

# sp400

# Reconciliation Report

- Window: **2011-11-20 → 2026-10-19**
- Seed roster size: **400**
- Current Wikipedia roster size: **400**
- Roster size after walking events: **400**
- Diff ratio vs. current: **11.25%**
- Synthetic events inserted: **2**
- Renames applied / skipped (other-index no-ops): **4 / 31**
- Fill no-ops (revision-diff events on already-consistent state): **366**

## Invalid 'added' on existing ticker (15)

- 2012-06-29  ALEX
  - this event: `List_of_S&P_400_companies · table 1 · row 617: June 29, 2012 | ALEX | Alexander & Baldwin | PCX | Patriot Coal | Spin-off. [ 406 ]`
- 2015-07-01  CC
  - this event: `List_of_S&P_400_companies · table 1 · row 527: June 30, 2015 [ 321 ] | CC | Chemours | SMTC | Semtech | S&P 100 & 500 constituent E. I. du Pont de Nemours and Co. (NYSE: DD) spins off Chemours.`
  - last applied: `2015-06-30 added: Historical_components_of_the_S&P_400 · table 1 · row 521: June 30, 2015 | CC | Chemours | SMTC | Semtech | E. I. du Pont de Nemours and Co. completed the corporate spin-off of Chemours. | [ 317 ]`
- 2015-07-30  JACK
  - this event: `List_of_S&P_400_companies · table 1 · row 524: July 8, 2015 [ 320 ] | JACK | Jack in the Box | AAP | Advance Auto Parts | Dollar Tree has acquired Family Dollar Stores. Advance Auto Parts moves to S&P 500 to`
  - last applied: `2015-07-08 added: Historical_components_of_the_S&P_400 · table 1 · row 518: July 8, 2015 | JACK | Jack in the Box | AAP | Advance Auto Parts | Dollar Tree acquired Family Dollar Stores. Advance Auto Parts moved to the S&P 500 to replace`
- 2016-04-04  ABMD
  - this event: `List_of_S&P_400_companies · table 1 · row 502: March 30, 2016 [ 301 ] | ABMD | Abiomed | HOLX | Hologic | Exelon acquired Pepco Holdings. Hologic moved to S&P 500 to replace Pepco Holdings.`
  - last applied: `2016-03-30 added: Historical_components_of_the_S&P_400 · table 1 · row 496: March 30, 2016 | ABMD | Abiomed | HOLX | Hologic | Exelon acquired Pepco Holdings. Hologic moved to S&P 500 to replace Pepco Holdings. | [ 297 ]`
- 2016-06-24  HELE
  - this event: `List_of_S&P_400_companies · table 1 · row 490: May 31, 2016 [ 290 ] | HELE | Helen of Troy | WCN | Waste Connections | Progressive Waste Solutions Ltd. (TSX:BIN, NYSE: BIN) and Waste Connections are merging `
  - last applied: `2016-05-31 added: Historical_components_of_the_S&P_400 · table 1 · row 484: May 31, 2016 | HELE | Helen of Troy Limited | WCN | Waste Connections | Progressive Waste Solutions and Waste Connections merged to form a new company called Wa`
- 2016-09-27  NWE
  - this event: `List_of_S&P_400_companies · table 1 · row 478: September 22, 2016 [ 279 ] | NWE | NorthWestern | COO | The Cooper Companies | The Cooper Companies Inc. (NYSE: COO) replaces Starwood Hotels & Resorts Worldwid`
  - last applied: `2016-09-22 added: Historical_components_of_the_S&P_400 · table 1 · row 472: September 22, 2016 | NWE | NorthWestern Corporation | COO | The Cooper Companies | The Cooper Companies replaced Starwood Hotels & Resorts Worldwide in the S&P `
- 2017-01-04  OI
  - this event: `List_of_S&P_400_companies · table 1 · row 467: December 1, 2016 [ 271 ] | OI | Owens-Illinois | MAA | Mid-America Apartments | OI replaces MAA. Owens-Illinois is ranked near the bottom of the S&P 500 and has`
  - last applied: `2016-12-01 added: Historical_components_of_the_S&P_400 · table 1 · row 461: December 1, 2016 | OI | Owens-Illinois | MAA | Market capitalization changes. | [ 267 ]`
- 2017-01-04  UMBF
  - this event: `List_of_S&P_400_companies · table 1 · row 465: December 6, 2016 [ 270 ] | UMBF | UMB Financial | IM | Ingram Micro | Tianjin Tianhai Investment Company Ltd acquired Ingram Micro.`
  - last applied: `2016-12-06 added: Historical_components_of_the_S&P_400 · table 1 · row 459: December 6, 2016 | UMBF | UMB Financial Corporation | IM | Ingram Micro | Tianjin Tianhai Investment Company acquired Ingram Micro. | [ 266 ]`
- 2018-11-14  LGND
  - this event: `List_of_S&P_400_companies · table 1 · row 367: November 13, 2018 [ 208 ] | LGND | Ligand Pharmaceuticals | KEYS | Keysight Technologies | Keysight replaced CA Inc. in the S&P 500.`
  - last applied: `2018-11-13 added: Historical_components_of_the_S&P_400 · table 1 · row 363: November 13, 2018 | LGND | Ligand Pharmaceuticals | KEYS | Keysight Technologies | Keysight replaced CA Inc. in the S&P 500. | [ 204 ]`
- 2018-12-10  PEB
  - this event: `List_of_S&P_400_companies · table 1 · row 363: December 3, 2018 [ 207 ] | PEB | Pebblebrook Hotel Trust | LHO | LaSalle Hotel Properties | Pebblebrook Hotel Trust is acquiring LaSalle Hotel Properties.`
  - last applied: `2018-12-03 added: Historical_components_of_the_S&P_400 · table 1 · row 359: December 3, 2018 | PEB | Pebblebrook Hotel Trust | LHO | LaSalle Hotel Properties | Pebblebrook Hotel Trust acquired LaSalle Hotel Properties. | [ 203 ]`
- 2019-03-22  CFX
  - this event: `List_of_S&P_400_companies · table 1 · row 352: March 18, 2019 [ 198 ] | CFX | Colfax | BIG | Big Lots | Colfax Corp. (NYSE:CFX) will replace and Big Lots Inc. (NYSE:BIG) in the S&P MidCap 400.`
  - last applied: `2019-03-18 added: Historical_components_of_the_S&P_400 · table 1 · row 348: March 18, 2019 | CFX | Colfax Corporation | BIG | Big Lots | Colfax replaced Big Lots in the S&P MidCap 400. | [ 194 ]`
- 2019-03-22  GT
  - this event: `List_of_S&P_400_companies · table 1 · row 355: February 27, 2019 [ 199 ] | GT | Goodyear Tire & Rubber | WAB | Wabtec | The Goodyear Tire & Rubber will replace Wabtec in the S&P MidCap 400.`
  - last applied: `2019-02-27 added: Historical_components_of_the_S&P_400 · table 1 · row 351: February 27, 2019 | GT | Goodyear Tire & Rubber | WAB | Wabtec | Market capitalization changes. | [ 195 ]`
- 2019-05-07  SMTC
  - this event: `List_of_S&P_400_companies · table 1 · row 347: April 11, 2019 [ 195 ] | SMTC | Semtech | ARRS | Arris International | CommScope Holding Company Inc.(NASD:COMM) acquired ARRIS International.`
  - last applied: `2019-04-11 added: Historical_components_of_the_S&P_400 · table 1 · row 343: April 11, 2019 | SMTC | Semtech | ARRS | Arris International | CommScope Holding Company acquired ARRIS International. | [ 191 ]`
- 2019-09-23  GRUB
  - this event: `List_of_S&P_400_companies · table 1 · row 339: August 9, 2019 [ 188 ] | GRUB | Grubhub | LDOS | Leidos Holdings | Market capitalization`
  - last applied: `2019-08-09 added: Historical_components_of_the_S&P_400 · table 1 · row 335: August 9, 2019 | GRUB | Grubhub | LDOS | Leidos Holdings | Market capitalization changes. | [ 184 ]`
- 2023-04-04  CR
  - this event: `List_of_S&P_400_companies · table 1 · row 150: April 4, 2023 | CR | Crane (new) |  |  | S&P MidCap 400 constituent Crane Holdings Co. (NYSE:CR) spun off new Crane. Following the spin-off, the parent Crane Ho`

## Invalid 'removed' on missing ticker (28)

- 2012-09-28  RSH
  - this event: `List_of_S&P_400_companies · table 1 · row 613: September 28, 2012 | LXK | Lexmark | RSH | RadioShack | Spin-off. [ 402 ]`
- 2012-12-21  AGP
  - this event: `List_of_S&P_400_companies · table 1 · row 608: December 21, 2012 | UNFI | United Natural Foods | AGP | AMERIGROUP | Acquisition. [ 397 ]`
- 2013-04-30  REGN
  - this event: `List_of_S&P_400_companies · table 1 · row 603: April 30, 2013 | EXP | Eagle Materials | REGN | Regeneron Pharmaceuticals | Market capitalization change. [ 392 ]`
- 2013-05-01  NOG
  - this event: `List_of_S&P_400_companies · table 1 · row 602: May 1, 2013 | CST | CST Brands | NOG | Northern Oil & Gas | Spin-off. [ 391 ]`
- 2013-06-28  TLAB
  - this event: `List_of_S&P_400_companies · table 1 · row 596: June 28, 2013 | MNK | Mallinckrodt | TLAB | Tellabs | Spin-off. [ 385 ]`
- 2014-04-30  UAA
  - this event: `List_of_S&P_400_companies · table 1 · row 570: April 30, 2014 | POL | PolyOne | UAA | Under Armour | Spin-off. [ 359 ]`
- 2014-12-09  CNVR
  - this event: `List_of_S&P_400_companies · table 1 · row 540: December 9, 2014 | THS | TreeHouse Foods | CNVR | Conversant | Acquisition. [ 329 ]`
- 2015-07-01  HARSCO
  - this event: `List_of_S&P_400_companies · table 1 · row 529: EPC | Edgewell Personal Care | HSC | Harsco | S&P MidCap 400 constituent Energizer Inc. (NYSE: ENR) spins off "new" Energizer. Post spin, the parent company wil`
- 2015-07-01  SMTC
  - this event: `List_of_S&P_400_companies · table 1 · row 527: June 30, 2015 [ 321 ] | CC | Chemours | SMTC | Semtech | S&P 100 & 500 constituent E. I. du Pont de Nemours and Co. (NYSE: DD) spins off Chemours.`
  - last applied: `2015-06-30 removed: Historical_components_of_the_S&P_400 · table 1 · row 521: June 30, 2015 | CC | Chemours | SMTC | Semtech | E. I. du Pont de Nemours and Co. completed the corporate spin-off of Chemours. | [ 317 ]`
- 2015-07-30  AAP
  - this event: `List_of_S&P_400_companies · table 1 · row 524: July 8, 2015 [ 320 ] | JACK | Jack in the Box | AAP | Advance Auto Parts | Dollar Tree has acquired Family Dollar Stores. Advance Auto Parts moves to S&P 500 to`
  - last applied: `2015-07-08 removed: Historical_components_of_the_S&P_400 · table 1 · row 518: July 8, 2015 | JACK | Jack in the Box | AAP | Advance Auto Parts | Dollar Tree acquired Family Dollar Stores. Advance Auto Parts moved to the S&P 500 to replace`
- 2016-04-04  HOLX
  - this event: `List_of_S&P_400_companies · table 1 · row 502: March 30, 2016 [ 301 ] | ABMD | Abiomed | HOLX | Hologic | Exelon acquired Pepco Holdings. Hologic moved to S&P 500 to replace Pepco Holdings.`
  - last applied: `2016-03-30 removed: Historical_components_of_the_S&P_400 · table 1 · row 496: March 30, 2016 | ABMD | Abiomed | HOLX | Hologic | Exelon acquired Pepco Holdings. Hologic moved to S&P 500 to replace Pepco Holdings. | [ 297 ]`
- 2016-06-24  WCN
  - this event: `List_of_S&P_400_companies · table 1 · row 490: May 31, 2016 [ 290 ] | HELE | Helen of Troy | WCN | Waste Connections | Progressive Waste Solutions Ltd. (TSX:BIN, NYSE: BIN) and Waste Connections are merging `
  - last applied: `2016-05-31 removed: Historical_components_of_the_S&P_400 · table 1 · row 484: May 31, 2016 | HELE | Helen of Troy Limited | WCN | Waste Connections | Progressive Waste Solutions and Waste Connections merged to form a new company called Wa`
- 2016-09-27  COO
  - this event: `List_of_S&P_400_companies · table 1 · row 478: September 22, 2016 [ 279 ] | NWE | NorthWestern | COO | The Cooper Companies | The Cooper Companies Inc. (NYSE: COO) replaces Starwood Hotels & Resorts Worldwid`
  - last applied: `2016-09-22 removed: Historical_components_of_the_S&P_400 · table 1 · row 472: September 22, 2016 | NWE | NorthWestern Corporation | COO | The Cooper Companies | The Cooper Companies replaced Starwood Hotels & Resorts Worldwide in the S&P `
- 2016-12-01  AMSG
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 463: December 1, 2016 | LM | Legg Mason | AMSG | AmSurg | AmSurg replaced Legg Mason in the S&P 500, and Legg Mason replaced AmSurg in the S&P MidCap 400. AmSurg acq`
- 2016-12-01  PPS
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 462: December 1, 2016 | PZZA | Papa John's Pizza | PPS | Post Properties | Papa John's International replaced Post Properties in the S&P MidCap 400, and Wingstop rep`
- 2017-01-04  IM
  - this event: `List_of_S&P_400_companies · table 1 · row 465: December 6, 2016 [ 270 ] | UMBF | UMB Financial | IM | Ingram Micro | Tianjin Tianhai Investment Company Ltd acquired Ingram Micro.`
  - last applied: `2016-12-06 removed: Historical_components_of_the_S&P_400 · table 1 · row 459: December 6, 2016 | UMBF | UMB Financial Corporation | IM | Ingram Micro | Tianjin Tianhai Investment Company acquired Ingram Micro. | [ 266 ]`
- 2017-01-04  MAA
  - this event: `List_of_S&P_400_companies · table 1 · row 467: December 1, 2016 [ 271 ] | OI | Owens-Illinois | MAA | Mid-America Apartments | OI replaces MAA. Owens-Illinois is ranked near the bottom of the S&P 500 and has`
  - last applied: `2016-12-01 removed: Historical_components_of_the_S&P_400 · table 1 · row 461: December 1, 2016 | OI | Owens-Illinois | MAA | Market capitalization changes. | [ 267 ]`
- 2017-09-18  WEBMD
  - this event: `List_of_S&P_400_companies · table 1 · row 418: CPE | Callon Petroleum | WBMD | WebMD | Internet Brands acquired WebMD Health. [ 242 ]`
- 2018-11-14  KEYS
  - this event: `List_of_S&P_400_companies · table 1 · row 367: November 13, 2018 [ 208 ] | LGND | Ligand Pharmaceuticals | KEYS | Keysight Technologies | Keysight replaced CA Inc. in the S&P 500.`
  - last applied: `2018-11-13 removed: Historical_components_of_the_S&P_400 · table 1 · row 363: November 13, 2018 | LGND | Ligand Pharmaceuticals | KEYS | Keysight Technologies | Keysight replaced CA Inc. in the S&P 500. | [ 204 ]`
- 2018-12-10  LHO
  - this event: `List_of_S&P_400_companies · table 1 · row 363: December 3, 2018 [ 207 ] | PEB | Pebblebrook Hotel Trust | LHO | LaSalle Hotel Properties | Pebblebrook Hotel Trust is acquiring LaSalle Hotel Properties.`
  - last applied: `2018-12-03 removed: Historical_components_of_the_S&P_400 · table 1 · row 359: December 3, 2018 | PEB | Pebblebrook Hotel Trust | LHO | LaSalle Hotel Properties | Pebblebrook Hotel Trust acquired LaSalle Hotel Properties. | [ 203 ]`
- 2019-03-22  BIG
  - this event: `List_of_S&P_400_companies · table 1 · row 352: March 18, 2019 [ 198 ] | CFX | Colfax | BIG | Big Lots | Colfax Corp. (NYSE:CFX) will replace and Big Lots Inc. (NYSE:BIG) in the S&P MidCap 400.`
  - last applied: `2019-03-18 removed: Historical_components_of_the_S&P_400 · table 1 · row 348: March 18, 2019 | CFX | Colfax Corporation | BIG | Big Lots | Colfax replaced Big Lots in the S&P MidCap 400. | [ 194 ]`
- 2019-03-22  WAB
  - this event: `List_of_S&P_400_companies · table 1 · row 355: February 27, 2019 [ 199 ] | GT | Goodyear Tire & Rubber | WAB | Wabtec | The Goodyear Tire & Rubber will replace Wabtec in the S&P MidCap 400.`
  - last applied: `2019-02-27 removed: Historical_components_of_the_S&P_400 · table 1 · row 351: February 27, 2019 | GT | Goodyear Tire & Rubber | WAB | Wabtec | Market capitalization changes. | [ 195 ]`
- 2019-05-07  ARRS
  - this event: `List_of_S&P_400_companies · table 1 · row 347: April 11, 2019 [ 195 ] | SMTC | Semtech | ARRS | Arris International | CommScope Holding Company Inc.(NASD:COMM) acquired ARRIS International.`
  - last applied: `2019-04-11 removed: Historical_components_of_the_S&P_400 · table 1 · row 343: April 11, 2019 | SMTC | Semtech | ARRS | Arris International | CommScope Holding Company acquired ARRIS International. | [ 191 ]`
- 2019-09-18  INGN
  - this event: `List_of_S&P_400_companies · table 1 · row 329: September 18, 2019 | PK | Park Hotels & Resorts | INGN | Inogen | Market capitalization changes. [ 186 ]`
- 2019-09-23  LDOS
  - this event: `List_of_S&P_400_companies · table 1 · row 339: August 9, 2019 [ 188 ] | GRUB | Grubhub | LDOS | Leidos Holdings | Market capitalization`
  - last applied: `2019-08-09 removed: Historical_components_of_the_S&P_400 · table 1 · row 335: August 9, 2019 | GRUB | Grubhub | LDOS | Leidos Holdings | Market capitalization changes. | [ 184 ]`
- 2020-05-27  DHC
  - this event: `List_of_S&P_400_companies · table 1 · row 298: May 27, 2020 | HPP | Hudson Pacific Properties | DHC | Diversified Healthcare Trust | Hudson Pacific Properties Inc. (NYSE:HPP) replaced Diversified Healthcare `
- 2020-06-22  REZI
  - this event: `Historical_components_of_the_S&P_400 · table 1 · row 290: June 22, 2020 | UNVR | Univar Solutions | REZI | Resideo Technologies | Market capitalization changes. | [ 158 ]`
- 2021-03-22  CZR
  - this event: `List_of_S&P_400_companies · table 1 · row 256: March 22, 2021 | VNT | Vontier | CZR | Caesars Entertainment | Market capitalization change. [ 142 ]`
  - last applied: `2020-07-24 removed: List_of_S&P_400_companies · table 1 · row 285: July 24, 2020 | EBS | Emergent BioSolutions | CZR | Caesars Entertainment | S&P MidCap 400 constituent Eldorado Resorts (NASD:ERI) acquired Caesars Entertainmen`

## Missing from event walk (synthetic add at start_date) (1)

SUI

## Extra from event walk (synthetic remove at end_date) (1)

WBS


# sp600

# Reconciliation Report

- Window: **2021-03-31 → 2026-10-19**
- Seed roster size: **601**
- Current Wikipedia roster size: **603**
- Roster size after walking events: **604**
- Diff ratio vs. current: **1.00%**
- Synthetic events inserted: **1**
- Renames applied / skipped (other-index no-ops): **0 / 20**
- Fill no-ops (revision-diff events on already-consistent state): **8**

## Invalid 'added' on existing ticker (2)

- 2022-10-03  XPER
  - this event: `List_of_S&P_600_companies · table 1 · row 332: October 3, 2022 | XPER | Xperi, Inc. | SLQT | SelectQuote | Xperi Holding Corporation spun off Xperi Incorporated. Post spin off both companies remained in the `
- 2025-09-02  BHLB
  - this event: `List_of_S&P_600_companies · table 1 · row 114: September 2, 2025 | BHLB | Berkshire Hills Bancorp | BBT | Beacon Financial Corp. | BHLB acquired Brookline Bancorp. Post merger, BHLB remained in the S&P 600 w`

## Invalid 'removed' on missing ticker (3)

- 2025-01-02  GEAR
  - this event: `List_of_S&P_600_companies · table 1 · row 147: January 2, 2025 | GDYN | Grid Dynamics Holdings | GEAR | Revelyst | GDYN replaced GEAR after it was acquired by Strategic Value Partners. [ 70 ]`
- 2025-09-02  BBT
  - this event: `List_of_S&P_600_companies · table 1 · row 114: September 2, 2025 | BHLB | Berkshire Hills Bancorp | BBT | Beacon Financial Corp. | BHLB acquired Brookline Bancorp. Post merger, BHLB remained in the S&P 600 w`
- 2026-03-23  AHRT
  - this event: `List_of_S&P_600_companies · table 1 · row 58: March 23, 2026 | LAUR | Laureate Education | AHRT | AH Realty Trust | LAUR replaced AHRT as it was no longer representative of the small-cap market space. [ 32 `

## Missing from event walk (synthetic add at start_date) (0)

_none_

## Extra from event walk (synthetic remove at end_date) (1)

ALSK
