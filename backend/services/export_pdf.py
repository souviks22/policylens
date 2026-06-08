"""
export_pdf.py  —  Generates a professional PDF comparison report using reportlab.
"""
from __future__ import annotations

import io
from html import escape
from datetime import datetime
from typing import Any, List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.platypus.flowables import Flowable

from models.schemas import ComparisonResult, SemanticChange, ImpactLevel, ChangeType


# ── Colour palette ───────────────────────────────────────────────────────────────
C_BG        = colors.HexColor("#1a1815")
C_SURFACE   = colors.HexColor("#2a2825")
C_BORDER    = colors.HexColor("#3d3a34")
C_TEXT      = colors.HexColor("#e8e6de")
C_MUTED     = colors.HexColor("#7a7464")
C_AMBER     = colors.HexColor("#f59e0b")
C_AMBER_LT  = colors.HexColor("#fde68a")
C_JADE      = colors.HexColor("#22c55e")
C_JADE_LT   = colors.HexColor("#bbf7d0")
C_CRIMSON   = colors.HexColor("#e11d48")
C_CRIMSON_LT= colors.HexColor("#fecdd3")
C_SAPPHIRE  = colors.HexColor("#2563eb")
C_SAPPHIRE_LT = colors.HexColor("#bfdbfe")
C_WHITE     = colors.white
C_BLACK     = colors.HexColor("#1a1815")

IMPACT_COLOR = {
    ImpactLevel.HIGH:   (C_CRIMSON,    C_CRIMSON_LT),
    ImpactLevel.MEDIUM: (C_AMBER,      C_AMBER_LT),
    ImpactLevel.LOW:    (C_JADE,       C_JADE_LT),
    ImpactLevel.NONE:   (C_MUTED,      C_BORDER),
}

CHANGE_COLOR = {
    ChangeType.ADDITION:    (C_JADE,     C_JADE_LT),
    ChangeType.DELETION:    (C_CRIMSON,  C_CRIMSON_LT),
    ChangeType.MODIFICATION:(C_AMBER,    C_AMBER_LT),
    ChangeType.REGULATORY:  (C_SAPPHIRE, C_SAPPHIRE_LT),
    ChangeType.UNCHANGED:   (C_MUTED,    C_BORDER),
}

W, H = A4
MARGIN = 18 * mm


# ── Styles ───────────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "cover_title": s("cover_title",
            fontSize=28, textColor=C_BLACK, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=6),
        "cover_sub": s("cover_sub",
            fontSize=13, textColor=C_MUTED, fontName="Helvetica",
            alignment=TA_CENTER, spaceAfter=4),
        "cover_meta": s("cover_meta",
            fontSize=9, textColor=C_MUTED, fontName="Helvetica",
            alignment=TA_CENTER, spaceAfter=2),
        "section_head": s("section_head",
            fontSize=14, textColor=C_BLACK, fontName="Helvetica-Bold",
            spaceBefore=14, spaceAfter=6),
        "subsection_head": s("subsection_head",
            fontSize=11, textColor=C_BLACK, fontName="Helvetica-Bold",
            spaceBefore=8, spaceAfter=4),
        "body": s("body",
            fontSize=9, textColor=C_BLACK, fontName="Helvetica",
            leading=14, alignment=TA_JUSTIFY, spaceAfter=4),
        "body_bold": s("body_bold",
            fontSize=9, textColor=C_BLACK, fontName="Helvetica-Bold",
            leading=14, spaceAfter=2),
        "small": s("small",
            fontSize=8, textColor=C_MUTED, fontName="Helvetica", leading=12),
        "bullet": s("bullet",
            fontSize=9, textColor=C_BLACK, fontName="Helvetica",
            leading=13, leftIndent=12, spaceAfter=2,
            bulletIndent=4, bulletFontSize=9),
        "code": s("code",
            fontSize=8, textColor=C_BLACK, fontName="Courier",
            leading=11, leftIndent=8, backColor=colors.HexColor("#f5f4f0"),
            borderPadding=(4, 6, 4, 6), spaceAfter=4),
        "label": s("label",
            fontSize=7, textColor=C_MUTED, fontName="Helvetica-Bold",
            spaceAfter=1),
    }


