# TO DO
from PIL import Image, ImageDraw
im = Image.open('/home/yartu/Pictures/121410.jpg')
d = ImageDraw.Draw(im)
d.text(xy=(100, 100), text='DEDEDE', fill=(255, 69, 0))
im.save('qwe', 'JPEG')
