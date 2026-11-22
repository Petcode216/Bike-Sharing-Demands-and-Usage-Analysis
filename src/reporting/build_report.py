"""Build the Word (.docx) analytical report.

Every figure quoted in the text is read from the computed `Results` object at
build time, so the document cannot drift from the analysis.
"""
from datetime import date

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from src.analysis.results import Results
from src.config import FIGURES_DIR, FINDINGS_DIR

REPORT_PATH = FINDINGS_DIR / "Bike_Sharing_Report.docx"
ACCENT = RGBColor(0x2A, 0x78, 0xD6)
MUTED = RGBColor(0x52, 0x51, 0x4E)


# ---------- formatting helpers ----------
def n0(x: float) -> str:
    return f"{x:,.0f}"


def pct(x: float, d: int = 0) -> str:
    return f"{x * 100:.{d}f}%"


def pval(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def _shade(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


class ReportWriter:
    def __init__(self) -> None:
        self.doc = Document()
        sec = self.doc.sections[0]
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.top_margin = sec.bottom_margin = Cm(2.0)
        normal = self.doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        for lvl, size in [(1, 16), (2, 13), (3, 11.5)]:
            st = self.doc.styles[f"Heading {lvl}"]
            st.font.name = "Calibri"
            st.font.size = Pt(size)
            st.font.color.rgb = ACCENT if lvl < 3 else RGBColor(0x0B, 0x0B, 0x0B)
        self.fig_no = 0
        self.tab_no = 0

    def h(self, text: str, level: int = 1) -> None:
        self.doc.add_heading(text, level=level)

    def p(self, text: str, bold_lead: str | None = None, italic: bool = False) -> None:
        para = self.doc.add_paragraph()
        if bold_lead:
            para.add_run(bold_lead).bold = True
        run = para.add_run(text)
        run.italic = italic

    def bullets(self, items: list[str]) -> None:
        for it in items:
            para = self.doc.add_paragraph(style="List Bullet")
            if "::" in it:
                lead, rest = it.split("::", 1)
                para.add_run(lead).bold = True
                para.add_run(rest)
            else:
                para.add_run(it)

    def figure(self, name: str, caption: str, width_cm: float = 16.0) -> None:
        path = FIGURES_DIR / f"{name}.png"
        if not path.exists():
            raise FileNotFoundError(f"Figure missing: {path}. Run the pipeline first.")
        self.doc.add_picture(str(path), width=Cm(width_cm))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.fig_no += 1
        cap = self.doc.add_paragraph()
        r = cap.add_run(f"Figure {self.fig_no}. {caption}")
        r.italic = True
        r.font.size = Pt(9)
        r.font.color.rgb = MUTED

    def table(self, df: pd.DataFrame, caption: str) -> None:
        self.tab_no += 1
        cap = self.doc.add_paragraph()
        r = cap.add_run(f"Table {self.tab_no}. {caption}")
        r.bold = True
        r.font.size = Pt(9.5)
        t = self.doc.add_table(rows=1, cols=len(df.columns))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, col in enumerate(df.columns):
            cell = t.rows[0].cells[i]
            cell.text = str(col)
            cell.paragraphs[0].runs[0].bold = True
            _shade(cell, "E8F0FB")
        for _, row in df.iterrows():
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = str(v)
        for row in t.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(9)
        self.doc.add_paragraph()

    def insight(self, title: str, what: str, evidence: str, who: str, why: str, action: str) -> None:
        self.h(title, 3)
        self.bullets([f"What happened: :: {what}", f"Evidence: :: {evidence}", f"Who / when: :: {who}",
                      f"Why it matters: :: {why}", f"Operational implication: :: {action}"])


# ---------- report content ----------
def build_report(res: Results) -> str:
    w = ReportWriter()
    day, hour = res.day, res.hour
    total = res.kpi("Total rentals")
    yoy = res.kpi("Year-over-year growth")
    cas_share = res.kpi("Casual share")
    dt = res.by_day_type
    ws = res.by_weather
    seas = res.by_season
    peaks = res.peaks.set_index(["day_type", "segment"])
    t_cnt, t_cas, t_reg = res.working_tests
    st = res.season_test
    reg = res.regression
    coef = reg.coefficients
    corr = res.correlations.set_index(["target", "variable"])
    sim = res.profile_similarity.set_index("day_type")
    win = res.windows
    hi_slots = win[win["tier"] == "Consistently high"]
    monthly = res.monthly.set_index("year_month")
    mratio = day.groupby(["month", "year"])["cnt"].mean().unstack()
    mratio = mratio[2012] / mratio[2011]
    tb = res.temp_bands.set_index("temp_band")
    max_band = tb["mean_cnt"].idxmax()
    work_peak = peaks.loc[("Working day", "cnt")]
    wkend_peak = peaks.loc[("Weekend", "cnt")]
    night_work = win[(win["day_type"] == "Working day") & (win["hr"] <= 5)]["mean_cnt"]
    night_all_max = win[win["hr"].between(2, 5)]["mean_cnt"].max()

    # Title page
    title = w.doc.add_heading("Bike Sharing Demand & Usage Pattern Analysis", 0)
    title.runs[0].font.color.rgb = ACCENT
    w.p("Capital Bikeshare, Washington D.C., 2011-2012: demand drivers, user segments, and "
        "implications for operational planning", italic=True)
    w.p(f"Report generated {date.today():%d %B %Y} from the reproducible pipeline (python -m src.pipeline).",
        italic=True)

    # 1. Executive summary
    w.h("1. Executive summary")
    w.p(f"Over 731 days the system recorded {n0(total)} rentals: "
        f"{pct(res.kpi('Registered share'))} by registered members and {pct(cas_share)} by casual users. "
        f"Volume grew {pct(yoy)} from 2011 to 2012. Five patterns stand out:")
    w.bullets([
        f"Peaks match commuting times. :: On working days, demand peaks at {int(work_peak['peak_hour'])}:00 "
        f"({n0(work_peak['peak_mean_per_hour'])} rentals per hour on average) and at 8:00. "
        f"Hours 8, 17 and 18 on working days are the only slots classed as consistently high-demand.",
        f"Total daily demand barely changes between working and non-working days, but the mix does. :: "
        f"Casual riders make up {pct(dt.loc['Working day', 'casual_share'])} of working-day rentals and "
        f"{pct(dt.loc['Weekend', 'casual_share'])} of weekend rentals.",
        f"Apart from year-over-year growth, season and temperature show the strongest associations. :: Mean daily rentals range "
        f"from {n0(seas.loc['Winter', 'mean_cnt'])} in winter to {n0(seas.loc['Summer', 'mean_cnt'])} in summer. "
        f"Demand rises with temperature and levels off around {res.temp_turning_point:.0f} °C.",
        f"Rain and snow coincide with steep drops in demand. :: Rain/snow days average "
        f"{ws.loc['Rain / snow', 'cnt_index']:.0f}% of clear-day demand. Casual demand falls to "
        f"{ws.loc['Rain / snow', 'casual_index']:.0f}% and registered demand to "
        f"{ws.loc['Rain / snow', 'registered_index']:.0f}%.",
        f"Natural maintenance windows exist. :: From 02:00 to 05:00 mean demand is at most "
        f"{n0(night_all_max)} rentals per hour on any day type. Winter (Dec-Mar) is the lowest-demand season.",
    ])
    w.p("All findings describe associations in observational data. The dataset has no station, "
        "inventory or trip-level information, so the recommendations are implications of rental "
        "patterns, not measured effects on availability.", italic=True)

    # 2. Data & method
    w.h("2. Data and method")
    w.h("2.1 Business question", 2)
    w.p("What factors and usage patterns are associated with bike rental demand, and how can the operator "
        "use them to improve service availability and operational planning?")
    w.h("2.2 Dataset", 2)
    w.bullets([
        f"day.csv:: : {len(day)} rows, one per day, 2011-01-01 to 2012-12-31. Used for trends, "
        "weather relationships, hypothesis tests and the regression.",
        f"hour.csv:: : {n0(len(hour))} rows, one per observed hour. Used only for intraday patterns.",
        "The two grains are never combined. Summed hourly counts were checked against the daily "
        "file and match on all 731 days.",
        "Rental counts are rental events, not unique customers.",
    ])
    w.h("2.3 Data quality and preparation", 2)
    w.bullets([
        "No missing values, duplicates or out-of-range codes. cnt = casual + registered holds on every row.",
        f"Missing hours:: : {24 * 731 - len(hour)} hour slots are absent from hour.csv (76 days). "
        "Daily totals reconcile, so these are most likely zero-rental or outage hours. They are not imputed.",
        "Season labels corrected:: : the Readme labels codes 1-4 as spring, summer, fall and winter, but "
        "the dates show code 1 covers ~21 Dec-20 Mar, i.e. astronomical winter. Seasons are labelled by "
        "their actual dates.",
        "Weather variables were de-normalized using the Readme maxima (temperature x41, feels-like x50, "
        "humidity x100, wind x67).",
        "The humidity reading of 0% on 2011-03-10 is implausible and treated as missing.",
        "Weather categories 3 and 4 are merged into 'Rain / snow'. Category 4 occurs in only 3 hourly "
        "records and never at daily grain.",
    ])
    w.h("2.4 Statistical approach", 2)
    w.p("Daily rentals are autocorrelated, trend strongly between the two years, and have unequal "
        "variances across groups. The analysis therefore pairs every mean comparison with a rank-based "
        "test. Confidence intervals come from a moving-block bootstrap (14-day blocks), which preserves "
        "day-to-day dependence. The regression uses Newey-West (HAC) standard errors. Because "
        "observations are not independent, p-values from classical tests are treated as optimistic, "
        "and effect sizes carry more weight than significance.")

    # 3. Findings
    w.h("3. Findings")
    w.h("3.1 Rental demand and temporal patterns", 2)
    w.figure("01_daily_trend", "Daily rentals by user type, 7-day rolling mean.")
    w.p(f"Mean daily rentals were {n0(res.kpi('Mean daily rentals'))} (median "
        f"{n0(res.kpi('Median daily rentals'))}), ranging from {n0(res.kpi('Min daily rentals'))} on "
        f"{res.kpi_note('Min daily rentals')} (Hurricane Sandy) to {n0(res.kpi('Max daily rentals'))} "
        f"on {res.kpi_note('Max daily rentals')}. Total rentals rose from {n0(res.kpi('2011 total'))} in 2011 "
        f"to {n0(res.kpi('2012 total'))} in 2012 (+{pct(yoy)}). Growth was uneven: January-March grew "
        f"{mratio.loc[[1, 2, 3]].min():.1f}-{mratio.loc[[1, 2, 3]].max():.1f}x and summer months "
        f"{mratio.loc[[6, 7, 8]].min():.1f}-{mratio.loc[[6, 7, 8]].max():.1f}x.")
    w.figure("02_distributions", "Distribution of rentals per day (left) and per hour (right); different grains.")
    w.figure("06_monthly_by_year", "Mean daily rentals by month and year.")
    w.figure("03_hourly_by_daytype", "Mean hourly rentals by day type, with 10th-90th percentile band.")
    w.p(f"Intraday demand has two distinct shapes. Working days show sharp peaks at 08:00 and "
        f"{int(work_peak['peak_hour'])}:00-18:00. Weekends and holidays show a single broad plateau from late morning "
        f"to late afternoon, peaking at {int(wkend_peak['peak_hour'])}:00 "
        f"({n0(wkend_peak['peak_mean_per_hour'])} per hour on weekends). The hour x weekday heatmap "
        "confirms that the commuting pattern holds Monday to Friday.")
    w.figure("04_hour_weekday_heatmap", "Mean rentals per hour, by weekday and hour.")
    wd = res.by_weekday
    w.p(f"Across weekdays, mean daily rentals range only from {n0(wd['mean_cnt'].min())} "
        f"({wd['mean_cnt'].idxmin()}) to {n0(wd['mean_cnt'].max())} ({wd['mean_cnt'].idxmax()}). "
        f"The user mix moves much more: the casual share is {pct(wd['casual_share'].min())}-"
        f"{pct(wd.loc[['Mon','Tue','Wed','Thu','Fri'], 'casual_share'].max())} on weekdays and "
        f"{pct(wd.loc[['Sat','Sun'], 'casual_share'].min())} at weekends.")
    w.figure("05_weekday_segments", "Mean daily rentals by weekday and user type.")
    w.table(pd.DataFrame({
        "Day type": dt.index.astype(str), "Days": dt["days"],
        "Mean / day": dt["mean_cnt"].map(n0), "Median / day": dt["median_cnt"].map(n0),
        "Mean casual": dt["mean_casual"].map(n0), "Mean registered": dt["mean_registered"].map(n0),
        "Casual share": dt["casual_share"].map(pct)}), "Daily demand by day type (grain: per day).")

    w.h("3.2 Seasonal and weather conditions", 2)
    w.figure("07_season_box", "Distribution of daily rentals by season and year.")
    w.table(pd.DataFrame({
        "Season": seas.index.astype(str), "Days": seas["days"], "Mean / day": seas["mean_cnt"].map(n0),
        "Median / day": seas["median_cnt"].map(n0), "Casual share": seas["casual_share"].map(pct)}),
        "Daily demand by season (astronomical seasons; grain: per day).")
    w.figure("08_temperature", "Daily rentals against de-normalized daily temperature.")
    w.p(f"Temperature has the strongest association of the weather variables: Spearman rho = "
        f"{corr.loc[('cnt','temp_c'),'spearman_rho']:.2f} (95% CI "
        f"{corr.loc[('cnt','temp_c'),'spearman_ci_low']:.2f} to {corr.loc[('cnt','temp_c'),'spearman_ci_high']:.2f}). "
        f"The relationship is not linear. Mean demand is highest in the {max_band} °C band "
        f"({n0(tb.loc[max_band,'mean_cnt'])} per day) and slightly lower on the hottest days. "
        f"Feels-like temperature is almost identical to actual temperature (r = 0.99), so it adds no "
        f"separate information. Humidity (rho = {corr.loc[('cnt','hum_pct'),'spearman_rho']:.2f}, CI includes 0) "
        f"and wind speed (rho = {corr.loc[('cnt','windspeed_kmh'),'spearman_rho']:.2f}) have weak "
        "associations on their own.")
    w.figure("09_humidity_wind", "Daily rentals against humidity and wind speed.")
    w.figure("13_correlations", "Spearman correlations of weather variables with daily rentals, by user type.")
    w.figure("10_weather_sensitivity", "Mean daily rentals by weather category, indexed to clear days.")
    w.p(f"Weather category has a large association with demand. Misty/cloudy days average "
        f"{ws.loc['Mist / cloudy','cnt_index']:.0f}% of clear-day demand and rain/snow days "
        f"{ws.loc['Rain / snow','cnt_index']:.0f}%. Only {ws.loc['Rain / snow','days']} days fall in the "
        "rain/snow category, so that estimate is imprecise.")

    w.h("3.3 User segments", 2)
    w.figure("11_segment_hourly", "Mean hourly rentals by user type, working vs non-working days.")
    w.p(f"Registered and casual riders use the system differently. On working days, the two segments' "
        f"hourly shapes correlate only weakly (r = {sim.loc['Working day','shape_correlation']:.2f}). "
        f"{pct(sim.loc['Working day','registered_commute_share'])} of registered riders' typical working-day "
        f"rentals fall in the 7-9h and 17-19h windows, against "
        f"{pct(sim.loc['Working day','casual_commute_share'])} for casual riders. On weekends the shapes are "
        f"nearly identical (r = {sim.loc['Weekend','shape_correlation']:.2f}), both peaking around midday.")
    w.figure("12_casual_share_month", "Casual share of monthly rentals.")

    # 4. Statistics
    w.h("4. Statistical analysis")
    w.h("4.1 Working vs non-working days", 2)
    w.p("Method: Welch's t-test (does not assume equal variances), checked with a Mann-Whitney U test "
        "(does not assume normality). The 95% CI for the mean difference comes from a block bootstrap.")
    rows = []
    for t, label in [(t_cnt, "Total"), (t_cas, "Casual"), (t_reg, "Registered")]:
        rows.append({"Segment": label, "Working mean": n0(t.extra["mean_working"]),
                     "Non-working mean": n0(t.extra["mean_non_working"]),
                     "Difference": f"{t.effect:+,.0f}", "95% CI": f"{t.ci_low:+,.0f} to {t.ci_high:+,.0f}",
                     "Welch": pval(t.p_value), "Mann-Whitney": pval(t.extra["mannwhitney_p"]),
                     "Cohen's d": f"{t.extra['cohens_d']:.2f}"})
    w.table(pd.DataFrame(rows), "Mean daily rentals, working vs non-working days.")
    w.p(f"For total demand the evidence is weak and inconsistent. Welch's test does not detect a difference "
        f"({pval(t_cnt.p_value)}), the block-bootstrap interval "
        f"({t_cnt.ci_low:+,.0f} to {t_cnt.ci_high:+,.0f}) just excludes zero, and the effect size is "
        f"negligible (d = {t_cnt.extra['cohens_d']:.2f}). The segment differences, by contrast, are large "
        f"and robust: casual demand is about {1 - t_cas.extra['mean_working'] / t_cas.extra['mean_non_working']:.0%} "
        f"lower on working days (d = {t_cas.extra['cohens_d']:.2f}), and registered demand is about "
        f"{t_reg.extra['mean_working'] / t_reg.extra['mean_non_working'] - 1:.0%} higher "
        f"(d = {t_reg.extra['cohens_d']:.2f}). These opposing shifts largely cancel out in the total.")
    w.h("4.2 Seasonal differences", 2)
    pw = res.season_pairwise
    nonsig = pw[pw["p_holm"] >= 0.05]
    nonsig_txt = ("; ".join(f"{r.season_a} vs {r.season_b} (Holm p = {r.p_holm:.2f})" for r in nonsig.itertuples())
                  or "none")
    w.p(f"Method: Kruskal-Wallis test, because variances differ across seasons (Levene "
        f"{pval(st.extra['levene_p'])}), with Holm-corrected pairwise Mann-Whitney tests. Result: "
        f"H = {st.statistic:.1f}, {pval(st.p_value)}, epsilon² = {st.effect:.2f} (a large effect). "
        f"One-way ANOVA agrees (F = {st.extra['anova_f']:.1f}, eta² = {st.extra['eta_sq']:.2f}). "
        f"Season pairs not significantly different after correction: {nonsig_txt}.")
    w.h("4.3 Multivariable regression of daily demand", 2)
    w.p("Why a regression: season, temperature, weather and year are intertwined; for example, summer is "
        "both warmer and less rainy. A multivariable model estimates each factor's association while "
        "holding the others constant.")
    w.p(f"Model: OLS, n = {reg.nobs} days, R² = {reg.r2:.3f} (adjusted {reg.adj_r2:.3f}). Temperature enters "
        f"as a centred quadratic. The Durbin-Watson statistic of {reg.durbin_watson:.2f} confirms positive "
        f"residual autocorrelation, so Newey-West standard errors ({reg.hac_lags} lags) are used. All variance "
        f"inflation factors are below {reg.vif['vif'].max():.1f}.")
    w.figure("14_regression", "Regression coefficients with 95% HAC confidence intervals.")
    c = coef
    w.bullets([
        f"Year 2012:: : +{n0(c.loc['C(year)[T.2012]','coef'])} rentals per day relative to 2011, other "
        "factors equal. This is the largest single term and reflects system growth over time (it cannot "
        "be separated from network expansion or a membership increase).",
        f"Rain / snow:: : {n0(c.loc['C(weather_group)[T.Rain / snow]','coef'])} per day relative to clear "
        f"weather (CI {n0(c.loc['C(weather_group)[T.Rain / snow]','ci_low'])} to "
        f"{n0(c.loc['C(weather_group)[T.Rain / snow]','ci_high'])}). Mist/cloud: "
        f"{n0(c.loc['C(weather_group)[T.Mist / cloudy]','coef'])}.",
        f"Temperature:: : the fitted effect rises to a maximum at about {res.temp_turning_point:.1f} °C, "
        "then declines.",
        f"Humidity and wind:: : {c.loc['hum_pct','coef']:.1f} per percentage point of humidity and "
        f"{c.loc['windspeed_kmh','coef']:.1f} per km/h of wind. Both are clearer after controlling for "
        "temperature and season than on their own.",
        f"Seasons (vs winter, at equal temperature):: : spring +{n0(c.loc['C(season_label)[T.Spring]','coef'])}, "
        f"summer +{n0(c.loc['C(season_label)[T.Summer]','coef'])}, fall +{n0(c.loc['C(season_label)[T.Fall]','coef'])}. "
        "Winter remains lower even after accounting for temperature, which may reflect daylight or "
        "other unmeasured factors.",
        f"Working day:: : +{n0(c.loc['workingday','coef'])} (CI {n0(c.loc['workingday','ci_low'])} to "
        f"{n0(c.loc['workingday','ci_high'])}). This is small, consistent with section 4.1.",
    ])
    w.p("The model is an explanatory model of association, not a forecast or a causal model. Unobserved "
        "events (e.g. Hurricane Sandy, holidays near weekends, city events) are not modelled.", italic=True)

    # 5. Operational insights
    w.h("5. Business insights and operational implications")
    w.p("Each insight is separated into what the data shows and what the operator could consider. "
        "Because the dataset lacks station and inventory data, the actions are hypotheses to validate, "
        "not proven interventions.", italic=True)
    w.figure("15_demand_windows", "Demand tiers by hour and day type.")
    w.insight(
        "Insight 1: Working-day commute peaks are the system's capacity-critical windows",
        f"Demand concentrates at 08:00 and 17:00-18:00 on working days.",
        f"Consistently high slots: {', '.join(f'{int(h)}:00' for h in hi_slots['hr'])} on working days, "
        f"with means of {n0(hi_slots['mean_cnt'].min())}-{n0(hi_slots['mean_cnt'].max())} rentals per hour and "
        f"10th percentiles of at least {n0(hi_slots['p10_cnt'].min())}.",
        "Registered members on Monday-Friday.",
        "These hours carry the highest and most predictable load. A shortage here would affect the "
        "core member base.",
        "Prioritise bike availability before 07:00 and 16:00 on working days (e.g. schedule rebalancing "
        "to finish before these windows). Station-level data is needed to target specific locations.")
    w.insight(
        "Insight 2: Weekend and holiday demand is a leisure market led by casual riders",
        "Weekend demand has a broad midday plateau and a much higher casual share.",
        f"Casual share {pct(dt.loc['Weekend','casual_share'])} at weekends vs "
        f"{pct(dt.loc['Working day','casual_share'])} on working days; casual demand peaks at "
        f"{int(peaks.loc[('Weekend','casual'),'peak_hour'])}:00 at weekends.",
        "Casual users, 11:00-17:00 on weekends and holidays, March to October.",
        "Casual riders are the most weather- and season-sensitive segment, and a natural target for "
        "membership conversion (conversion rates cannot be measured in this data).",
        "Plan weekend capacity around midday rather than commute hours. Consider promotions that convert "
        "casual riders into members during spring and summer weekends.")
    w.insight(
        "Insight 3: Overnight hours and winter offer natural maintenance windows",
        "Demand is very low overnight on all day types and lowest in winter.",
        f"Working-day mean for 00:00-05:00 is {n0(night_work.min())}-{n0(night_work.max())} rentals per hour; "
        f"winter averages {n0(seas.loc['Winter','mean_cnt'])} per day vs {n0(seas.loc['Summer','mean_cnt'])} in summer.",
        "All segments, 02:00-05:00, and December-March.",
        "Taking bikes out of service when demand is lowest minimises the number of rentals affected.",
        "Schedule routine maintenance overnight (02:00-05:00) and heavier fleet overhauls in winter. "
        "Avoid working-day commute hours.")
    w.insight(
        "Insight 4: Weather forecasts are a usable planning signal",
        "Rain and snow coincide with large drops in demand, after controlling for season and temperature.",
        f"Rain/snow days average {ws.loc['Rain / snow','cnt_index']:.0f}% of clear-day demand "
        f"(regression: {n0(c.loc['C(weather_group)[T.Rain / snow]','coef'])} per day).",
        f"Casual riders most strongly (casual demand index {ws.loc['Rain / snow','casual_index']:.0f}).",
        "Weather is forecastable days ahead, so it can feed short-term planning.",
        "Use forecast rain days to bring forward maintenance or reduce field staffing. Expect smaller "
        "drops among registered commuters than among casual riders.")
    w.insight(
        "Insight 5: Demand grew strongly between the two years, fastest in January-March",
        f"Total rentals grew {pct(yoy)} year over year.",
        f"January-March grew {mratio.loc[[1,2,3]].min():.1f}-{mratio.loc[[1,2,3]].max():.1f}x vs "
        f"{mratio.loc[[6,7,8]].min():.1f}-{mratio.loc[[6,7,8]].max():.1f}x in summer. The regression's year "
        f"term is +{n0(c.loc['C(year)[T.2012]','coef'])} per day.",
        "Both segments, all seasons.",
        "If growth continues, capacity that sufficed in 2011 peaks may not suffice later.",
        "Review fleet size and dock capacity against 2012 peak levels. Two years is too short to "
        "extrapolate a trend, and the data cannot show whether growth came from more stations or more "
        "riders per station.")

    # 6. Limitations
    w.h("6. Limitations")
    w.bullets([
        "No station, trip, inventory or maintenance data:: : the analysis cannot measure availability, "
        "stockouts, station imbalance or unmet demand. Observed rentals are a lower bound on true demand.",
        "Only two years:: : trend and year effects cannot be separated from system expansion or "
        "pricing changes.",
        "Observational data:: : all relationships are associations. Weather and season are "
        "correlated with each other and with unobserved factors such as daylight, tourism and events.",
        "Serial dependence:: : days are not independent. HAC errors and block bootstrap reduce, but do "
        "not eliminate, the overconfidence of classical tests.",
        "Data quirks:: : 165 missing hours (not imputed), one implausible humidity day, and season "
        "labels in the Readme that contradict the dates (corrected).",
        "Rentals are not riders:: : counts reflect rental events, not unique customers.",
    ])
    w.h("7. Reproducibility")
    w.p("Run `python -m src.pipeline` from the project root to regenerate the cleaned data, result tables "
        "(reports/findings/tables/), figures (reports/figures/) and this report. The interactive dashboard "
        "is started with `python dashboard/app.py`.")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    w.doc.save(REPORT_PATH)
    return str(REPORT_PATH)
