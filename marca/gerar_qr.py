"""Gera marca/png/qr-code-grupo.png com o link de convite do grupo.

Uso: pip install qrcode pillow && python marca/gerar_qr.py [link]
Rode de novo se o link do grupo for redefinido no WhatsApp, e depois
`node marca/exportar.js` para atualizar o story de convite.
"""

import sys
from pathlib import Path

import qrcode
from PIL import Image
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

LINK = sys.argv[1] if len(sys.argv) > 1 else "https://chat.whatsapp.com/JRY7yIMbOv609NylCljfsz"
PNG = Path(__file__).parent / "png"

q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=30, border=2)
q.add_data(LINK)
q.make(fit=True)
img = q.make_image(
    image_factory=StyledPilImage,
    module_drawer=RoundedModuleDrawer(),
    color_mask=SolidFillColorMask(back_color=(255, 255, 255), front_color=(0x1D, 0x44, 0xB8)),
).convert("RGB")

# logo no centro: a correção de erro "H" aguenta cobrir até 30% do código
lado = img.size[0]
s = int(lado * 0.24)
logo = Image.open(PNG / "foto-grupo.png").convert("RGB").resize((s, s), Image.LANCZOS)
moldura = Image.new("RGB", (s + 24, s + 24), "white")
moldura.paste(logo, (12, 12))
img.paste(moldura, ((lado - s - 24) // 2, (lado - s - 24) // 2))
img.resize((1080, 1080), Image.LANCZOS).save(PNG / "qr-code-grupo.png")
print("ok", PNG / "qr-code-grupo.png")
