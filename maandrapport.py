import os
import json
import gspread
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import smtplib
import sys
import traceback
from email.message import EmailMessage

# --- 1. CONFIGURATIE VIA GITHUB SECRETS ---
def get_gspread_client():
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json:
            raise ValueError("Secret GOOGLE_CREDENTIALS is niet gevonden!")
        creds_dict = json.loads(creds_json)
        return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        print(f"!!! FOUT BIJ LADEN GOOGLE CREDENTIALS: {e}")
        sys.exit(1)

GOOGLE_SHEET_ID = '1oNNkeY5Uzgna7F3D2ZDIMbdEWwZL7mTxwPt9kR-p6Ow'
TABBLAD_NAAM = 'Seizoen 25 - 26'

EMAIL_AFZENDER = os.environ.get("GMAIL_USER")
EMAIL_WACHTWOORD = os.environ.get("GMAIL_PASSWORD")
EMAIL_ONTVANGERS = ["johan.jouck@hotmail.com"]

LOGO_PAD = "logo.png"  # Zorg dat dit bestand in je GitHub repo staat!
MAANDEN_NL = {1: "JANUARI", 2: "FEBRUARI", 3: "MAART", 4: "APRIL", 5: "MEI", 6: "JUNI", 7: "JULI", 8: "AUGUSTUS", 9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DECEMBER"}

# Kleuren
CLR_BG = (15, 23, 42)      
CLR_CARD = (30, 41, 59)    
CLR_ACCENT = (250, 204, 21) 
CLR_W = (34, 197, 94)      
CLR_G = (249, 115, 22)     
CLR_V = (239, 68, 68)      
CLR_TEXT = (241, 245, 249)

def verstuur_mail(bestandsnaam, pad, maand_naam):
    print(f">>> Poging om mail te sturen naar {EMAIL_ONTVANGERS}...")
    msg = EmailMessage()
    msg['Subject'] = f"📊 TEST Maandrapport FC Ambras: {maand_naam}"
    msg['From'] = EMAIL_AFZENDER
    msg['To'] = ", ".join(EMAIL_ONTVANGERS)
    
    msg.set_content(f"Dag Johan,\n\nDit is de automatische test van de Ambrasbot via GitHub Actions.\n\nSportieve groet,\nAmbrasbot")

    with open(pad, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename=bestandsnaam)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_AFZENDER, EMAIL_WACHTWOORD)
            smtp.send_message(msg)
        print(">>> E-MAIL SUCCESVOL VERZONDEN! 🚀")
    except Exception as e:
        print(f"!!! FOUT BIJ MAILEN: {e}")

def genereer_maandrapport():
    print(">>> Start genereren maandrapport...")
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        worksheet = sh.worksheet(TABBLAD_NAAM)
        data = worksheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        print(">>> Data succesvol ingeladen uit Google Sheets.")
    except Exception as e:
        print(f"!!! DATA-FOUT: {e}")
        return

    # Tijdslogica
    nu = datetime.now()
    vorige_maand_datum = nu.replace(day=1) - timedelta(days=1)
    rapport_maand_getal = vorige_maand_datum.month
    rapport_jaar = vorige_maand_datum.year
    rapport_maand_naam = MAANDEN_NL[rapport_maand_getal]

    start_rapport = vorige_maand_datum.replace(day=1, hour=0, minute=0, second=0)
    eind_rapport = vorige_maand_datum.replace(hour=23, minute=59, second=59)

    # Filteren & Berekenen
    df['Datum'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df['goals'] = pd.to_numeric(df['goals'], errors='coerce')
    df['goals tegen'] = pd.to_numeric(df['goals tegen'], errors='coerce')

    df_nu = df[(df['Datum'] >= start_rapport) & (df['Datum'] <= eind_rapport)].dropna(subset=['goals']).copy()
    
    voor, tegen = df_nu['goals'].sum(), df_nu['goals tegen'].sum()
    matchen = []
    for _, row in df_nu.iterrows():
        score = f"{int(row['goals'])} - {int(row['goals tegen'])}"
        matchen.append(f"{row['Datum'].strftime('%d/%m')} | {row['Thuisploeg']} {score} {row['Uitploeg']}")

    # Afbeelding maken
    print(">>> Bezig met tekenen afbeelding...")
    w, h = 1000, 1200 
    img = Image.new('RGB', (w, h), color=CLR_BG)
    draw = ImageDraw.Draw(img)
    
    # Gebruik een standaard Linux font dat op GitHub Actions aanwezig is
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        title_f = ImageFont.truetype(font_path, 60)
        head_f = ImageFont.truetype(font_path, 35)
        text_f = ImageFont.truetype(font_path, 25)
    except:
        print("!!! Specifiek font niet gevonden, gebruik standaard.")
        title_f = head_f = text_f = ImageFont.load_default()

    # Header tekenen
    draw.rectangle([0, 0, w, 200], fill=CLR_CARD)
    if os.path.exists(LOGO_PAD):
        logo = Image.open(LOGO_PAD).convert("RGBA")
        logo.thumbnail((120, 120))
        img.paste(logo, (40, 40), logo)
    
    draw.text((w/2, 80), "MAANDRAPPORT", fill=CLR_ACCENT, font=title_f, anchor="mm")
    draw.text((w/2, 140), f"{rapport_maand_naam} {rapport_jaar}", fill=CLR_TEXT, font=head_f, anchor="mm")

    # Matchen tekst
    y = 250
    draw.text((50, y), "GESPEELDE WEDSTRIJDEN:", fill=CLR_ACCENT, font=head_f)
    y += 60
    for m in matchen[:10]:
        draw.text((50, y), f"• {m}", fill=CLR_TEXT, font=text_f)
        y += 40

    # Opslaan in de huidige map (GitHub werkomgeving)
    bestandsnaam = "rapport_test.png"
    img.save(bestandsnaam)
    print(f">>> Afbeelding tijdelijk opgeslagen: {bestandsnaam}")
    
    verstuur_mail(bestandsnaam, bestandsnaam, rapport_maand_naam)

if __name__ == "__main__":
    print(">>> START GITHUB ACTIONS RUN...")
    genereer_maandrapport()
    print(">>> RUN VOLTOOID.")
