from pathlib import Path
from PIL import Image, ImageDraw

p = Path(__file__).resolve().parent / 'vexi.ico'
if p.exists():
    print('ICON EXISTS:', p)
    raise SystemExit(0)
size=256
img=Image.new('RGBA',(size,size),(0,0,0,0))
d=ImageDraw.Draw(img)
d.ellipse((18,18,size-18,size-18),fill=(18,20,28,255),outline=(60,170,255,255),width=12)
d.ellipse((68,68,size-68,size-68),fill=(55,150,255,255))
d.ellipse((104,88,130,114),fill=(255,255,255,220))
img.save(p,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('DEFAULT ICON CREATED:', p)
