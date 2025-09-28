#!/usr/bin/env python3
# Procedurális (nem OOP) megközelítés, a kérésed szerint.

import os, sys, time, configparser
from PIL import Image, ImageDraw, ImageFont
import pyotp

# --- Beállítások betöltése ---
BASE_DIR = "/opt/totp-display"
CONF = os.path.join(BASE_DIR, "config.ini")
SECRET_FILE = os.path.join(BASE_DIR, "totp_secret.txt")
FONT_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSansMono.ttf")

config = configparser.ConfigParser()
config.read(CONF)
rotation = int(config.get("display", "rotation", fallback="0"))
invert   = int(config.get("display", "invert", fallback="0"))
label    = config.get("display", "label", fallback="TOTP")

# --- boot képernyő rajzoló
def draw_boot(img, line1="Indulás…", line2="Kérlek várj"):
    draw = ImageDraw.Draw(img)
    try:
        font_mid = ImageFont.truetype(FONT_PATH, 24)
        font_small = ImageFont.truetype(FONT_PATH, 16)
    except:
        font_mid = ImageFont.load_default()
        font_small = ImageFont.load_default()

    fg = 0 if invert == 0 else 255
    bg = 255 if invert == 0 else 0
    draw.rectangle((0,0,EPD_WIDTH,EPD_HEIGHT), fill=bg)

    # felső sarokba a label (pl. TOTP)
    draw.text((6, 6), f"{label}", font=font_small, fill=fg)

    # középre: line1
    w, h = draw.textsize(line1, font=font_mid)
    x = (EPD_WIDTH - w) // 2
    y = (EPD_HEIGHT - h) // 2 - 8
    draw.text((x, y), line1, font=font_mid, fill=fg)

    # alul: line2
    w2, h2 = draw.textsize(line2, font=font_small)
    x2 = (EPD_WIDTH - w2) // 2
    y2 = EPD_HEIGHT - h2 - 8
    draw.text((x2, y2), line2, font=font_small, fill=fg)

    return img

def show_boot(text_top="Indulás…", text_bottom="Kérlek várj"):
    img = blank_image()
    img = draw_boot(img, text_top, text_bottom)
    show_image(img)


# --- TOTP titok betöltése ---
def load_secret():
    if not os.path.exists(SECRET_FILE):
        return None
    with open(SECRET_FILE, "r") as f:
        raw = f.read().strip()
    # húzzuk le a megjegyzéseket és whitespace-t
    secret = raw.split("#", 1)[0].strip().replace(" ", "")
    return secret if secret else None

secret = load_secret()
totp = pyotp.TOTP(secret) if secret else None

# --- Kép buffer létrehozás ---
def blank_image():
    # fehér háttér (E-Ink-en a 255 a fehér)
    img = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
    return img

def draw_screen(img, code_text, seconds_left, status_text):
    draw = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype(FONT_PATH, 48)
        font_small = ImageFont.truetype(FONT_PATH, 16)
        font_mid   = ImageFont.truetype(FONT_PATH, 18)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_mid   = ImageFont.load_default()

    # Opcionális invertálás
    fg = 0 if invert == 0 else 255
    bg = 255 if invert == 0 else 0
    draw.rectangle((0,0,EPD_WIDTH,EPD_HEIGHT), fill=bg)

    # Címke
    draw.text((6, 6), f"{label}", font=font_small, fill=fg)

    # Kód (középre igazítva)
    w, h = draw.textsize(code_text, font=font_large)
    x = (EPD_WIDTH - w) // 2
    y = (EPD_HEIGHT - h) // 2 - 6
    draw.text((x, y), code_text, font=font_large, fill=fg)

    # Visszaszámláló + státusz
    bottom_text = f"{seconds_left:02d}mp van hátra   [{status_text}]"
    bw, bh = draw.textsize(bottom_text, font=font_mid)
    bx = (EPD_WIDTH - bw) // 2
    by = EPD_HEIGHT - bh - 6
    draw.text((bx, by), bottom_text, font=font_mid, fill=fg)

    return img

def rotate_if_needed(img):
    if rotation in (0, 90, 180, 270):
        return img.rotate(rotation, expand=True)
    return img

def show_image(img):
    if epd:
        # A V4 panel natív orientációja 122x250; a buffer 250x122, ezért forgatás után igazítunk
        out = rotate_if_needed(img)
        # Ha 90 vagy 270 fok, a méret felcserélődik – a driver 122x250-et vár.
        if out.size != (EPD_HEIGHT, EPD_WIDTH):
            out = out.resize((EPD_HEIGHT, EPD_WIDTH))
        epd.display(epd.getbuffer(out))
    else:
        # Fejlesztői fallback: csak kiírjuk a kódot stdout-ra
        out = img  # nem használjuk, hogy gyors legyen
        pass

def format_code(code):
    # 6 jegy -> 3-3-as csoport: "123 456"
    if len(code) == 6:
        return code[:3] + " " + code[3:]
    return code

# --- E-Ink driver import ---
EPD_WIDTH = 250
EPD_HEIGHT = 122
try:
    from waveshare_epd import epd2in13_V4
    epd = epd2in13_V4.EPD()
    epd.init()
    show_boot("Indulás...", "Kérlek várj")
except Exception as e:
    print("Hiba az e-Paper driver inicializálásakor:", e)
    print("Futunk 'kijelző nélküli' módon (stdout).")
    epd = None

def main_loop():
    global totp
    # Ha nincs kulcs, 5 mp-enként nézzük újra
    if totp is None:
        while True:
            img = blank_image()
            img = draw_screen(img, "------", 0, "NINCS KULCS – /opt/totp-display/totp_secret.txt")
            show_image(img)
            time.sleep(5)
            s = load_secret()
            if s:
                totp = pyotp.TOTP(s)
                break

    # szinkronizáljunk a 30 mp-es rácshoz
    step = 30
    first_draw = True
    while True:
        try:
            now = int(time.time())
            # hány mp van hátra az aktuális 30 mp-es ciklusból
            remaining = step - (now % step)

            # csak ciklushatáron (új kódnál) frissítünk kijelzőt
            if remaining == step:
                code = totp.now()
                code_fmt = format_code(code)

                if epd and first_draw:
                    epd.Clear(0xFF)
                    first_draw = False

                img = blank_image()
                img = draw_screen(img, code_fmt, step, "OK")
                show_image(img)

                # energia: aludjunk a ciklus végéig (kb. 29.5 mp)
                # (kis extra -0.5, hogy a következő határra biztos időben érjünk)
                time.sleep(step - 0.5)
            else:
                # várjunk a következő egész másodpercig pici CPU-val
                time.sleep(0.2)

        except KeyboardInterrupt:
            break
        except Exception as e:
            try:
                img = blank_image()
                img = draw_screen(img, "ERR", 0, str(e)[:22])
                show_image(img)
            except:
                pass
            time.sleep(2)

    if epd:
        epd.init()
        epd.Clear(0xFF)


if __name__ == "__main__":
    main_loop()
