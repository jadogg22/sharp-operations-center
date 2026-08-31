from __future__ import annotations

from io import BytesIO
from statistics import fmean, pstdev

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import LaneLoad

TARGET_REVENUE_PER_MILE = 2.79
BRAND_GREEN = colors.HexColor("#174D37")
MUTED = colors.HexColor("#66716A")
PALE_GREEN = colors.HexColor("#E6EFE8")
PALE_GOLD = colors.HexColor("#F7E9BA")
LANE_SCALE = LinearSegmentedColormap.from_list(
    "lane_scale", ["#A14935", "#F0C75E", "#174D37"]
)


def _safe_mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0


def _z_scores(values: list[float]) -> list[float]:
    # Quality scores compare lanes on different scales (RPM, volume, and empty
    # miles), so standardize each metric before combining it.
    if not values:
        return []
    deviation = pstdev(values)
    if deviation == 0:
        return [0.0] * len(values)
    mean = fmean(values)
    return [(value - mean) / deviation for value in values]


def analyze_lanes(loads: list[LaneLoad]) -> list[dict[str, float | int | str]]:
    one_way: dict[tuple[str, str], list[LaneLoad]] = {}
    for load in loads:
        if (
            load.total_miles <= 0
            or load.total_revenue <= 0
            or not load.origin_state
            or not load.destination_state
            or load.origin_state == load.destination_state
        ):
            continue
        one_way.setdefault((load.origin_state, load.destination_state), []).append(load)

    lanes: list[dict[str, float | int | str]] = []
    destinations = sorted(destination for origin, destination in one_way if origin == "UT")
    for destination in destinations:
        outbound = one_way.get(("UT", destination), [])
        inbound = one_way.get((destination, "UT"), [])
        if not outbound or not inbound:
            continue

        outbound_rpm = _safe_mean([load.total_revenue / load.total_miles for load in outbound])
        inbound_rpm = _safe_mean([load.total_revenue / load.total_miles for load in inbound])
        combined = outbound + inbound
        lanes.append(
            {
                "destination": destination,
                "outbound_rpm": outbound_rpm,
                "inbound_rpm": inbound_rpm,
                "round_trip_rpm": (outbound_rpm + inbound_rpm) / 2,
                "outbound_trips": len(outbound),
                "inbound_trips": len(inbound),
                "total_trips": len(combined),
                "empty_pct": _safe_mean(
                    [load.empty_miles / load.total_miles for load in combined]
                ),
            }
        )

    if not lanes:
        return lanes

    # Empty-mile z-score is subtracted because less empty mileage is better;
    # inbound/outbound revenue and trip volume are positive contributors.
    outbound_scores = _z_scores([float(lane["outbound_rpm"]) for lane in lanes])
    inbound_scores = _z_scores([float(lane["inbound_rpm"]) for lane in lanes])
    trip_scores = _z_scores([float(lane["total_trips"]) for lane in lanes])
    empty_scores = _z_scores([float(lane["empty_pct"]) for lane in lanes])
    for index, lane in enumerate(lanes):
        lane["quality_score"] = (
            outbound_scores[index]
            + inbound_scores[index]
            + trip_scores[index]
            - (0.5 * empty_scores[index])
        )

    return sorted(lanes, key=lambda lane: float(lane["quality_score"]), reverse=True)


def _chart_to_buffer(fig: plt.Figure) -> BytesIO:
    output = BytesIO()
    fig.savefig(output, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    output.seek(0)
    return output


def _lane_colors(values: list[float]) -> list[tuple[float, float, float, float]]:
    if not values:
        return []
    minimum, maximum = min(values), max(values)
    if minimum == maximum:
        return [LANE_SCALE(0.72)] * len(values)
    scale = Normalize(vmin=minimum, vmax=maximum)
    return [LANE_SCALE(scale(value)) for value in values]


def _round_trip_chart(lanes: list[dict[str, float | int | str]]) -> BytesIO:
    ordered = sorted(lanes, key=lambda lane: float(lane["round_trip_rpm"]), reverse=True)
    values = [float(lane["round_trip_rpm"]) for lane in ordered]
    fig, axis = plt.subplots(figsize=(8.2, max(4.7, len(ordered) * 0.34 + 1.6)))
    bars = axis.barh(
        [str(lane["destination"]) for lane in ordered][::-1],
        values[::-1],
        color=_lane_colors(values)[::-1],
        height=0.68,
    )
    axis.axvline(TARGET_REVENUE_PER_MILE, color="#B35C35", linestyle="--", linewidth=1.5)
    axis.set_xlabel("Average round-trip revenue per mile ($/mile)")
    axis.set_ylabel("Destination state")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="x", color="#E5E9E6", linewidth=0.8)
    axis.set_axisbelow(True)
    for bar in bars:
        axis.text(
            bar.get_width() + 0.035,
            bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():.2f}",
            ha="left",
            va="center",
            fontsize=7,
            color="#59635C",
        )
    fig.tight_layout()
    return _chart_to_buffer(fig)


