from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from io import BytesIO
from app.models.chart import ChartResponse

class PDFReportService:
    def generate_report(self, chart: ChartResponse, interpretation: str) -> BytesIO:
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Page 1: Header and Metadata
        p.setFont("Helvetica-Bold", 16)
        p.drawString(2 * cm, height - 3 * cm, "Usturlap Astrological Report")
        
        p.setFont("Helvetica", 12)
        p.drawString(2 * cm, height - 4 * cm, f"Date: {chart.meta.datetime.strftime('%Y-%m-%d %H:%M')}")
        p.drawString(2 * cm, height - 4.5 * cm, f"Location: Lat {chart.meta.location.lat}, Lon {chart.meta.location.lon}")
        
        # Draw a simple circle for the chart placeholder (could be expanded with SVG-to-Canvas path)
        p.setStrokeColor(colors.black)
        p.circle(width/2, height/2, 5 * cm, stroke=1, fill=0)
        p.drawString(width/2 - 2*cm, height/2, "[Chart Wheel Visual]")

        # Page 2: Planetary Positions
        p.showPage()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(2 * cm, height - 2 * cm, "Planetary Positions")
        
        p.setFont("Helvetica", 10)
        y = height - 3 * cm
        for pl in chart.planets:
            p.drawString(2 * cm, y, f"{pl.name}: {pl.degree:.2f} {pl.sign} (House {pl.house})")
            y -= 0.5 * cm
            if y < 2 * cm:
                p.showPage()
                y = height - 2 * cm

        # Page 3: Interpretation
        p.showPage()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(2 * cm, height - 2 * cm, "Professional Interpretation")
        
        p.setFont("Helvetica", 10)
        text_object = p.beginText(2 * cm, height - 3 * cm)
        for line in interpretation.split('\n'):
            text_object.textLine(line)
        p.drawText(text_object)

        p.save()
        buffer.seek(0)
        return buffer
