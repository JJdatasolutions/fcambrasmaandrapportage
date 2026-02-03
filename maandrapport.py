import os
import json
import gspread
import pandas as pd
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from PIL import Image, ImageDraw, ImageFont

# --- 1. CONFIGURATIE VIA GITHUB SECRETS & OMGEVING ---

def get_gspread_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Geen GOOGLE_CREDENTIALS gevonden in environment variables.")
    creds_dict = json.loads(creds_json)
    return gspread.service_account_from_dict(creds_dict)

GOOGLE_SHEET_ID = '1oNNkeY5Uzgna7F3D2ZDIMbdEWwZL7mTxwPt9kR-p6Ow'
TABBLAD_MATCHES = 'Seizoen 25 - 26'
TABBLAD_STATS = 'gamestats'

EMAIL_AFZENDER = os.environ.get("GMAIL_USER")
EMAIL_WACHTWOORD = os.environ.get("GMAIL_PASSWORD")

# Ontvangerslijst
EMAIL_ONTVANGERS = [
    "brightadiyia@gmail.com", "pieter_conjaerts@hotmail.com", "cedricpatyn@gmail.com", "daan_vananderoye@hotmail.com", 
    "johan.jouck@hotmail.com", "janoschkrzywania@hotmail.com", "joris.piette@hotmail.com", 
    "jort_vananderoye@hotmail.be", "maartenkenens1988@hotmail.com", 
    "maartenvandercammen_@hotmail.com", "maxim_patyn@hotmail.com", 
    "philippejaenen@outlook.com", "renaat.grossar@gmail.com", "robin.grossar@telenet.be", 
    "robinoptroodt1@hotmail.com", "rubentheuwen@gmail.com", "simonoptroodt@hotmail.com", 
    "tibo.geuns@hotmail.com", "tom.carlens@telenet.be", "t_vanhoyland@hotmail.com", 
    "jansgert@hotmail.com", "janlambrigts@gmail.com", "toonsjongers@outlook.com", 
    "lucien.jouck@telenet.be", "roxane_manirakiza@hotmail.com"
]

MAANDEN_NL = {1: "JANUARI", 2: "FEBRUARI", 3: "MAART", 4: "APRIL", 5: "MEI", 6: "JUNI", 7: "JULI", 8: "AUGUSTUS", 9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DECEMBER"}

# --- 2. KLEUREN & STIJL (NIEUW DESIGN) ---
CLR_BG = (15, 23, 42)        
CLR_CARD = (30, 41, 59)      
CLR_ACCENT = (250, 204, 21) # Goud/Geel
CLR_TEXT = (241, 245, 249)
CLR_W = (34, 197, 94)        
CLR_G = (249, 115, 22)       
CLR_V = (239, 68, 68)        

# --- 3. HULPFUNCTIES ---

def verstuur_mail(bestandsnaam, pad, maand_naam):
    print(f">>> Versturen naar {len(EMAIL_ONTVANGERS)} ontvangers...")
    msg = EmailMessage()
    msg['Subject'] = f"📊 Maandrapport FC Ambras: {maand_naam}"
    msg['From'] = EMAIL_AFZENDER
    msg['To'] = ", ".join(EMAIL_ONTVANGERS)
    
    msg.set_content(f"Dag beste vrienden van Ambras,\n\nHierbij het maandrapport van {maand_naam}.\n\nFC Ambras is wereldklas!\n\nMet sportieve groet,\nAmbrasbot")

    with open(pad, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename=bestandsnaam)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_AFZENDER, EMAIL_WACHTWOORD)
            smtp.send_message(msg)
        print(">>> E-MAIL SUCCESVOL VERZONDEN! 🚀")
    except Exception as e:
        print(f"!!! FOUT BIJ MAILEN: {e}")

def get_top_performers(df_stats, maand, jaar, stat_type):
    """Haalt top 5 spelers op voor goals of assists in de specifieke maand."""
    df_stats['Datum'] = pd.to_datetime(df_stats['Datum'], dayfirst=True, errors='coerce')
    mask = (df_stats['Datum'].dt.month == maand) & \
           (df_stats['Datum'].dt.year == jaar) & \
           (df_stats['Type'].str.lower() == stat_type.lower())
    
    filtered = df_stats[mask].copy()
    filtered['Aantal'] = pd.to_numeric(filtered['Aantal'], errors='coerce').fillna(0)
    summary = filtered.groupby('Speler')['Aantal'].sum().reset_index()
    return summary.sort_values(by='Aantal', ascending=False).head(5).values.tolist()

# --- 4. HOOFDFUNCTIE ---

