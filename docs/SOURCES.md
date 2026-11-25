# Sources

Read for this project on 25 November 2026. The column "taken from it" says exactly what is used.
Where a document could not be opened, the row says so and names the public source that was used
instead. Anything not in this table is an assumption, tagged [A] in the code and in `DOSSIER.md`
section 8.

## Regulations

| # | Source | URL | Taken from it |
|---|---|---|---|
| R1 | UN Regulation No. 11, door latches and door retention components. Text "incorporating all valid text up to Supplement 2 to the 03 series of amendments, date of entry into force 17 March 2010", Official Journal of the EU L 120, 13.5.2010 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:42010X0513(01) | Paragraph 6.1.4.1: the latch system "shall not disengage from the fully latched position when an inertial load of 30 g is applied to the door latch system, including the latch and its activation device", longitudinal and transverse. Paragraph 6.1.4.3: calculation allowed; the combined resistance must keep the system latched at 30 g. Annex 4, 2.1.1: "Spring forces are the average of the minimum spring output in the installed position and the minimum spring output in the release position. Friction effects and work to be done are not considered in the calculations." Annex 4, Figure 4-1: the sample calculation (masses, distances, spring loads and results), recomputed in `handletest/regulation.py` and checked in `tests/test_model.py`. |
| R1b | UN Regulation No. 11, later revisions (Revision 3, 04 series) on unece.org | not opened (the server refused the request) | Nothing. Paragraph and annex numbers in this repo are those of R1 and may differ in later revisions. |
| R2 | FMVSS No. 206, 49 CFR 571.206, door locks and door retention components (eCFR text as of 2 June 2025) | https://www.ecfr.gov/api/versioner/v1/full/2025-06-02/title-49.xml?part=571&section=571.206 (same wording at https://www.law.cornell.edu/cfr/text/49/571.206) | S4.1.1.4: primary and auxiliary door latch systems meet either a dynamic test or the calculation of S4.1.1.4(c): the combined resistance "must assure that the door latch system, when properly assembled in the vehicle door, will remain latched when subjected to an inertial load of 30 g". S5.1.1.4(a): the calculation follows paragraph 6 of SAE J839 (1991). |
| R3 | SAE J839 (1991), passenger car side door latch systems | not read (paid) | Nothing. Named only because R2 refers to it. |

Neither R1 nor R2 names the exterior handle in the calculation paragraphs; both say "the latch and
its activation device". Treating the handle as the activation device, and asking it to hold itself
at 30 g with its own spring, is the design rule of this study, not a quotation.

## Measurement system analysis

| # | Source | URL | Taken from it |
|---|---|---|---|
| G1 | Hilti, supplier guide "MSA studies for electronics tester qualification", version 2.0, 24.01.2024 | https://www.hilti.group/content/dam/documents/Media-Release/supplier_documents/en/Hilti_MSA-study_guide.pdf | Type-1 study: Cg = 0.2 T / (6 s), Cgk = (0.1 T - abs(mean - xm)) / (3 s), T = USL - LSL; a standard measured 50 times by one operator; Cg and Cgk at least 1.33; resolution at most 5 % of T. (The guide takes xm as the centre of the tolerance band when no calibrated standard exists; here xm is the reference value of the master.) |
| G2 | Minitab support, Type 1 Gage Study: interpretation and data considerations | https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/type-1-gage-study/interpret-the-results/all-statistics-and-graphs/ | "commonly used benchmark value of 1.33"; resolution "should not be greater than 5% of the tolerance"; 50 measurements for an adequate study; default 20 % of the tolerance. |
| G3 | AIAG, Measurement Systems Analysis, 4th edition; VDA Volume 5; Bosch booklet 10 | not read (paid, or no public copy found) | Nothing is quoted from them. The Type-1 study is used as described in G1 and G2. |

## OEE

| # | Source | URL | Taken from it |
|---|---|---|---|
| K1 | OPC 40501-1, OPC UA for Machine Tools, Part 1, v1.02, Annex C.2.4 ("example interpretation for ISO 22400") | https://reference.opcfoundation.org/specs/OPC-40501-1/c-2-4 | Availability = APT / PBT; Effectiveness = PRI x PQ / APT; Quality rate = GQ / PQ; OEE is the product of the three. APT actual production time, PBT planned busy time, PRI planned run time per item, PQ produced quantity, GQ good quantity. |
| K2 | ISO 22400-2:2014, key performance indicators for manufacturing operations management | not read (paid) | Nothing directly. The definitions are used as given in K1. The edition year is from the Wikipedia article "Overall equipment effectiveness". |

## Curve evaluation in process-monitoring units

| # | Source | URL | Taken from it |
|---|---|---|---|
| M1 | Kistler, maXYmos BL instruction manual (type 5867B), document 5867B_002-626e-04.16, read on ManualsLib | https://www.manualslib.com/manual/3114579/Kistler-Maxymos-Bl.html | The kinds of evaluation element: UNI-BOX, LINE-X, LINE-Y, NO-PASS, ENVELOPE. UNI-BOX: "The measurement curve must enter through the specified entry side once and leave through the specified exit side once." ENVELOPE: "The envelope automatically wraps around the outside contour of the bundle of curves." That manual has no element that compares the forward and the return curve; the mean and the difference of pull and return force at one travel are this study's own element. |

The elements in `plc/FB_CurveEval.scl` are simplified forms of these ideas (a force read at a set
travel, a peak that must lie in a box, a travel read at a set force, a band at fixed nodes). They
are not a copy of any product.

## Machine design

| # | Source | URL | Taken from it |
|---|---|---|---|
| D1 | Lecture slides to Shigley's Mechanical Engineering Design, chapter 10 "Mechanical Springs" (McGraw-Hill, 2012), slides 94 and 100 | https://www.philadelphia.edu.jo/academics/mgogazeh/uploads/DESIGN%202%20CH10.pdf | Helical torsion springs: Ki = (4C^2 - C - 1) / (4C(C - 1)), eq. (10-43); sigma = Ki 32 F r / (pi d^3), eq. (10-44); rate per radian k = d^4 E / (64 D Na), eq. (10-49); rate per turn k' = d^4 E / (10.2 D Na), eq. (10-50), or 10.8 with arbor friction, eq. (10-51). Equation numbers are those on the slides; they differ between editions. |
| D2 | Coulomb friction with a viscous term (friction torque = constant with the sign of the speed, plus a term proportional to speed) | textbook relation, not re-read for this project | The pivot friction model. No number is taken from a source. |

## Not found, not verified

- No public data on real door-handle spring torques, pivot friction or pull forces was used. All part
  values and their spreads are illustrative.
- No allowable stress for the spring wire was looked up. The stress at the end stop is reported, not judged.
- Whether real handle lines run a force-travel test at the end of the line is an assumption.
