# -*- coding: utf-8 -*-
"""Láminas visuales: Khipu y Fintoc. No es asesoría legal ni financiera."""

from reportlab.lib.colors import Color, white, black
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))

OUT = r"C:\Users\jesus\Downloads\Informe_Khipu_y_Fintoc.pdf"
W, H = A4

NAVY = Color(0.07, 0.16, 0.29)
TEAL = Color(0.05, 0.55, 0.52)
TEAL_SOFT = Color(0.86, 0.95, 0.94)
ORANGE = Color(0.93, 0.55, 0.12)
ORANGE_SOFT = Color(1, 0.95, 0.86)
KLAP = Color(0.38, 0.24, 0.72)
KLAP_SOFT = Color(0.94, 0.91, 0.98)
INK = Color(0.12, 0.16, 0.22)
MUTED = Color(0.38, 0.44, 0.52)
LINE = Color(0.86, 0.89, 0.92)
BG = Color(0.96, 0.97, 0.98)
CARD = white
GREEN = Color(0.18, 0.62, 0.45)
RED = Color(0.82, 0.33, 0.28)
RED_SOFT = Color(0.99, 0.93, 0.92)
GOLD = Color(0.95, 0.78, 0.25)
ACCENT = Color(0.525, 0.737, 0.145)


def clp(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def wrap(text, font, size, max_w):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if pdfmetrics.stringWidth(trial, font, size) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text(c, s, x, y, font="Arial", size=11, color=INK, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center":
        c.drawCentredString(x, y, s)
    elif align == "right":
        c.drawRightString(x, y, s)
    else:
        c.drawString(x, y, s)


def paragraph(c, s, x, y, max_w, font="Arial", size=11, leading=14, color=INK, align="left"):
    lines = wrap(s, font, size, max_w)
    c.setFillColor(color)
    c.setFont(font, size)
    for i, line in enumerate(lines):
        yy = y - i * leading
        if align == "center":
            c.drawCentredString(x, yy, line)
        else:
            c.drawString(x, yy, line)
    return len(lines) * leading


def card(c, x, y, w, h, fill=CARD, radius=14, stroke=None):
    c.setFillColor(Color(0.85, 0.88, 0.92))
    c.roundRect(x + 2, y - 2, w, h, radius, fill=1, stroke=0)
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(1.4)
        c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
    else:
        c.roundRect(x, y, w, h, radius, fill=1, stroke=0)


def circle_icon(c, x, y, r, fill, kind):
    c.setFillColor(fill)
    c.circle(x, y, r, fill=1, stroke=0)
    c.setStrokeColor(white)
    c.setFillColor(white)
    c.setLineWidth(1.8)
    c.setLineCap(1)
    c.setLineJoin(1)
    if kind == "shop":
        c.rect(x - 7, y - 8, 14, 10, fill=0, stroke=1)
        c.line(x - 9, y + 2, x + 9, y + 2)
        c.line(x - 5, y + 2, x - 3, y + 8)
        c.line(x + 5, y + 2, x + 3, y + 8)
        c.line(x - 3, y + 8, x + 3, y + 8)
    elif kind == "bank":
        c.line(x - 8, y - 7, x + 8, y - 7)
        c.line(x - 6, y - 7, x - 6, y + 1)
        c.line(x, y - 7, x, y + 1)
        c.line(x + 6, y - 7, x + 6, y + 1)
        c.line(x - 9, y + 1, x + 9, y + 1)
        p = c.beginPath()
        p.moveTo(x - 8, y + 1)
        p.lineTo(x, y + 9)
        p.lineTo(x + 8, y + 1)
        c.drawPath(p, fill=0, stroke=1)
    elif kind == "phone":
        c.roundRect(x - 5, y - 9, 10, 18, 2, fill=0, stroke=1)
        c.circle(x, y - 6, 1.1, fill=1, stroke=0)
    elif kind == "coin":
        c.circle(x, y, 7, fill=0, stroke=1)
        c.setFont("Arial-Bold", 9)
        c.drawCentredString(x, y - 3, "$")
    elif kind == "key":
        c.circle(x - 3, y + 2, 4, fill=0, stroke=1)
        c.line(x, y, x + 8, y - 6)
        c.line(x + 5, y - 3, x + 8, y - 1)
    elif kind == "doc":
        c.rect(x - 6, y - 8, 12, 16, fill=0, stroke=1)
        c.line(x - 3, y + 3, x + 3, y + 3)
        c.line(x - 3, y, x + 3, y)
        c.line(x - 3, y - 3, x + 1, y - 3)
    elif kind == "check":
        c.setLineWidth(2.2)
        c.line(x - 6, y, x - 2, y - 5)
        c.line(x - 2, y - 5, x + 7, y + 6)
    elif kind == "alert":
        p = c.beginPath()
        p.moveTo(x, y + 8)
        p.lineTo(x - 8, y - 7)
        p.lineTo(x + 8, y - 7)
        p.close()
        c.drawPath(p, fill=0, stroke=1)
        c.setFont("Arial-Bold", 10)
        c.drawCentredString(x, y - 4, "!")
    elif kind == "people":
        c.circle(x - 3, y + 3, 3.2, fill=0, stroke=1)
        c.circle(x + 4, y + 4, 2.6, fill=0, stroke=1)
        c.roundRect(x - 8, y - 8, 9, 7, 3, fill=0, stroke=1)
    elif kind == "clock":
        c.circle(x, y, 7, fill=0, stroke=1)
        c.line(x, y, x, y + 4)
        c.line(x, y, x + 3, y - 2)
    elif kind == "box":
        c.rect(x - 7, y - 6, 14, 12, fill=0, stroke=1)
        c.line(x - 7, y + 6, x, y + 9)
        c.line(x, y + 9, x + 7, y + 6)
    elif kind == "law":
        c.line(x, y - 8, x, y + 6)
        c.line(x - 7, y + 4, x + 7, y + 4)
        c.line(x - 7, y + 4, x - 7, y)
        c.line(x + 7, y + 4, x + 7, y)
        c.circle(x - 7, y - 2, 2.2, fill=0, stroke=1)
        c.circle(x + 7, y - 2, 2.2, fill=0, stroke=1)
    elif kind == "split":
        c.roundRect(x - 8, y - 6, 7, 12, 1, fill=0, stroke=1)
        c.roundRect(x + 1, y - 6, 7, 12, 1, fill=0, stroke=1)
    elif kind == "card":
        c.roundRect(x - 8, y - 5, 16, 11, 2, fill=0, stroke=1)
        c.line(x - 8, y + 2, x + 8, y + 2)
        c.line(x - 4, y - 2, x + 2, y - 2)


def footer(c, n, total=18):
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 28, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, 28, W, 3, fill=1, stroke=0)
    text(c, "Datos públicos al 12 oct 2026  ·  No es consejo de abogado ni promesa de ganancia", 24, 11, size=8, color=white)
    text(c, f"{n} / {total}", W - 24, 11, size=8, color=white, align="right")


def page_cover(c):
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(0, H - 8, W, 8, fill=1, stroke=0)
    text(c, "INFORME", 48, 720, "Arial", 11, MUTED)
    text(c, "Khipu, Fintoc", 48, 660, "Arial-Bold", 40, black)
    text(c, "y Klap", 48, 612, "Arial-Bold", 40, black)
    c.setStrokeColor(black)
    c.setLineWidth(0.7)
    c.line(48, 590, 168, 590)
    paragraph(
        c,
        "Tres formas de cobrar: transferencia o tarjeta. Cuánto se queda cada uno, y cómo armar una empresa parecida.",
        48, 560, 400, "Arial", 13, 18, INK,
    )
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.line(48, 64, W - 48, 64)
    text(c, "12 de octubre de 2026", 48, 42, "Arial", 11, INK)
    text(c, "Pagos en Chile", W - 48, 42, "Arial", 11, MUTED, "right")


def page_simple(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "En simple", 36, 790, "Arial-Bold", 26, NAVY)
    paragraph(c, "Dos cobran con transferencia. Klap cobra con tarjeta.", 36, 764, 500, size=13, leading=16, color=MUTED)

    trio = [
        (28, TEAL_SOFT, TEAL, "bank", "Khipu", "Desde 2011", [
            "El cliente paga desde su banco.",
            "Avisa a la tienda.",
            "La plata llega al día siguiente.",
        ]),
        (210, ORANGE_SOFT, ORANGE, "phone", "Fintoc", "Desde 2020", [
            "También usa transferencia.",
            "Puede leer la cuenta.",
            "Chile y México.",
        ]),
        (392, KLAP_SOFT, KLAP, "card", "Klap", "Tarjeta", [
            "Máquina, celular o link.",
            "Débito, crédito y prepago.",
            "Abono en 1 día hábil.",
        ]),
    ]
    for x, bg, col, icon, name, sub, lines in trio:
        card(c, x, 500, 172, 230, bg)
        circle_icon(c, x + 28, 690, 16, col, icon)
        text(c, name, x + 52, 684, "Arial-Bold", 14, NAVY)
        text(c, sub, x + 16, 652, "Arial", 10, MUTED)
        for i, line in enumerate(lines):
            text(c, "•  " + line, x + 14, 620 - i * 28, "Arial", 9, INK)

    card(c, 28, 48, 540, 430)
    text(c, "Camino Khipu y Fintoc  ·  transferencia", 48, 440, "Arial-Bold", 14, NAVY)
    steps = [
        ("1", "Toca", "Pagar", TEAL),
        ("2", "Elige", "su banco", ORANGE),
        ("3", "Clave", "en el banco", NAVY),
        ("4", "Viaja", "la plata", GREEN),
        ("5", "Aviso", "a la tienda", RED),
    ]
    for i, (n, a, b, col) in enumerate(steps):
        x = 52 + i * 104
        c.setFillColor(col)
        c.circle(x + 28, 360, 24, fill=1, stroke=0)
        text(c, n, x + 28, 354, "Arial-Bold", 15, white, "center")
        text(c, a, x + 28, 316, "Arial-Bold", 11, NAVY, "center")
        text(c, b, x + 28, 300, "Arial", 10, MUTED, "center")
        if i < 4:
            c.setStrokeColor(LINE)
            c.setLineWidth(3)
            c.line(x + 56, 360, x + 76, 360)
    text(c, "Camino Klap  ·  tarjeta", 48, 250, "Arial-Bold", 14, KLAP)
    klap_steps = [("1", "Acerca", "la tarjeta"), ("2", "Pone", "el PIN"), ("3", "Listo", "aprobado")]
    for i, (n, a, b) in enumerate(klap_steps):
        x = 70 + i * 160
        c.setFillColor(KLAP)
        c.circle(x, 200, 20, fill=1, stroke=0)
        text(c, n, x, 194, "Arial-Bold", 13, white, "center")
        text(c, a, x, 160, "Arial-Bold", 11, NAVY, "center")
        text(c, b, x, 146, "Arial", 10, MUTED, "center")
        if i < 2:
            c.setStrokeColor(LINE)
            c.setLineWidth(3)
            c.line(x + 28, 200, x + 112, 200)
    card(c, 48, 68, 500, 58, Color(1, 0.97, 0.90), radius=10)
    paragraph(c, "En transferencia, la tienda espera el aviso antes de entregar. La clave se pone en el banco. En Klap, el cliente acerca la tarjeta y digita el PIN.", 64, 108, 470, size=10, leading=13)
    footer(c, 2)


def page_compare(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "En qué se parecen y en qué no", 36, 790, "Arial-Bold", 24, NAVY)

    rows = [
        ("Qué es", "Transferencia", "Transferencia y cuentas", "Tarjeta"),
        ("Precio citado", "0,69% + IVA", "Desde 1%. Shopify 1,35%", "Máquina débito: fijo + 0,62%"),
        ("Otra tarifa", "UF 0,0105 por pago", "A veces un fijo en UF", "Link 2,89%. Tap 2,29%"),
        ("Cuándo llega", "Día hábil siguiente", "Cerca de 1 día hábil", "1 día hábil"),
        ("Quién paga", "La tienda", "La tienda", "La tienda"),
        ("Permiso", "Mandato de cobro", "Contrato y CMF", "Adquirente. Itaú acordó comprar"),
    ]
    y = 730
    c.setFillColor(NAVY)
    c.roundRect(28, y, 540, 34, 8, fill=1, stroke=0)
    text(c, "Tema", 40, y + 11, "Arial-Bold", 10, white)
    text(c, "Khipu", 150, y + 11, "Arial-Bold", 10, white)
    text(c, "Fintoc", 300, y + 11, "Arial-Bold", 10, white)
    text(c, "Klap", 450, y + 11, "Arial-Bold", 10, white)
    for i, (tema, k, f, kl) in enumerate(rows):
        y -= 92
        bg = white if i % 2 == 0 else Color(0.93, 0.96, 0.97)
        c.setFillColor(bg)
        c.roundRect(28, y, 540, 82, 10, fill=1, stroke=0)
        text(c, tema, 40, y + 34, "Arial-Bold", 10, NAVY)
        paragraph(c, k, 145, y + 48, 140, size=10, leading=13)
        paragraph(c, f, 295, y + 48, 140, size=10, leading=13)
        paragraph(c, kl, 445, y + 48, 110, size=10, leading=13)
    footer(c, 3)


def page_fees(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Cuánto cobran", 36, 790, "Arial-Bold", 26, NAVY)
    paragraph(c, "El porcentaje es de la venta. Encima va el IVA de 19%. Lo paga la tienda.", 36, 762, 500, size=12, leading=16, color=MUTED)

    tiles = [
        (24, "0,69%", "Khipu", "transferencia", TEAL),
        (164, "1% a 1,35%", "Fintoc", "según el plan", ORANGE),
        (304, "0,62% + fijo", "Klap máquina", "débito. El fijo de hoy es ~$78", KLAP),
        (444, "2,89%", "Klap link", "débito, crédito y prepago", NAVY),
    ]
    for x, big, name, sub, col in tiles:
        card(c, x, 575, 128, 155)
        c.setFillColor(col)
        c.rect(x, 704, 128, 8, fill=1, stroke=0)
        text(c, big, x + 64, 668, "Arial-Bold", 12, col, "center")
        text(c, name, x + 64, 646, "Arial-Bold", 10, NAVY, "center")
        paragraph(c, sub, x + 64, 626, 108, size=8, leading=11, color=MUTED, align="center")

    text(c, "Venta de $100.000, con IVA", 36, 540, "Arial-Bold", 15, NAVY)

    bars = [
        ("Khipu 0,69%", 821, TEAL),
        ("Klap máquina débito", 831, KLAP),
        ("Fintoc 1,35%", 1607, ORANGE),
        ("Klap Tap 2,29%", 2725, Color(0.55, 0.40, 0.82)),
        ("Klap link 2,89%", 3439, NAVY),
    ]
    max_v = 3439
    y = 490
    for name, val, col in bars:
        text(c, name, 36, y, "Arial", 10, INK)
        text(c, clp(val), 548, y, "Arial-Bold", 10, NAVY, "right")
        c.setFillColor(LINE)
        c.roundRect(36, y - 16, 500, 12, 6, fill=1, stroke=0)
        c.setFillColor(col)
        c.roundRect(36, y - 16, max(16, 500 * val / max_v), 12, 6, fill=1, stroke=0)
        y -= 46

    card(c, 28, 48, 540, 88, KLAP_SOFT, radius=12)
    text(c, "Dato fácil", 48, 110, "Arial-Bold", 12, KLAP)
    paragraph(
        c,
        "En $100.000, la máquina de débito de Klap (~$831) queda casi igual que Khipu ($821). El link de Klap sale cerca de $3.439. El fijo de la máquina es 0,0019 UF: hoy unos $78. En marzo Klap lo mostraba como $76.",
        48, 92, 500, size=10, leading=13,
    )
    footer(c, 4)


def page_money(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "De dónde sale la ganancia", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "No se quedan con los $100.000. Se quedan con la comisión.", 36, 758, 500, size=13, leading=16, color=MUTED)

    # big bill
    card(c, 36, 520, 524, 200, NAVY, radius=16)
    text(c, "VENTA", 60, 680, "Arial-Bold", 11, GOLD)
    text(c, "$100.000", 60, 640, "Arial-Bold", 36, white)
    text(c, "van a la tienda", 60, 610, "Arial", 13, Color(0.8, 0.86, 0.92))
    c.setFillColor(TEAL)
    c.roundRect(330, 575, 200, 110, 12, fill=1, stroke=0)
    text(c, "COMISIÓN", 430, 655, "Arial-Bold", 11, white, "center")
    text(c, "$821", 430, 615, "Arial-Bold", 28, white, "center")
    text(c, "ejemplo Khipu + IVA", 430, 592, "Arial", 10, Color(0.85, 0.95, 0.94), "center")

    boxes = [
        (36, "Poco volumen", "Hay comisión,\npero no alcanza\npara los sueldos.", RED, RED_SOFT),
        (220, "Volumen medio", "Se pagan las\ncuentas. Todavía\nno sobra mucho.", ORANGE, ORANGE_SOFT),
        (404, "Mucho volumen", "Cada pago extra\ndeja ganancia.\nAhí está el negocio.", GREEN, Color(0.90, 0.97, 0.93)),
    ]
    for x, title, body, col, bg in boxes:
        card(c, x, 300, 156, 190, bg)
        c.setFillColor(col)
        c.circle(x + 28, 455, 8, fill=1, stroke=0)
        text(c, title, x + 16, 420, "Arial-Bold", 12, NAVY)
        for i, line in enumerate(body.split("\n")):
            text(c, line, x + 16, 390 - i * 18, "Arial", 11, INK)

    card(c, 36, 58, 524, 210)
    text(c, "Cuenta de servilleta", 56, 230, "Arial-Bold", 14, NAVY)
    items = [
        ("$5.000.000", "dos sueldos: $3 y $2 millones"),
        ("$6,3 millones al mes", "con servidor e ISO del primer año"),
        ("Unos $703 millones", "de ventas al mes para empatar"),
    ]
    for i, (a, b) in enumerate(items):
        y = 190 - i * 42
        circle_icon(c, 78, y + 8, 14, TEAL, "coin")
        text(c, a, 108, y + 12, "Arial-Bold", 13, NAVY)
        text(c, b, 108, y - 6, "Arial", 11, MUTED)
    footer(c, 5)


def page_napkin(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "La cuenta, número por número", 36, 790, "Arial-Bold", 22, NAVY)
    paragraph(c, "Ejemplo para ver cuándo se empata. No es la ganancia real de Khipu ni de Fintoc.", 36, 764, 520, size=12, leading=15, color=MUTED)

    card(c, 36, 590, 524, 145)
    text(c, "1. De una venta de $100.000", 56, 700, "Arial-Bold", 14, NAVY)
    text(c, "$100.000  ×  0,90%  =  $900", 56, 668, "Arial-Bold", 18, TEAL)
    paragraph(c, "Esos $900 son tuyos. Los otros $99.100 son de la tienda. El 0,90% es un precio de ejemplo, no el de ellos.", 56, 640, 480, size=12, leading=16)

    card(c, 36, 400, 524, 170)
    text(c, "2. Gasto de este equipo", 56, 534, "Arial-Bold", 14, NAVY)
    paragraph(c, "Programador $3.000.000 + programador $2.000.000 = $5.000.000. Servidor, base y respaldos: $500.000, ejemplo. ISO 27001, piso publicado de $10 millones el primer año, partido en 12: $830.000.", 56, 508, 480, size=11, leading=15)
    text(c, "Total  $6.330.000 al mes", 56, 448, "Arial-Bold", 14, TEAL)
    paragraph(c, "$6.330.000 ÷ $900 = 7.034 ventas. Eso es unos $703 millones movidos, solo para empatar.", 56, 424, 480, size=12, leading=15)

    card(c, 36, 268, 250, 115)
    text(c, "Los dos sueldos", 52, 350, "Arial-Bold", 12, NAVY)
    paragraph(c, "$3.000.000 y $2.000.000. Son sueldo. Las imposiciones del empleador van aparte.", 52, 326, 214, size=11, leading=14)

    card(c, 310, 268, 250, 115)
    text(c, "ISO e infraestructura", 326, 350, "Arial-Bold", 12, NAVY)
    paragraph(c, "Una pyme de 10 a 30 personas publica $17 a $29 millones el año 1. Aquí uso el piso de $10 millones.", 326, 326, 214, size=11, leading=14)

    card(c, 36, 48, 524, 200, ORANGE_SOFT)
    text(c, "Si revendes, no te quedas el 0,90%", 56, 214, "Arial-Bold", 14, NAVY)
    paragraph(
        c,
        "Te quedas $786 por cada $100.000: cobras $1.607 y Khipu te cobra $821. El gasto sigue en $6.330.000.",
        56, 188, 480, size=12, leading=16,
    )
    text(c, "$6.330.000  ÷  $786  ≈  8.050 ventas", 56, 140, "Arial-Bold", 13, ORANGE)
    paragraph(c, "Unos $805 millones al mes para empatar, porque de cada venta te queda menos.", 56, 114, 480, size=12, leading=16)
    footer(c, 6)


def page_gains(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Ganancia al mes", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "Cada venta deja $900. El gasto es $6,3 millones: dos sueldos, servidor e ISO.", 36, 764, 520, size=12, leading=15, color=MUTED)

    c.setFillColor(NAVY)
    c.roundRect(36, 708, 524, 28, 6, fill=1, stroke=0)
    text(c, "Ventas", 52, 717, "Arial-Bold", 10, white)
    text(c, "Plata movida", 175, 717, "Arial-Bold", 10, white)
    text(c, "Comisión", 330, 717, "Arial-Bold", 10, white)
    text(c, "Después del gasto", 548, 717, "Arial-Bold", 10, white, "right")

    rows = [
        ("1.000", "$100 millones", "$900 mil", "− $5,4 millones", RED),
        ("3.000", "$300 millones", "$2,7 millones", "− $3,6 millones", RED),
        ("5.000", "$500 millones", "$4,5 millones", "− $1,8 millones", ORANGE),
        ("7.034", "$703 millones", "$6,3 millones", "$0  empatas", NAVY),
        ("10.000", "$1.000 millones", "$9 millones", "+ $2,7 millones", GREEN),
        ("20.000", "$2.000 millones", "$18 millones", "+ $11,7 millones", GREEN),
    ]
    y = 640
    for i, (ventas, movido, comision, queda, col) in enumerate(rows):
        bg = white if i % 2 == 0 else Color(0.94, 0.96, 0.98)
        c.setFillColor(bg)
        c.rect(36, y, 524, 52, fill=1, stroke=0)
        c.setFillColor(col)
        c.rect(36, y, 6, 52, fill=1, stroke=0)
        text(c, ventas, 52, y + 20, "Arial-Bold", 12, NAVY)
        text(c, movido, 175, y + 20, "Arial", 12, INK)
        text(c, comision, 330, y + 20, "Arial", 12, INK)
        text(c, queda, 548, y + 20, "Arial-Bold", 11, col, "right")
        y -= 52

    card(c, 36, 48, 524, 200, ORANGE_SOFT)
    text(c, "Si revendes y te quedan $786 por venta", 56, 214, "Arial-Bold", 13, NAVY)
    paragraph(c, "Mismo gasto de $6.330.000. La comisión ya es solo la diferencia: cobras $1.607 y Khipu te cobra $821.", 56, 190, 480, size=11, leading=14)
    text(c, "5.000 ventas   comisión $3,9 millones   pierdes $2,4 millones", 56, 148, "Arial", 11, INK)
    text(c, "8.050 ventas   comisión $6,3 millones   empatas", 56, 126, "Arial", 11, INK)
    text(c, "20.000 ventas   comisión $15,7 millones   ganas $9,4 millones", 56, 104, "Arial-Bold", 11, GREEN)
    footer(c, 7)


def page_law(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "La ley, en fichas", 36, 790, "Arial-Bold", 26, NAVY)
    paragraph(c, "Chile pide permiso para mover pagos de otras personas. Esto es un mapa, no un dictamen.", 36, 762, 510, size=12, leading=16, color=MUTED)

    tiles = [
        ("law", "Pedir registro", "La CMF inscribe a quien inicia pagos. La ley es la 21.521.", TEAL),
        ("key", "Sin guardar claves", "El cliente entra a su banco. La empresa no se queda con la clave.", ORANGE),
        ("split", "Dos cajas", "La plata de la tienda no se mezcla con la de la empresa.", NAVY),
        ("doc", "Factura chica", "Se factura la comisión, no los $100.000 de la venta.", GREEN),
        ("clock", "Poca custodia", "Si guardan plata ajena, el tope público es de unas 72 horas.", RED),
        ("people", "El reclamo", "Si el producto no llega, el cliente reclama a la tienda.", Color(0.35, 0.40, 0.70)),
    ]
    for i, (kind, title, body, col) in enumerate(tiles):
        col_i = i % 2
        row = i // 2
        x = 36 + col_i * 270
        y = 560 - row * 160
        card(c, x, y, 254, 145)
        circle_icon(c, x + 36, y + 100, 20, col, kind)
        text(c, title, x + 68, y + 92, "Arial-Bold", 14, NAVY)
        paragraph(c, body, x + 20, y + 58, 214, size=11, leading=15)
    footer(c, 8)


def page_steps(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Cómo crear una empresa así", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "El atajo cobra ya. El camino largo es ser tú quien habla con cada banco.", 36, 762, 520, size=12, leading=15, color=MUTED)

    steps = [
        ("1", "Elige el camino", "Atajo: revender Khipu o Fintoc. Ellos ya tienen los bancos. Camino largo: convenio propio y registro en la CMF."),
        ("2", "Crea la SpA", "Por Empresa en un Día, con ClaveÚnica, el trámite es $0. Quedas con RUT y domicilio en Chile."),
        ("3", "SII y dos cajas", "El inicio de actividades es $0. Una cuenta para tus gastos. Si guardas plata de tiendas, otra cuenta, aparte."),
        ("4", "Contrato con quien ya cobra", "Le cobras a la tienda un poco más de lo que te cobra Khipu o Fintoc. Esa diferencia es tu ganancia."),
        ("5", "El camino de la ley", "Cuando la CMF habilite la conexión, el cliente autoriza en su banco. Tú ordenas el pago por ese sistema."),
        ("6", "Si mueves plata de otras tiendas", "Ahí entra la CMF, aunque el banco te firme un convenio. No guardes la clave del cliente. El tope de custodia es 72 horas."),
    ]
    for i, (n, title, body) in enumerate(steps):
        y = 690 - i * 105
        card(c, 36, y - 88, 524, 96)
        c.setFillColor(TEAL if i < 4 else ORANGE)
        c.circle(64, y - 40, 16, fill=1, stroke=0)
        text(c, n, 64, y - 46, "Arial-Bold", 14, white, "center")
        text(c, title, 96, y - 28, "Arial-Bold", 13, NAVY)
        paragraph(c, body, 96, y - 50, 440, size=11, leading=14)
    footer(c, 9)


def page_costs(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Cuánto cuesta partir", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "El trámite de la empresa es barato. La garantía y el equipo son el gasto grande.", 36, 762, 520, size=12, leading=15, color=MUTED)

    rows = [
        ("Crear la SpA", "$0", "Empresa en un Día, con ClaveÚnica. ChileAtiende."),
        ("Inicio de actividades", "$0", "Se hace en el SII. Sin eso el banco no abre la cuenta."),
        ("Derechos de la CMF", "17 UF", "Unos $694.000 en la lista de agosto 2026, ítem otros registros. Confirmar el ítem al tramitar."),
        ("Garantía, 6 meses", "UF 1.000", "Unos $41 millones. Es boleta o póliza, no un pago a la CMF."),
        ("Después de 6 meses", "sube", "UF 1.000 más 0,07% del monto diario promedio. Se renueva cada 3 meses."),
        ("Abogado o asesor", "a cotizar", "Finlaw y NextSteps no publican tarifa."),
    ]
    y = 710
    for i, (name, amount, note) in enumerate(rows):
        y -= 88
        card(c, 36, y, 524, 78)
        c.setFillColor(TEAL if i < 2 else (ORANGE if i < 5 else KLAP))
        c.rect(36, y, 8, 78, fill=1, stroke=0)
        text(c, name, 60, y + 48, "Arial-Bold", 13, NAVY)
        text(c, amount, W - 52, y + 48, "Arial-Bold", 13, NAVY, "right")
        paragraph(c, note, 60, y + 26, 480, size=11, leading=14, color=MUTED)
    footer(c, 10)


def page_now(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Cobrar ya, sin esperar", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "No hace falta esperar el sistema nuevo de la ley. Khipu y Fintoc ya tienen los convenios.", 36, 762, 520, size=12, leading=15, color=MUTED)

    paths = [
        (TEAL, "1  ·  Revender Khipu", "Ellos hablan con los bancos. Tú sumas tiendas y te quedas un margen. En su panel eso se llama Business Partner. Escribes a soporte@khipu.com. Oficina: Las Urbinas 53, Providencia."),
        (ORANGE, "2  ·  Fintoc", "Mismo atajo: tú cobras más de lo que te cobran a ti. El contacto público es fintoc.com/cl. Pide contrato comercial, no una clave de banco."),
    ]
    for i, (col, title, body) in enumerate(paths):
        y = 560 - i * 155
        card(c, 36, y, 524, 142)
        c.setFillColor(col)
        c.rect(36, y, 8, 142, fill=1, stroke=0)
        text(c, title, 60, y + 108, "Arial-Bold", 14, NAVY)
        paragraph(c, body, 60, y + 84, 470, size=12, leading=16)

    card(c, 36, 48, 524, 78, RED_SOFT)
    text(c, "Un convenio no apaga la ley", 56, 90, "Arial-Bold", 13, RED)
    paragraph(c, "Si la plata es de otras tiendas, la CMF igual pide registro. El atajo legal de hoy es revender a quien ya está conectado.", 56, 68, 480, size=11, leading=14)
    footer(c, 11)


def page_help(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Con quién hablar", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "Para cobrar ya, habla con Khipu o con Fintoc. Para el permiso, con un asesor.", 36, 762, 520, size=12, leading=15, color=MUTED)

    people = [
        (TEAL, "Khipu", "soporte@khipu.com", "Pide el modo Business Partner. Ahí ves el margen de las tiendas que sumes."),
        (ORANGE, "Fintoc", "fintoc.com/cl", "Pide el contrato comercial. Ellos ponen la conexión con los bancos."),
        (NAVY, "Cuenta de la empresa", "En el banco, a tu nombre", "Es la cuenta de los gastos de la empresa. El cobro al cliente va por Khipu, Fintoc o por el sistema de la CMF."),
        (KLAP, "Finlaw", "finlaw.cl", "Abogados de fintech. Te dicen si debes inscribirte en la CMF, la UAF o el Banco Central. No publican precio."),
        (GREEN, "NextSteps", "nextsteps.cl", "Asesoran medios de pago, adquirencia y la Ley 21.521. Tampoco publican tarifa: se cotiza."),
    ]
    y = 710
    for col, title, where, body in people:
        y -= 120
        card(c, 36, y, 524, 108)
        c.setFillColor(col)
        c.circle(68, y + 54, 16, fill=1, stroke=0)
        text(c, title, 100, y + 68, "Arial-Bold", 14, NAVY)
        text(c, where, 100, y + 48, "Arial", 11, MUTED)
        paragraph(c, body, 100, y + 26, 420, size=11, leading=14)
    footer(c, 12)


def page_enable(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Lo que van a habilitar", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "La CMF abre un sistema común. El cliente autoriza en su banco. Tú no firmas un convenio con cada uno.", 36, 762, 520, size=12, leading=15, color=MUTED)

    marks = [
        ("1", "Octubre 2026", "Ambiente de pruebas y directorio de participantes. La norma pide tenerlos listos 9 meses antes de partir."),
        ("2", "Antes de julio 2027", "Formulario para entrar solo a probar. Sirve para ensayar. No deja cobrar plata de verdad."),
        ("3", "3 de julio de 2027", "Parte el sistema. Ahí se pide el registro de iniciador de pagos, con derechos y garantía."),
        ("4", "Cerca de julio 2028", "Los bancos deben tener la conexión para iniciar un pago único de una persona. Son 12 meses desde el inicio."),
        ("5", "Hasta 18 meses después", "Pagos que se repiten, y pagos de empresas. Esos bancos los habilitan más tarde."),
    ]
    for i, (n, title, body) in enumerate(marks):
        y = 680 - i * 120
        card(c, 36, y - 100, 524, 108)
        c.setFillColor(TEAL if i < 3 else ORANGE)
        c.circle(64, y - 46, 16, fill=1, stroke=0)
        text(c, n, 64, y - 52, "Arial-Bold", 14, white, "center")
        text(c, title, 96, y - 28, "Arial-Bold", 14, NAVY)
        paragraph(c, body, 96, y - 52, 430, size=12, leading=16)
    footer(c, 13)


def page_law_steps(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Paso a paso con la ley", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "Así se arma la empresa nueva usando el sistema que habilita la CMF. Ley 21.521.", 36, 762, 520, size=12, leading=15, color=MUTED)

    steps = [
        ("1", "Crea la empresa ahora", "SpA chilena, con RUT y domicilio en Chile. Empresa en un Día sale $0."),
        ("2", "Arma la carpeta", "Plan de negocio, organigrama, texto del permiso del cliente, política de datos y certificado de que no estás en quiebra."),
        ("3", "Entra al ambiente de pruebas", "Cuando abran el formulario, ensayas con datos de prueba. Un tercero escribe el informe de esas pruebas."),
        ("4", "Certificado de seguridad", "Otro tercero certifica que tu conexión cumple el estándar. Sin eso la CMF no te inscribe."),
        ("5", "Pide el registro el 3 jul 2027", "Iniciador de pagos. Pagas 17 UF y dejas la garantía de UF 1.000 los primeros 6 meses."),
        ("6", "Cobra cuando el banco esté listo", "El cliente acepta en su banco. Tú ordenas el pago por el sistema. No guardas su clave. Si la plata pasa por ti, máximo 72 horas."),
    ]
    for i, (n, title, body) in enumerate(steps):
        y = 690 - i * 105
        card(c, 36, y - 88, 524, 96)
        c.setFillColor(TEAL if i < 4 else ORANGE)
        c.circle(64, y - 40, 16, fill=1, stroke=0)
        text(c, n, 64, y - 46, "Arial-Bold", 14, white, "center")
        text(c, title, 96, y - 28, "Arial-Bold", 13, NAVY)
        paragraph(c, body, 96, y - 50, 440, size=11, leading=14)
    footer(c, 14)


def page_cert(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "El certificado de seguridad", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "No lo firmas tú. Una empresa distinta prueba tu conexión y entrega el papel a la CMF.", 36, 762, 520, size=12, leading=15, color=MUTED)

    steps = [
        ("1", "Quién puede firmarlo", "Lleva al menos 3 años probando sistemas. Sabe de seguridad de conexiones (el estándar se llama FAPI) y tiene un sello tipo ISO 27001 o SOC 2."),
        ("2", "Dónde prueba", "En el ambiente de pruebas de la CMF, no en la cuenta real de un cliente. Revisa el directorio, el permiso del cliente y la orden de pago."),
        ("3", "Qué tiene que cumplir", "El canal va cifrado. Tú y el banco se identifican con certificado. El cliente entra en su banco. Tú no guardas la clave."),
        ("4", "Sin ese papel no hay registro", "Se adjunta al pedido de inscripción. La CMF no inscribe al iniciador de pagos si falta."),
        ("5", "No queda para siempre", "Se repite si cambias el sistema, sumas otra conexión o aparece una falla grave. El precio no está publicado: se cotiza."),
    ]
    for i, (n, title, body) in enumerate(steps):
        y = 690 - i * 125
        card(c, 36, y - 105, 524, 112)
        c.setFillColor(TEAL if i < 3 else ORANGE)
        c.circle(64, y - 48, 16, fill=1, stroke=0)
        text(c, n, 64, y - 54, "Arial-Bold", 14, white, "center")
        text(c, title, 96, y - 32, "Arial-Bold", 13, NAVY)
        paragraph(c, body, 96, y - 56, 440, size=11, leading=15)
    footer(c, 15)


def page_when(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Cuándo se cobra de verdad", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "Con la ley nueva. El registro no es el mismo día del primer cobro al cliente.", 36, 762, 520, size=12, leading=15, color=MUTED)

    steps = [
        ("1", "3 de julio de 2027", "Parte el sistema y pides el registro. Ese día todavía no hay cobro real por esta vía."),
        ("2", "Cerca de julio de 2028", "Primer cobro a una persona, por un pago solo. El banco tiene 12 meses para dejar lista esa conexión."),
        ("3", "Cerca de septiembre de 2028", "Pagos que se repiten, de una persona. Son 14 meses desde el inicio."),
        ("4", "Fines de 2028 a inicios de 2029", "Pagos de empresas. La norma da de 15 a 18 meses, según si el pago es único o se repite."),
        ("5", "Dos condiciones", "Tienes que estar inscrito, y solo cobras una conexión que ya probaste en el ambiente de la CMF."),
    ]
    for i, (n, title, body) in enumerate(steps):
        y = 690 - i * 125
        card(c, 36, y - 105, 524, 112)
        c.setFillColor(ORANGE if i == 0 else TEAL)
        c.circle(64, y - 48, 16, fill=1, stroke=0)
        text(c, n, 64, y - 54, "Arial-Bold", 14, white, "center")
        text(c, title, 96, y - 32, "Arial-Bold", 13, NAVY)
        paragraph(c, body, 96, y - 56, 440, size=11, leading=15)
    footer(c, 16)


def page_invoice(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Boleta o factura del cobro", 36, 790, "Arial-Bold", 24, NAVY)
    paragraph(c, "El documento es de tu comisión. La venta de $100.000 la documenta la tienda, no tú.", 36, 762, 520, size=12, leading=15, color=MUTED)

    steps = [
        ("1", "Qué monto va en el papel", "Solo el fee. En $100.000 al 0,69%, la comisión neta es $690. El IVA de 19% son $131. El total del documento es $821."),
        ("2", "Factura o boleta", "Factura electrónica si el cliente es una tienda con RUT. Boleta electrónica si el cliente es una persona."),
        ("3", "Cuándo se emite", "El día en que ganas la comisión. Sale del facturador del SII o de un software conectado al SII, con folio."),
        ("4", "Un cobro, un documento", "El sistema calcula el fee, pide el folio y envía el PDF al RUT de quien te paga la comisión."),
        ("5", "Si hay muchos cobros", "A la misma tienda se puede emitir una factura del día o del mes, con la lista de cada cobro. Cada uno queda en el detalle."),
        ("6", "Dos papeles si revendes", "Khipu o Fintoc te facturan a ti su fee. Tú le facturas a la tienda el precio que le cobras."),
    ]
    for i, (n, title, body) in enumerate(steps):
        y = 690 - i * 105
        card(c, 36, y - 88, 524, 96)
        c.setFillColor(GREEN if i < 4 else ORANGE)
        c.circle(64, y - 40, 16, fill=1, stroke=0)
        text(c, n, 64, y - 46, "Arial-Bold", 14, white, "center")
        text(c, title, 96, y - 28, "Arial-Bold", 13, NAVY)
        paragraph(c, body, 96, y - 50, 440, size=11, leading=14)
    footer(c, 17)


def page_close(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Para llevar", 36, 790, "Arial-Bold", 26, NAVY)

    takes = [
        (TEAL, "Khipu", "Transferencia. Tarifa citada: 0,69% + IVA. La plata llega al día hábil siguiente."),
        (ORANGE, "Fintoc", "Transferencia y cuentas. En Shopify Chile publica 1,35% + IVA."),
        (KLAP, "Klap", "Tarjeta. En la máquina, débito es un fijo más 0,62% + IVA. El link publica 2,89% + IVA."),
        (GREEN, "Para empezar", "Hoy: escribe a Khipu o a Fintoc y quédate un margen. El convenio propio con cada banco viene después, con la CMF."),
    ]
    y = 700
    for col, title, body in takes:
        card(c, 36, y - 70, 524, 82)
        c.setFillColor(col)
        c.rect(36, y - 70, 8, 82, fill=1, stroke=0)
        text(c, title, 60, y - 18, "Arial-Bold", 14, NAVY)
        paragraph(c, body, 60, y - 40, 470, size=12, leading=15)
        y -= 100

    card(c, 36, 70, 524, 150, RED_SOFT)
    circle_icon(c, 70, 175, 18, RED, "alert")
    text(c, "Ojo", 100, 168, "Arial-Bold", 14, RED)
    paragraph(
        c,
        "Las tarifas cambian con el contrato y con el volumen. La UF del 12 oct 2026 vale $41.147. Esto no dice cuánto ganan de verdad: eso no está publicado. Tampoco reemplaza a un abogado.",
        56, 140, 480, size=11, leading=15,
    )
    footer(c, 18)


def build():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle("Khipu, Fintoc y Klap, guía visual")
    for fn in (
        page_cover, page_simple, page_compare, page_fees, page_money, page_napkin, page_gains,
        page_law, page_steps, page_costs, page_now, page_help, page_enable, page_law_steps,
        page_cert, page_when, page_invoice, page_close,
    ):
        fn(c)
        c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    build()