def genereer_maandrapport():
    print(">>> Start genereren rapport...")

    # A. DATUMS BEREKENEN
    # Het script draait op 1 februari.
    nu = datetime.now() 
    
    # Rapport gaat over de VORIGE maand (Januari)
    eerste_dag_huidige_maand = nu.replace(day=1)
    laatste_dag_vorige_maand = eerste_dag_huidige_maand - timedelta(days=1)
    
    r_maand = laatste_dag_vorige_maand.month       # 1 (Januari)
    r_jaar = laatste_dag_vorige_maand.year         # 2026
    r_maand_naam = MAANDEN_NL[r_maand]

    # Programma gaat over de HUIDIGE maand (Februari)
    p_maand = nu.month                             # 2 (Februari)
    p_maand_naam = MAANDEN_NL[p_maand]

    print(f"Rapport voor: {r_maand_naam} {r_jaar}")
    print(f"Programma voor: {p_maand_naam}")

    # B. DATA OPHALEN
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        
        # Matches ophalen
        ws_m = sh.worksheet(TABBLAD_MATCHES)
        df = pd.DataFrame(ws_m.get_all_values()[1:], columns=ws_m.get_all_values()[0])
        
        # Stats ophalen (voor goals/assists)
        ws_s = sh.worksheet(TABBLAD_STATS)
        df_stats = pd.DataFrame(ws_s.get_all_values()[1:], columns=ws_s.get_all_values()[0])
    except Exception as e:
        print(f"!!! FOUT BIJ DATA OPHALEN: {e}"); return

    # C. DATA VERWERKEN (MATCHES & STATS)
    df['Datum'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    
    # Filter: Wedstrijden van de RAPPORT maand (Januari)
    df_rapport = df[(df['Datum'].dt.month == r_maand) & (df['Datum'].dt.year == r_jaar)].copy()
    
    winst, gelijk, verlies, voor, tegen = 0, 0, 0, 0, 0
    matchen_lijst = []

    for _, row in df_rapport.iterrows():
        score_val, tegen_val = str(row['goals']).strip(), str(row['goals tegen']).strip()
        
        if score_val == "" and tegen_val == "":
            matchen_lijst.append(f"{row['Datum'].strftime('%d/%m')} | {row['Thuisploeg']} - {row['Uitploeg']} (AFGELAST)")
        elif score_val.isdigit() and tegen_val.isdigit():
            g, gt = int(score_val), int(tegen_val)
            
            if g > gt: winst += 1
            elif g == gt: gelijk += 1
            else: verlies += 1
            
            voor += g
            tegen += gt
            
            score_tekst = f"{g} - {gt}" if "Ambras" in str(row['Thuisploeg']) else f"{gt} - {g}"
            matchen_lijst.append(f"{row['Datum'].strftime('%d/%m')} | {row['Thuisploeg']}  {score_tekst}  {row['Uitploeg']}")

    # Filter: Programma van de KOMENDE maand (Februari)
    df_prog = df[(df['Datum'].dt.month == p_maand) & (df['Datum'].dt.year == nu.year)]
    prog_lijst = [f"{r['Datum'].strftime('%d/%m')} - {r['Thuisploeg']} vs {r['Uitploeg']}" for _, r in df_prog.iterrows()]

    # Filter: Top Performers van de RAPPORT maand
    top_goals = get_top_performers(df_stats, r_maand, r_jaar, "goal")
    top_assists = get_top_performers(df_stats, r_maand, r_jaar, "assist")

    # D. VISUALISEREN (Het nieuwe design)
    w, h = 1000, 2000 
    img = Image.new('RGB', (w, h), color=CLR_BG)
    draw = ImageDraw.Draw(img)

    # Fonts (Linux paden voor GitHub Actions, fallback voor lokaal)
    linux_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    linux_font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    try:
        title_f = ImageFont.truetype(linux_font, 60)
        head_f = ImageFont.truetype(linux_font, 38)
        stat_f = ImageFont.truetype(linux_font, 80)
        gold_f = ImageFont.truetype(linux_font, 34)
        text_f = ImageFont.truetype(linux_font_reg, 28)
    except:
        # Fallback als fonts niet bestaan
        title_f = head_f = stat_f = gold_f = text_f = ImageFont.load_default()

    # 1. Header
    draw.rectangle([0, 0, w, 210], fill=CLR_CARD)
    draw.text((w/2, 80), "MAANDRAPPORT", fill=CLR_ACCENT, font=title_f, anchor="mm")
    draw.text((w/2, 150), f"{r_maand_naam} {r_jaar}", fill=CLR_TEXT, font=head_f, anchor="mm")

    # 2. Winst/Gelijk/Verlies Blokken
    y_s = 260
    for val, lbl, clr, x in [(winst, "WINST", CLR_W, 200), (gelijk, "GELIJK", CLR_G, 500), (verlies, "VERLIES", CLR_V, 800)]:
        draw.rounded_rectangle([x-140, y_s, x+140, y_s+160], radius=15, fill=CLR_CARD)
        draw.text((x, y_s+60), str(val), fill=clr, font=stat_f, anchor="mm")
        draw.text((x, y_s+125), lbl, fill=CLR_TEXT, font=text_f, anchor="mm")

    # 3. Goals Voor / Tegen Blokken
    y_g = 450
    # Box Voor
    draw.rounded_rectangle([150, y_g, 480, y_g+130], radius=15, fill=CLR_CARD)
    draw.text((315, y_g+50), str(voor), fill=CLR_W, font=stat_f, anchor="mm")
    draw.text((315, y_g+105), "GOALS VOOR", fill=CLR_TEXT, font=text_f, anchor="mm")
    # Box Tegen
    draw.rounded_rectangle([520, y_g, 850, y_g+130], radius=15, fill=CLR_CARD)
    draw.text((685, y_g+50), str(tegen), fill=CLR_V, font=stat_f, anchor="mm")
    draw.text((685, y_g+105), "GOALS TEGEN", fill=CLR_TEXT, font=text_f, anchor="mm")

    # 4. Top Performances (Goals & Assists)
    y_p = 620
    draw.text((100, y_p), "TOPPERFORMANCES", fill=CLR_ACCENT, font=head_f)
    
    def draw_fair_list(draw_obj, data, start_x, start_y, title, title_clr):
        draw_obj.rounded_rectangle([start_x, start_y, start_x+380, start_y+300], radius=15, fill=CLR_CARD)
        draw_obj.text((start_x+20, start_y+20), title, fill=title_clr, font=text_f)
        
        if not data:
            draw_obj.text((start_x+20, start_y+100), "Geen data", fill=(120,120,120), font=text_f)
            return

        max_score = data[0][1] 
        
        for idx, (naam, aantal) in enumerate(data[:4]): # Top 4 tonen
            is_winner = (aantal == max_score and aantal > 0)
            color = CLR_ACCENT if is_winner else CLR_TEXT
            font = gold_f if is_winner else text_f
            
            pos_label = "1." if is_winner else f"{idx+1}."
            draw_obj.text((start_x+20, start_y+85+(idx*50)), f"{pos_label} {naam}: {int(aantal)}", fill=color, font=font)

    draw_fair_list(draw, top_goals, 100, y_p+50, "GOALS", CLR_W)
    draw_fair_list(draw, top_assists, 520, y_p+50, "ASSISTS", CLR_ACCENT)

    # 5. Gespeelde Wedstrijden
    y_r = 1030
    draw.text((100, y_r), "GESPEELDE WEDSTRIJDEN", fill=CLR_ACCENT, font=head_f)
    for i, m in enumerate(matchen_lijst[:5]):
        y_pos = y_r + 60 + (i*60)
        draw.rounded_rectangle([100, y_pos, 900, y_pos+50], radius=8, fill=CLR_CARD)
        draw.text((120, y_pos+10), m, fill=CLR_TEXT, font=text_f)

    # 6. Programma Volgende Maand
    y_prog = 1430
    draw.rectangle([50, y_prog, w-50, y_prog+3], fill=CLR_ACCENT)
    draw.text((100, y_prog+40), f"PROGRAMMA {p_maand_naam}", fill=CLR_ACCENT, font=head_f)
    
    if not prog_lijst:
        draw.text((120, y_prog+110), "Geen wedstrijden gepland", fill=(150,150,150), font=text_f)
    else:
        for i, p in enumerate(prog_lijst[:6]):
            draw.text((120, y_prog+110+(i*50)), f"- {p}", fill=CLR_TEXT, font=text_f)

    # 7. Footer
    draw.rectangle([0, h-90, w, h], fill=CLR_ACCENT)
    draw.text((w/2, h-45), "FC AMBRAS IS WERELDKLAS!", fill=CLR_BG, font=head_f, anchor="mm")

    # E. OPSLAAN & VERZENDEN
    bestandsnaam = f"rapport_ambras_{r_maand}_{r_jaar}.png"
    img.save(bestandsnaam)
    print(f"Rapport gegenereerd: {bestandsnaam}")
    
    verstuur_mail(bestandsnaam, bestandsnaam, r_maand_naam)

if __name__ == "__main__":
    genereer_maandrapport()


