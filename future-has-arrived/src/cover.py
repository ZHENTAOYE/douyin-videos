"""Cover image (封面): the dusk chip-'city' with the title and the question."""
import numpy as np, cv2, skia
import gfx, cards, scene_chip
from config import W, H, OUTPUT

img = scene_chip.render_city(2.6)
img = gfx.bloom(img, 0.75, 0.8)
img = gfx.tonemap(img)
img = gfx.vignette(img, 0.35)
# darken the centre band so the type reads at thumbnail size
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
band = np.exp(-((yy - H * 0.47) / 230.0) ** 2) * np.exp(-((xx - W / 2) / 1100.0) ** 2)
img *= (1 - 0.55 * band)[..., None]
L = gfx.Layer()
c = L.canvas
f = cards.fnt('serif', 'Black', 190)
text = '未来已到达'
sp = 40
ws = [f.getWidths(f.textToGlyphs(ch))[0] for ch in text]
x = W / 2 - (sum(ws) + sp * (len(text) - 1)) / 2
for ch, w in zip(text, ws):
    b = skia.TextBlobBuilder()
    b.allocRunPos(f, f.textToGlyphs(ch), [skia.Point(x, H * 0.5 + 40)])
    blob = b.make()
    c.drawTextBlob(blob, 0, 6, cards.paint((0, 0, 0), 0.7, 24))
    c.drawTextBlob(blob, 0, 0, cards.paint(cards.WHITE, 1.0))
    x += w + sp
cards.draw_mixed(c, '人类的科技，究竟走到了哪一步？', W / 2, H * 0.5 + 150, cards.fnt('sans', 'Medium', 54),
                 cards.fnt('num', 'Medium', 58), cards.ACCENT, 1.0, align='center', spacing=6, shadow=0.9)
gfx.over(img, L.rgba())
out = f'{OUTPUT}/cover.jpg'
cv2.imwrite(out, cv2.cvtColor(gfx.to_u8(img), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
print(out)