# ── Page template ────────────────────────────────────────────────────────────────

def _header_footer(canvas, doc, doc1_name: str, doc2_name: str):
    canvas.saveState()
    W_pt, H_pt = A4

    # Header bar
    canvas.setFillColor(C_AMBER)
    canvas.rect(0, H_pt - 10 * mm, W_pt, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(C_BLACK)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, H_pt - 6.5 * mm, "PolicyLens")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_BLACK)
    label = f"{doc1_name[:30]}  ↔  {doc2_name[:30]}"
    canvas.drawRightString(W_pt - MARGIN, H_pt - 6.5 * mm, label)

    # Footer
    canvas.setFillColor(C_BORDER)
    canvas.rect(0, 0, W_pt, 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 3 * mm, f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · PolicyLens")
    canvas.drawRightString(W_pt - MARGIN, 3 * mm, f"Page {doc.page}")

    canvas.restoreState()


# ── Main generator ────────────────────────────────────────────────────────────────

def generate_pdf(result: ComparisonResult, annotations: Optional[Sequence[Any]] = None) -> bytes:
    buf = io.BytesIO()
    ST = _build_styles()
    summary = result.summary
    annotation_map = _group_annotations(annotations or [])

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title=f"Policy Comparison — {result.doc1_name} vs {result.doc2_name}",
        author="PolicyLens",
    )

    frame = Frame(
        MARGIN, 10 * mm,
        W - 2 * MARGIN, H - 24 * mm,
        id="main",
    )
    template = PageTemplate(
        id="main",
        frames=[frame],
        onPage=lambda c, d: _header_footer(c, d, result.doc1_name, result.doc2_name),
    )
    doc.addPageTemplates([template])

    story = []

    # ── Cover ────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("POLICY COMPARISON REPORT", ST["cover_title"]))
    story.append(Spacer(1, 4 * mm))

    imp_color, imp_bg = IMPACT_COLOR[summary.overall_impact_level]
    impact_label = summary.overall_impact_level.value.upper() + " IMPACT"
    impact_table = Table(
        [[Paragraph(impact_label, ParagraphStyle("il",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=imp_color, alignment=TA_CENTER))]],
        colWidths=[50 * mm],
    )
    impact_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), imp_bg),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(_centered(impact_table, 50 * mm))
    story.append(Spacer(1, 8 * mm))

    cover_data = [
        ["Document A (Legacy)",  result.doc1_name],
        ["Document B (Updated)", result.doc2_name],
        ["Comparison ID",        result.comparison_id[:16] + "…"],
        ["Generated",            datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        ["Text Similarity",      f"{result.text_similarity_ratio * 100:.1f}%"],
    ]
    cover_table = Table(cover_data, colWidths=[45 * mm, W - 2 * MARGIN - 45 * mm])
    cover_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), C_MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), C_BLACK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f5f4f0"), C_WHITE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ── Stats row ────────────────────────────────────────────────────────────────
    story.append(Paragraph("At a Glance", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 3 * mm))

    stat_cells = [
        _stat_cell("Total Changes", str(summary.total_changes),    C_BLACK),
        _stat_cell("Additions",     str(summary.additions),         C_JADE),
        _stat_cell("Deletions",     str(summary.deletions),         C_CRIMSON),
        _stat_cell("Modifications", str(summary.modifications),     C_AMBER),
        _stat_cell("Regulatory",    str(summary.regulatory_updates),C_SAPPHIRE),
    ]
    col_w = (W - 2 * MARGIN) / 5
    stats_table = Table([stat_cells], colWidths=[col_w] * 5)
    stats_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, C_BORDER),
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f9f8f5")),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 5 * mm))

    # ── Document statistics rendered in the frontend ────────────────────────────
    story.append(Paragraph("Document Statistics", ST["subsection_head"]))
    doc_stats_rows = [[
        Paragraph("<b>Document</b>", _th_style()),
        Paragraph("<b>Pages</b>", _th_style()),
        Paragraph("<b>Words</b>", _th_style()),
        Paragraph("<b>Characters</b>", _th_style()),
        Paragraph("<b>Sections</b>", _th_style()),
    ]]
    for label, stats in [
        ("Document A (Legacy)", result.doc1_stats),
        ("Document B (Updated)", result.doc2_stats),
    ]:
        doc_stats_rows.append([
            Paragraph(label, _cell_style()),
            Paragraph(str(stats.total_pages), _cell_style()),
            Paragraph(f"{stats.total_words:,}", _cell_style()),
            Paragraph(f"{stats.total_characters:,}", _cell_style()),
            Paragraph(str(len(stats.sections_detected)), _cell_style()),
        ])
    doc_stats_tbl = Table(
        doc_stats_rows,
        colWidths=[48 * mm, 22 * mm, 26 * mm, 28 * mm, W - 2 * MARGIN - 124 * mm],
        repeatRows=1,
    )
    doc_stats_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_AMBER),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(doc_stats_tbl)

    for label, sections in [
        ("Document A Detected Sections", result.doc1_sections),
        ("Document B Detected Sections", result.doc2_sections),
    ]:
        if sections:
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(label, ST["subsection_head"]))
            for section_name in sections:
                story.append(Paragraph(f"• {_safe(section_name)}", ST["bullet"]))

    # ── Executive Summary ────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 2 * mm))
    for para in summary.executive_summary.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), ST["body"]))

    # Key changes
    if summary.key_changes:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("Key Changes", ST["subsection_head"]))
        for kc in summary.key_changes:
            story.append(Paragraph(f"• {kc}", ST["bullet"]))

    # Risk areas + compliance flags in two columns
    side_items = []
    if summary.risk_areas:
        side_items.append(("Risk Areas", summary.risk_areas, C_CRIMSON_LT, C_CRIMSON))
    if summary.compliance_flags:
        side_items.append(("Compliance Flags", summary.compliance_flags, C_SAPPHIRE_LT, C_SAPPHIRE))

    if side_items:
        story.append(Spacer(1, 3 * mm))
        full_w = W - 2 * MARGIN
        if len(side_items) == 2:
            # FIX: use a fixed gap, zero out its cell padding so width never goes negative
            GAP = 4 * mm
            half = (full_w - GAP) / 2
            left  = _side_box_content(side_items[0][0], side_items[0][1], side_items[0][2], half)
            right = _side_box_content(side_items[1][0], side_items[1][1], side_items[1][2], half)
            two_col = Table([[left, "", right]], colWidths=[half, GAP, half], splitByRow=1)
            two_col.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND",    (0, 0), (0, 0), side_items[0][2]),
                ("BACKGROUND",    (2, 0), (2, 0), side_items[1][2]),
                ("BOX",           (0, 0), (0, 0), 0.5, side_items[0][3]),
                ("BOX",           (2, 0), (2, 0), 0.5, side_items[1][3]),
                ("TOPPADDING",    (0, 0), (0, 0), 6),
                ("BOTTOMPADDING", (0, 0), (0, 0), 6),
                ("LEFTPADDING",   (0, 0), (0, 0), 8),
                ("RIGHTPADDING",  (0, 0), (0, 0), 8),
                ("TOPPADDING",    (2, 0), (2, 0), 6),
                ("BOTTOMPADDING", (2, 0), (2, 0), 6),
                ("LEFTPADDING",   (2, 0), (2, 0), 8),
                ("RIGHTPADDING",  (2, 0), (2, 0), 8),
                # Zero out all padding on the gap column so its cell never has negative available width
                ("LEFTPADDING",   (1, 0), (1, 0), 0),
                ("RIGHTPADDING",  (1, 0), (1, 0), 0),
                ("TOPPADDING",    (1, 0), (1, 0), 0),
                ("BOTTOMPADDING", (1, 0), (1, 0), 0),
            ]))
            story.append(two_col)
        else:
            item = side_items[0]
            story.append(_side_box(item[0], item[1], item[2], item[3], full_w))

    story.append(PageBreak())

    # ── Changes table ────────────────────────────────────────────────────────────
    story.append(Paragraph("Semantic Changes", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 2 * mm))

    if not result.semantic_changes:
        story.append(Paragraph("No semantic changes were identified.", ST["body"]))
    else:
        col_widths = [28 * mm, 25 * mm, 18 * mm, W - 2 * MARGIN - 28 * mm - 25 * mm - 18 * mm]
        header = [
            Paragraph("<b>Type</b>",    _th_style()),
            Paragraph("<b>Section</b>", _th_style()),
            Paragraph("<b>Impact</b>",  _th_style()),
            Paragraph("<b>Summary</b>", _th_style()),
        ]
        rows = [header]
        row_styles: List = [
            ("BACKGROUND", (0, 0), (-1, 0), C_AMBER),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_BLACK),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.3, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        for i, chg in enumerate(result.semantic_changes):
            bg = colors.HexColor("#f9f8f5") if i % 2 == 0 else C_WHITE
            row_styles.append(("BACKGROUND", (0, i + 1), (-1, i + 1), bg))
            _, ct_lt = CHANGE_COLOR.get(chg.change_type, (C_MUTED, C_BORDER))
            _, il_lt = IMPACT_COLOR.get(chg.impact_level, (C_MUTED, C_BORDER))
            row_styles.append(("BACKGROUND", (0, i + 1), (0, i + 1), ct_lt))
            row_styles.append(("BACKGROUND", (2, i + 1), (2, i + 1), il_lt))

            rows.append([
                Paragraph(_change_label(chg.change_type), _cell_style()),
                Paragraph(chg.section or "General", _cell_style()),
                Paragraph(chg.impact_level.value.upper(), _cell_style()),
                Paragraph(chg.summary, _cell_style()),
            ])

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle(row_styles))
        story.append(tbl)

    story.append(PageBreak())

    # ── Detailed changes ─────────────────────────────────────────────────────────
    story.append(Paragraph("Detailed Change Analysis", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))

    for idx, chg in enumerate(result.semantic_changes, 1):
        block = _change_detail_block(idx, chg, ST, W - 2 * MARGIN, annotation_map.get(chg.id, []))
        story.extend(block)
        story.append(Spacer(1, 3 * mm))

    # ── Section analysis ─────────────────────────────────────────────────────────
    if result.section_analysis and result.section_analysis.matches:
        story.append(PageBreak())
        story.append(Paragraph("Section Alignment Analysis", ST["section_head"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"Overall structural similarity: {result.section_analysis.overall_structural_similarity * 100:.1f}%",
            ST["body_bold"],
        ))
        counts = {
            "unchanged": sum(1 for m in result.section_analysis.matches if m.match_type == "unchanged"),
            "modified": sum(1 for m in result.section_analysis.matches if m.match_type == "modified"),
            "added": sum(1 for m in result.section_analysis.matches if m.match_type == "added"),
            "deleted": sum(1 for m in result.section_analysis.matches if m.match_type == "deleted"),
        }
        story.append(Paragraph(
            "Section counts: "
            f"unchanged={counts['unchanged']}, modified={counts['modified']}, "
            f"added={counts['added']}, deleted={counts['deleted']}",
            ST["small"],
        ))
        story.append(Spacer(1, 2 * mm))

        if result.section_analysis.semantic_clone_pairs:
            story.append(Paragraph("Semantic Clone Sections", ST["subsection_head"]))
            for h1, h2 in result.section_analysis.semantic_clone_pairs:
                story.append(Paragraph(f"• {_safe(h1)} ↔ {_safe(h2)}", ST["bullet"]))
            story.append(Spacer(1, 2 * mm))

        sa_col = [(W - 2 * MARGIN - 18 * mm) / 3] * 3 + [18 * mm]
        sa_header = [Paragraph(h, _th_style()) for h in ["Doc A Section", "Doc B Section", "Status", "Score"]]
        sa_rows = [sa_header]
        sa_styles: List = [
            ("BACKGROUND", (0, 0), (-1, 0), C_AMBER),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.3, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        for i, m in enumerate(result.section_analysis.matches):
            bg = colors.HexColor("#f9f8f5") if i % 2 == 0 else C_WHITE
            sa_styles.append(("BACKGROUND", (0, i + 1), (-1, i + 1), bg))
            sa_rows.append([
                Paragraph(m.doc1_section or "—", _cell_style()),
                Paragraph(m.doc2_section or "—", _cell_style()),
                Paragraph(m.match_type.upper(), _cell_style()),
                Paragraph(f"{m.similarity_score:.2f}", _cell_style()),
            ])
        sa_tbl = Table(sa_rows, colWidths=sa_col, repeatRows=1)
        sa_tbl.setStyle(TableStyle(sa_styles))
        story.append(sa_tbl)

        story.append(PageBreak())
        story.append(Paragraph("Section Match Details", ST["section_head"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
        for idx, m in enumerate(result.section_analysis.matches, 1):
            story.append(Paragraph(
                f"{idx}. {_safe(m.match_type.title())}: {_safe(m.doc1_section or 'Not present')} / {_safe(m.doc2_section or 'Not present')}",
                ST["subsection_head"],
            ))
            story.append(Paragraph(f"Similarity score: {m.similarity_score:.4f}", ST["small"]))
            story.append(_side_by_side_box(
                f"DOCUMENT A - {m.doc1_section or 'Not present'}",
                m.doc1_content or "Section not present in Document A",
                C_CRIMSON,
                f"DOCUMENT B - {m.doc2_section or 'Not present'}",
                m.doc2_content or "Section not present in Document B",
                C_JADE,
                W - 2 * MARGIN,
            ))
            story.append(Spacer(1, 2 * mm))

        if result.section_analysis.similarity_matrix:
            story.append(PageBreak())
            story.append(Paragraph("Section Cosine Similarity Matrix", ST["section_head"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            story.append(Paragraph(
                f"Rows = Document A ({len(result.section_analysis.doc1_section_labels)} sections); "
                f"columns = Document B ({len(result.section_analysis.doc2_section_labels)} sections).",
                ST["small"],
            ))
            for i, row in enumerate(result.section_analysis.similarity_matrix):
                label = result.section_analysis.doc1_section_labels[i] if i < len(result.section_analysis.doc1_section_labels) else f"Row {i + 1}"
                values = " | ".join(f"{v:.3f}" for v in row)
                story.extend(_long_text_flowables(f"{label}: {values}", ST["code"], chunk_size=1800))

    # ── Diff chunks rendered by the frontend diff tab ───────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Text Diff - Changed Blocks", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    changed_chunks = [c for c in result.diff_chunks if c.type != ChangeType.UNCHANGED]
    if not changed_chunks:
        story.append(Paragraph("No textual differences detected.", ST["body"]))
    for idx, chunk in enumerate(changed_chunks, 1):
        story.append(Paragraph(
            f"{idx}. {_change_label(chunk.type)} - {_safe(chunk.section or 'General')}",
            ST["subsection_head"],
        ))
        story.append(_side_by_side_box(
            "DOCUMENT A", chunk.old_text or "—", C_CRIMSON,
            "DOCUMENT B", chunk.new_text or "—", C_JADE,
            W - 2 * MARGIN,
        ))
        story.append(Spacer(1, 2 * mm))

    # ── Full source text rendered in the side-by-side frontend view ─────────────
    story.append(PageBreak())
    story.append(Paragraph("Full Source Text - Document A", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.extend(_long_text_flowables(result.doc1_content, ST["code"]))

    story.append(PageBreak())
    story.append(Paragraph("Full Source Text - Document B", ST["section_head"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.extend(_long_text_flowables(result.doc2_content, ST["code"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _centered(table, width):
    wrap = Table([[table]], colWidths=[width])
    wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return wrap


def _stat_cell(label: str, value: str, color) -> Paragraph:
    text = f'<font color="{color.hexval()}" size="18"><b>{value}</b></font><br/><font size="7" color="#7a7464">{label}</font>'
    return Paragraph(text, ParagraphStyle("sc", alignment=TA_CENTER, leading=22))


def _th_style():
    return ParagraphStyle("th", fontSize=8, fontName="Helvetica-Bold",
                          textColor=C_BLACK, alignment=TA_LEFT)


def _cell_style():
    return ParagraphStyle("cell", fontSize=8, fontName="Helvetica",
                          textColor=C_BLACK, leading=11)


def _change_label(ct: ChangeType) -> str:
    return {
        ChangeType.ADDITION:     "Addition",
        ChangeType.DELETION:     "Deletion",
        ChangeType.MODIFICATION: "Modification",
        ChangeType.REGULATORY:   "Regulatory",
        ChangeType.UNCHANGED:    "Unchanged",
    }.get(ct, ct.value)


def _side_box(title: str, items: List[str], bg_color, title_color, width) -> Table:
    content = [Paragraph(f"<b>{title}</b>", ParagraphStyle(
        "bh", fontSize=9, textColor=title_color, fontName="Helvetica-Bold", spaceAfter=3))]
    for item in items:
        content.append(Paragraph(f"• {item}", ParagraphStyle(
            "bi", fontSize=8, textColor=C_BLACK, fontName="Helvetica", leading=12, leftIndent=8)))
    tbl = Table([[content]], colWidths=[width], splitByRow=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.5, title_color),
    ]))
    return tbl


def _side_box_content(title: str, items: List[str], title_color, width) -> Paragraph:
    parts = [f'<font size="9" color="{title_color.hexval()}"><b>{_safe(title)}</b></font>']
    for item in items:
        parts.append(f'<font size="8" color="{C_BLACK.hexval()}">• {_safe(item)}</font>')
    return Paragraph("<br/>".join(parts), ParagraphStyle(
        "sb", fontSize=8, fontName="Helvetica", leading=12, spaceAfter=2))


def _change_detail_block(
    idx: int,
    chg: SemanticChange,
    ST: dict,
    full_width: float,
    annotations: Sequence[Any],
) -> List:
    ct_color, ct_bg = CHANGE_COLOR.get(chg.change_type, (C_MUTED, C_BORDER))
    il_color, il_bg = IMPACT_COLOR.get(chg.impact_level, (C_MUTED, C_BORDER))

    header_left = Paragraph(
        f'<b>{idx}. {_safe(chg.summary)}</b>',
        ParagraphStyle("ch", fontSize=9, fontName="Helvetica-Bold", textColor=C_BLACK))

    badges = Table([[
        Paragraph(_change_label(chg.change_type),
            ParagraphStyle("cb", fontSize=7, textColor=ct_color,
                fontName="Helvetica-Bold", alignment=TA_CENTER)),
        Paragraph(chg.impact_level.value.upper() + " IMPACT",
            ParagraphStyle("ib", fontSize=7, textColor=il_color,
                fontName="Helvetica-Bold", alignment=TA_CENTER)),
    ]], colWidths=[25 * mm, 25 * mm])
    badges.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), ct_bg),
        ("BACKGROUND",    (1, 0), (1, 0), il_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("BOX",           (0, 0), (0, 0), 0.3, ct_color),
        ("BOX",           (1, 0), (1, 0), 0.3, il_color),
    ]))

    header = Table([[header_left, badges]], colWidths=[full_width - 55 * mm, 55 * mm])
    header.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f5f4f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))

    block = [header]

    # Section label
    if chg.section and chg.section != "General":
        block.append(Paragraph(
            f"Section: {_safe(chg.section)}",
            ParagraphStyle("sec", fontSize=7, textColor=C_MUTED, fontName="Helvetica",
                           leftIndent=8, spaceAfter=2, spaceBefore=2)))

    # Before / After
    if chg.old_content or chg.new_content:
        ba = _side_by_side_box(
            "BEFORE", chg.old_content or "(not present)", C_CRIMSON,
            "AFTER",  chg.new_content or "(not present)", C_JADE,
            full_width,
        )
        block.append(Spacer(1, 1.5 * mm))
        block.append(ba)

    # Explanation
    if chg.explanation:
        block.append(Spacer(1, 1.5 * mm))
        block.append(Paragraph(f"<b>Analysis:</b> {_safe(chg.explanation)}",
            ParagraphStyle("exp", fontSize=8, fontName="Helvetica", textColor=C_BLACK,
                           leading=12, leftIndent=8, alignment=TA_JUSTIFY)))

    # Impact grid
    impact_items = [
        ("Business",    chg.business_impact),
        ("Compliance",  chg.compliance_impact),
        ("Regulatory",  chg.regulatory_impact),
    ]
    impact_items = [(k, v) for k, v in impact_items if v and v.strip()]
    if impact_items:
        iw = full_width / len(impact_items)
        impact_cells = []
        for label, text in impact_items:
            impact_cells.append(Paragraph(
                f'<font size="7" color="#7a7464"><b>{label.upper()}</b></font><br/>'
                f'<font size="8">{_safe(text)}</font>',
                ParagraphStyle("imp", fontSize=8, fontName="Helvetica",
                               textColor=C_BLACK, leading=12, leftIndent=4)))
        ig = Table([impact_cells], colWidths=[iw] * len(impact_cells))
        ig.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f9f8f5")),
            ("GRID",          (0, 0), (-1, -1), 0.3, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        block.append(Spacer(1, 1.5 * mm))
        block.append(ig)

    # Recommendations
    if chg.recommendations:
        block.append(Spacer(1, 1.5 * mm))
        block.append(Paragraph("<b>Recommended Actions:</b>",
            ParagraphStyle("rh", fontSize=8, fontName="Helvetica-Bold",
                           textColor=C_AMBER, leftIndent=8)))
        for r in chg.recommendations:
            block.append(Paragraph(f"→ {_safe(r)}",
                ParagraphStyle("ri", fontSize=8, fontName="Helvetica",
                               textColor=C_BLACK, leftIndent=16, leading=12)))

    if annotations:
        block.append(Spacer(1, 1.5 * mm))
        block.append(Paragraph("<b>Comments:</b>",
            ParagraphStyle("ah", fontSize=8, fontName="Helvetica-Bold",
                           textColor=C_AMBER, leftIndent=8)))
        for ann in annotations:
            status = "resolved" if bool(_ann_get(ann, "resolved")) else "open"
            created = _ann_get(ann, "created_at")
            author = _ann_get(ann, "author") or "Reviewer"
            text = _ann_get(ann, "text") or ""
            block.append(Paragraph(
                f"• [{status}] {_safe(str(author))} ({_safe(str(created))}): {_safe(str(text))}",
                ParagraphStyle("ai", fontSize=8, fontName="Helvetica",
                               textColor=C_BLACK, leftIndent=16, leading=12),
            ))

    return block


def _text_box(label: str, text: str, color, width: float) -> Paragraph:
    return Paragraph(
        f'<font size="7" color="{color.hexval()}"><b>{_safe(label)}</b></font><br/>'
        f'<font size="8" fontName="Courier">{_safe(text)}</font>',
        ParagraphStyle("tb", fontSize=8, fontName="Helvetica",
                       textColor=C_BLACK, leading=11))


def _long_text_flowables(text: str, style: ParagraphStyle, chunk_size: int = 2400) -> List:
    text = text or ""
    if not text:
        return [Paragraph("(empty)", style)]
    flowables: List = []
    for start in range(0, len(text), chunk_size):
        flowables.append(Paragraph(_safe(text[start:start + chunk_size]).replace("\n", "<br/>"), style))
        flowables.append(Spacer(1, 1 * mm))
    return flowables


def _safe(value: str) -> str:
    return escape(str(value), quote=False)


def _ann_get(annotation: Any, key: str):
    if isinstance(annotation, dict):
        return annotation.get(key)
    return getattr(annotation, key, None)


def _group_annotations(annotations: Sequence[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {}
    for ann in annotations:
        change_id = _ann_get(ann, "change_id")
        if not change_id:
            continue
        grouped.setdefault(change_id, []).append(ann)
    return grouped


def _chunk_text(text: str, chunk_size: int) -> List[str]:
    """Split *text* into chunks so that no single table row becomes too
    tall to fit on a page."""
    if not text:
        return []
    chunks: List[str] = []
    for start in range(0, len(text), chunk_size):
        chunks.append(text[start:start + chunk_size])
    return chunks


def _side_by_side_box(
    left_label: str,
    left_text: str,
    left_color,
    right_label: str,
    right_text: str,
    right_color,
    full_width: float,
    chunk_size: int = 2400,
) -> Table:
    """Return a side-by-side comparison table that can split across pages.

    Text is broken into chunks so that no single row exceeds the available
    frame height, avoiding the ``too large on page`` reportlab error.
    """
    half = (full_width - 3 * mm) / 2
    gap = 3 * mm

    left_chunks = _chunk_text(left_text, chunk_size) or ["(not present)"]
    right_chunks = _chunk_text(right_text, chunk_size) or ["(not present)"]
    max_rows = max(len(left_chunks), len(right_chunks))

    rows = []
    # Header row
    rows.append([
        Paragraph(
            f'<font size="7" color="{left_color.hexval()}"><b>{_safe(left_label)}</b></font>',
            ParagraphStyle("sbl", fontSize=8, fontName="Helvetica",
                           textColor=C_BLACK, leading=11),
        ),
        "",
        Paragraph(
            f'<font size="7" color="{right_color.hexval()}"><b>{_safe(right_label)}</b></font>',
            ParagraphStyle("sbr", fontSize=8, fontName="Helvetica",
                           textColor=C_BLACK, leading=11),
        ),
    ])

    for i in range(max_rows):
        lchunk = left_chunks[i] if i < len(left_chunks) else ""
        rchunk = right_chunks[i] if i < len(right_chunks) else ""
        rows.append([
            Paragraph(
                f'<font size="8" fontName="Courier">{_safe(lchunk)}</font>',
                ParagraphStyle("sbc", fontSize=8, fontName="Helvetica",
                               textColor=C_BLACK, leading=11),
            ),
            "",
            Paragraph(
                f'<font size="8" fontName="Courier">{_safe(rchunk)}</font>',
                ParagraphStyle("sbc", fontSize=8, fontName="Helvetica",
                               textColor=C_BLACK, leading=11),
            ),
        ])

    tbl = Table(rows, colWidths=[half, gap, half], splitByRow=1)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f9f8f5")),
        ("BACKGROUND", (2, 1), (2, -1), colors.HexColor("#f9f8f5")),
        ("BOX", (0, 0), (0, -1), 0.5, left_color),
        ("BOX", (2, 0), (2, -1), 0.5, right_color),
        # Header padding
        ("TOPPADDING", (0, 0), (0, 0), 5),
        ("BOTTOMPADDING", (0, 0), (0, 0), 5),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("TOPPADDING", (2, 0), (2, 0), 5),
        ("BOTTOMPADDING", (2, 0), (2, 0), 5),
        ("LEFTPADDING", (2, 0), (2, 0), 6),
        ("RIGHTPADDING", (2, 0), (2, 0), 6),
        # Content padding
        ("TOPPADDING", (0, 1), (0, -1), 3),
        ("BOTTOMPADDING", (0, 1), (0, -1), 3),
        ("LEFTPADDING", (0, 1), (0, -1), 6),
        ("RIGHTPADDING", (0, 1), (0, -1), 6),
        ("TOPPADDING", (2, 1), (2, -1), 3),
        ("BOTTOMPADDING", (2, 1), (2, -1), 3),
        ("LEFTPADDING", (2, 1), (2, -1), 6),
        ("RIGHTPADDING", (2, 1), (2, -1), 6),
        # Gap column – zero padding
        ("LEFTPADDING", (1, 0), (1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("TOPPADDING", (1, 0), (1, -1), 0),
        ("BOTTOMPADDING", (1, 0), (1, -1), 0),
    ]))
    return tbl