def _direction_chart(lanes: list[dict[str, float | int | str]]) -> BytesIO:
    ordered = sorted(lanes, key=lambda lane: float(lane["round_trip_rpm"]))
    destinations = [str(lane["destination"]) for lane in ordered]
    figure_height = max(4.7, len(ordered) * 0.34 + 1.6)
    fig, axes = plt.subplots(1, 2, figsize=(8.2, figure_height), sharey=True)
    for axis, key, title, color in (
        (axes[0], "outbound_rpm", "Outbound", "#174D37"),
        (axes[1], "inbound_rpm", "Inbound", "#F0C75E"),
    ):
        values = [float(lane[key]) for lane in ordered]
        bars = axis.barh(destinations, values, color=color, height=0.68)
        axis.axvline(TARGET_REVENUE_PER_MILE, color="#B35C35", linestyle="--", linewidth=1.2)
        axis.set_title(title, loc="left", fontsize=10, fontweight="bold", color="#174D37")
        axis.set_xlabel("$/mile")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="x", color="#E5E9E6", linewidth=0.8)
        axis.set_axisbelow(True)
        for bar in bars:
            axis.text(
                bar.get_width() + 0.035,
                bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.2f}",
                ha="left",
                va="center",
                fontsize=7,
                color="#59635C",
            )
    axes[0].set_ylabel("Destination state")
    fig.tight_layout()
    return _chart_to_buffer(fig)


def _scatter_chart(lanes: list[dict[str, float | int | str]]) -> BytesIO:
    fig, axis = plt.subplots(figsize=(8.2, 5.1))
    for lane in lanes:
        size = 42 + int(lane["total_trips"]) * 6
        axis.scatter(
            float(lane["outbound_rpm"]),
            float(lane["inbound_rpm"]),
            s=size,
            color="#F0C75E",
            edgecolor="#174D37",
            linewidth=1,
            alpha=0.88,
        )
        axis.annotate(
            str(lane["destination"]),
            (float(lane["outbound_rpm"]), float(lane["inbound_rpm"])),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            fontweight="bold",
        )
    axis.axhline(TARGET_REVENUE_PER_MILE, color="#B35C35", linestyle="--", linewidth=1.2)
    axis.axvline(TARGET_REVENUE_PER_MILE, color="#B35C35", linestyle="--", linewidth=1.2)
    axis.set_xlabel("Outbound revenue per mile")
    axis.set_ylabel("Inbound revenue per mile")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(color="#E5E9E6", linewidth=0.8)
    fig.tight_layout()
    return _chart_to_buffer(fig)


def _lane_pdf_styles() -> tuple[ParagraphStyle, ParagraphStyle, ParagraphStyle]:
    """Create the paragraph styles shared by every lane-PDF section."""
    styles = getSampleStyleSheet()
    return (
        ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=BRAND_GREEN, alignment=TA_LEFT, spaceAfter=8),
        ParagraphStyle("Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=BRAND_GREEN, spaceAfter=8),
        ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=MUTED),
    )


