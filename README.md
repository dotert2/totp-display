# TOTP Display – Raspberry Pi Zero W + e-Ink kijelző

Ez egy DIY hardveres TOTP (időalapú egyszer használatos jelszó) generátor,  
amely Raspberry Pi Zero W és Waveshare 2.13" V4 e-Paper kijelző segítségével jeleníti meg a 6 jegyű kódot.  
Alkalmazható Ügyfélkapu+, Google Authenticator, GitHub, Gmail és bármilyen TOTP (RFC 6238) alapú kétlépcsős hitelesítéshez (2FA).

---

## Hardver
- Raspberry Pi Zero W (512 MB RAM)
- Waveshare e-Paper 2.13" V4 kijelző (250×122)
- microSD kártya (Raspberry Pi OS Lite)
- Opcionális: DS3231 RTC modul (offline pontos időhöz)

---

## Rendszer előkészítés

1. Raspberry Pi OS Lite (Legacy 32-bit, Bullseye alapú) telepítése microSD-re a Raspberry Pi Imagerrel.
2. **Wi-Fi és SSH engedélyezés**:  
   - `wpa_supplicant.conf` + `ssh` fájl a BOOT partícióra
3. Első indítás után:  
   ```bash
   sudo apt update && sudo apt upgrade -y

## Szükséges csomagok telepítése

`sudo apt install -y git python3 python3-pip python3-pil python3-numpy python3-spidev python3-rpi.gpio fonts-dejavu-core`

`pip3 install pyotp`

## Waveshare e-Paper driver telepítése
```cd /opt
sudo git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install

## Projekt mappaszerkezet
```/opt/totp-display/
├── totp_display.py        # fő program
├── config.ini             # beállítások
├── totp_secret.txt        # titkos kulcs (ne töltsd fel GitHubra!)
├── fonts/
│   └── DejaVuSansMono.ttf
```


## Titkos kulcs
A totp_secret.txt fájlban tárold a BASE32 formátumú secretet, amit a szolgáltatás ad.
chmod 600 /opt/totp-display/totp_secret.txt

## Konfiguráció (config.ini)
```[display]
rotation = 90
invert = 0
label = Ugyfelkapu+

rotation: 0, 90, 180, 270 → kijelző elforgatás
invert: 0 = normál, 1 = fekete/fehér csere
label: a kijelző tetején megjelenő szöveg (pl. Ugyfelkapu+)

## Futtatás
cd /opt/totp-display
python3 totp_display.py

A kijelzőn megjelenik egy boot képernyő, majd a 6 jegyű TOTP kód.
A kód 30 másodpercenként frissül.

## Futtatás rendszerszolgáltatásként (systemd)
Hozz létre egy unit fájlt: /etc/systemd/system/totp-display.service

```[Unit]
Description=TOTP kijelző (Waveshare 2.13 V4) – /opt/totp-display
After=network-online.target time-sync.target
Wants=network-online.target

[Service]
Type=simple
User=user
Group=user
ExecStart=/usr/bin/python3 /opt/totp-display/totp_display.py
WorkingDirectory=/opt/totp-display
Restart=on-failure
# SPI és GPIO eléréshez szükség lehet:
AmbientCapabilities=CAP_SYS_RAWIO
# Környezet (ha kéne):
# Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target```

Aktiválás:
`sudo systemctl daemon-reload`
`sudo systemctl enable --now totp-display.service`
