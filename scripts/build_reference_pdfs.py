"""Turn Europe PMC JATS XML into readable full-text PDFs.

These are reading copies generated from open-access full text, not publisher
PDF replacements. The source XML remains in references/fulltext/.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parent.parent
XML_DIR = ROOT / "references" / "fulltext"
PDF_DIR = ROOT / "references" / "pdf"
FILES = {
    "PMC9759637": "Zhang_2021_virtual_preoperative_assessment",
    "PMC4136425": "Sankar_2014_ASA_reliability",
    "PMC8098727": "Karim_2021_ASA_variation",
    "PMC11815294": "Roustan_2025_LLM_hallucination",
    "PMC12318031": "Omar_2025_adversarial_hallucination",
}


def clean(text: str) -> str:
    text = " ".join(text.split())
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00b1": "+/-",
        "\u03ba": "kappa",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def node_text(node) -> str:
    return clean("".join(node.itertext())) if node is not None else ""


def find_text(root, xpath: str) -> str:
    node = root.find(xpath)
    return node_text(node)


def add_paragraph(story, text, style):
    text = clean(text)
    if text:
        story.append(Paragraph(text, style))
        story.append(Spacer(1, 2.5 * mm))


def build_pdf(xml_path: Path, output_path: Path):
    root = ET.parse(xml_path).getroot()
    title = find_text(root, ".//article-meta/title-group/article-title")
    journal = find_text(root, ".//journal-meta/journal-title-group/journal-title")
    year = find_text(root, ".//article-meta/pub-date/year")
    volume = find_text(root, ".//article-meta/volume")
    issue = find_text(root, ".//article-meta/issue")
    fpage = find_text(root, ".//article-meta/fpage")
    lpage = find_text(root, ".//article-meta/lpage")
    doi = find_text(root, ".//article-meta/article-id[@pub-id-type='doi']")
    authors = []
    for contrib in root.findall(".//contrib-group/contrib"):
        surname = find_text(contrib, "./name/surname")
        given = find_text(contrib, "./name/given-names")
        if surname:
            authors.append(f"{surname} {given}".strip())

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ArticleTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        spaceAfter=8 * mm,
        textColor="#1F2937",
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor="#4B5563",
        spaceAfter=2 * mm,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=5 * mm,
        spaceAfter=2.5 * mm,
        textColor="#003366",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=2 * mm,
    )
    note_style = ParagraphStyle(
        "Note",
        parent=meta_style,
        fontSize=8.5,
        leading=11,
        textColor="#6B7280",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor("#6B7280")
        canvas.drawString(
            20 * mm,
            12 * mm,
            f"Europe PMC full-text reading copy | {xml_path.stem}",
        )
        canvas.drawRightString(
            A4[0] - 20 * mm,
            12 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=clean(title),
        author=", ".join(authors[:8]),
        subject="Europe PMC open-access full text reading copy",
    )
    story = []
    add_paragraph(story, title or xml_path.stem, title_style)
    add_paragraph(story, ", ".join(authors), meta_style)
    citation = " ".join(
        part for part in [
            journal,
            f"{year};{volume}" if year or volume else "",
            f"({issue})" if issue else "",
            f"{fpage}-{lpage}" if fpage else "",
        ] if part
    )
    add_paragraph(story, citation, meta_style)
    if doi:
        add_paragraph(story, f"DOI: {doi}", meta_style)
    add_paragraph(
        story,
        "Reading copy generated from the Europe PMC open-access full-text XML. "
        "This is not a publisher's original PDF layout.",
        note_style,
    )

    abstract_nodes = root.findall(".//article-meta/abstract")
    if abstract_nodes:
        if abstract_nodes[0].find("./title") is None:
            story.append(Paragraph("Abstract", heading_style))
        for abstract in abstract_nodes:
            for child in abstract:
                if child.tag.endswith("title"):
                    add_paragraph(story, node_text(child), heading_style)
                elif child.tag.endswith("p"):
                    add_paragraph(story, node_text(child), body_style)
                else:
                    add_paragraph(story, node_text(child), body_style)

    body = root.find(".//body")
    if body is not None:
        def walk(element, include_title=False):
            if include_title:
                title_node = element.find("./title")
                if title_node is not None:
                    add_paragraph(story, node_text(title_node), heading_style)
            for child in element:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "title":
                    continue
                if tag == "p":
                    add_paragraph(story, node_text(child), body_style)
                elif tag == "sec":
                    walk(child, include_title=True)
                elif tag == "table-wrap":
                    caption = child.find("./caption")
                    if caption is not None:
                        add_paragraph(
                            story,
                            f"Table: {node_text(caption)}",
                            note_style,
                        )

        walk(body)

    if len(story) < 5:
        for paragraph in root.findall(".//p"):
            add_paragraph(story, node_text(paragraph), body_style)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output_path.name, output_path.stat().st_size)


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for pmc, stem in FILES.items():
        xml_path = XML_DIR / f"{pmc}.xml"
        if not xml_path.exists():
            raise FileNotFoundError(xml_path)
        build_pdf(xml_path, PDF_DIR / f"{pmc}_{stem}.pdf")


if __name__ == "__main__":
    main()