def _lane_summary_table(loads: list[LaneLoad], lanes: list[dict[str, float | int | str]]) -> Table:
    """Build the KPI table shown at the top of the lane report."""
    total_revenue = sum(load.total_revenue for load in loads)
    total_miles = sum(load.total_miles for load in loads)
    avg_rpm = total_revenue / total_miles if total_miles else 0
    table = Table(
        [["Loads", "Revenue", "Revenue / mile", "Round-trip lanes"],
         [f"{len(loads):,}", f"${total_revenue:,.0f}", f"${avg_rpm:,.2f}", f"{len(lanes):,}"]],
        colWidths=[1.75 * inch] * 4,
        rowHeights=[0.3 * inch, 0.52 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE_GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_GREEN),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("TEXTCOLOR", (0, 1), (-1, 1), BRAND_GREEN), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CFD9D1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DEE5DF")),
    ]))
    return table


def generate_lane_profitability_pdf(
    loads: list[LaneLoad], start_date: str, end_date: str
) -> bytes:
    """Generate a multi-page PDF from analyzed lanes and supporting charts.

    Analysis happens before document construction so a report with no complete
    Utah round trips fails clearly instead of producing a blank PDF.
    """
    lanes = analyze_lanes(loads)
    if not lanes:
        raise ValueError("No complete Utah round-trip lanes were found for this period")

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.55 * inch,
        title=f"Lane Profitability {start_date} to {end_date}",
    )
    title, heading, body = _lane_pdf_styles()

    top_lane = lanes[0]

    story = [
        Paragraph("Sharp Transportation", body),
        Paragraph("Lane profitability", title),
        Paragraph(f"{start_date} through {end_date}", body),
        Spacer(1, 0.24 * inch),
    ]
    summary = _lane_summary_table(loads, lanes)
    story.extend(
        [
            summary,
            Spacer(1, 0.28 * inch),
            Paragraph("What stands out", heading),
            Paragraph(
                f'<b>{top_lane["destination"]}</b> has the strongest composite lane score in this period, '
                f'with ${float(top_lane["round_trip_rpm"]):.2f} average round-trip revenue per mile '
                f'across {int(top_lane["total_trips"])} movements. The score balances inbound and outbound '
                "revenue, trip volume, and empty-mile percentage.",
                body,
            ),
            Spacer(1, 0.2 * inch),
        ]
    )

    table_data = [["Lane", "Out $/mi", "In $/mi", "Trips", "Empty %", "Score"]]
    for lane in lanes[:12]:
        table_data.append(
            [
                f'UT ↔ {lane["destination"]}',
                f'${float(lane["outbound_rpm"]):.2f}',
                f'${float(lane["inbound_rpm"]):.2f}',
                f'{int(lane["total_trips"])}',
                f'{float(lane["empty_pct"]):.1%}',
                f'{float(lane["quality_score"]):.2f}',
            ]
        )
    ranking = Table(table_data, colWidths=[1.45 * inch, 1.05 * inch, 1.05 * inch, 0.7 * inch, 0.9 * inch, 0.8 * inch])
    ranking.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8F5")]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE2DD")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([ranking, PageBreak()])

    round_trip_chart = _round_trip_chart(lanes)
    story.extend(
        [
            Paragraph("Average round-trip revenue", heading),
            Paragraph(
                "Bars are ranked highest to lowest and shaded from lower to stronger round-trip performance. The dashed line is the current $2.79 target; labels show the average number only.",
                body,
            ),
            Spacer(1, 0.14 * inch),
            Image(round_trip_chart, width=7.15 * inch, height=4.1 * inch),
            PageBreak(),
        ]
    )

    direction_chart = _direction_chart(lanes)
    story.extend(
        [
            Paragraph("Outbound and inbound detail", heading),
            Paragraph(
                "The split view keeps each direction visible on its own so sales and operations can see whether a lane is being carried by outbound or inbound pricing. The dashed line is the $2.79 target.",
                body,
            ),
            Spacer(1, 0.14 * inch),
            Image(direction_chart, width=7.15 * inch, height=4.45 * inch),
            Spacer(1, 0.18 * inch),
            Table(
                [["Target", "$2.79 / mile"], ["Best composite lane", f'UT ↔ {top_lane["destination"]}']],
                colWidths=[2.0 * inch, 3.0 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), PALE_GOLD),
                        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_GREEN),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DADFD9")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E3E7E3")),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
        ]
    )

    def add_page_number(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.6 * inch, 0.34 * inch, "Sharp Transportation - Internal")
        canvas.drawRightString(7.9 * inch, 0.34 * inch, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return output.getvalue()
