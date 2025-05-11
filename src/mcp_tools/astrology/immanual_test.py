from immanuel import charts
import json

from immanuel.classes.serialize import ToJSON
from immanuel import charts
from kerykeion import AstrologicalSubject, KerykeionChartSVG
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM

from kerykeion import Report, AstrologicalSubject


native = charts.Subject(
        date_time='2000-01-01 10:00',
        latitude='32n43',
        longitude='117w09'
    )

natal = charts.Natal(native)

print(json.dumps(natal.objects, cls=ToJSON, indent=4))

from kerykeion import AstrologicalSubject, KerykeionChartSVG

john = AstrologicalSubject("John Lennon", 1940, 10, 9, 18, 30, "Liverpool", "GB")
birth_chart_svg = KerykeionChartSVG(john)
birth_chart_svg.makeSVG()