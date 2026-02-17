#!/usr/bin/env python3
"""
Bolig Analyse Dashboard Generator v2.0
--------------------------------------
Genererer interaktivt HTML dashboard med dynamiske grafer og visualiseringer.
"""

import pandas as pd
import json
import sys
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

# Dansk font support
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Note: Vi genererer stadig matplotlib grafer for de statiske thumbnails,
# men bruger Plotly.js i browseren for interaktivitet

def safe_int(val, default=None):
    """Konverterer til int - håndterer '-', NaN, None og andre ugyldige værdier."""
    if val is None:
        return default
    if isinstance(val, str) and val.strip() in ('-', '', 'nan', 'None', 'N/A', '#N/A'):
        return default
    try:
        f = float(val)
        if pd.isna(f):
            return default
        return int(f)
    except (ValueError, TypeError):
        return default

def safe_float(val, default=None):
    """Konverterer til float - håndterer '-', NaN, None og andre ugyldige værdier."""
    if val is None:
        return default
    if isinstance(val, str) and val.strip() in ('-', '', 'nan', 'None', 'N/A', '#N/A'):
        return default
    try:
        f = float(val)
        if pd.isna(f):
            return default
        return f
    except (ValueError, TypeError):
        return default

def parse_city_from_handelsnavn(handelsnavn):

    """Udtrækker by fra handelsnavn format: 'Adresse, Postnr By'"""
    if pd.isna(handelsnavn):
        return "Ukendt"
    parts = handelsnavn.split(',')
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        words = last_part.split()
        if len(words) > 1:
            return ' '.join(words[1:])
    return "Ukendt"

def geocode_address(address):
    """Simpel geocoding baseret på kendt adresser"""
    known_addresses = {
        "Griffenfeldsgade 4B": (55.68953163, 12.55545457),
        "Rådmandsgade 34": (55.69978992, 12.55090717),
        "Rådmandsgade 36": (55.69987455, 12.55113735),
        "Venøgade 24": (55.71248034, 12.5644871),
        "Søllerødgade 17": (55.69416374, 12.54659476),
        "Søllerødgade 15": (55.69406004, 12.5467663),
        "Holger Danskes Vej 32": (55.68712091, 12.53648974),
        "Blegdamsvej 30A": (55.69266957, 12.56496568),
        "Bjelkes Allé 20": (55.69307928, 12.54489447),
        "Bjelkes Allé 16": (55.69284985, 12.54508262),
        "Alhambravej 15": (55.67535625, 12.54444716),
        "Alhambravej 13": (55.67517812, 12.54429515),
    }
    
    for known_addr, coords in known_addresses.items():
        if known_addr.lower() in address.lower():
            return coords
    
    return (55.6761, 12.5683)

def create_scatter_plot(df, mode='leje'):
    """Genererer scatter plot: Areal vs. Leje/Pris per m²"""
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#f0f2f5')
    ax.set_facecolor('#ffffff')

    if mode == 'leje':
        x_col = 'Leje/m2'
        y_col = 'Areal'
        room_col = 'Antal værelser'
        title = f'Areal vs. Leje per m²  (n={len(df)})'
        x_label = 'Leje per m² (kr./m²)'
    else:
        x_col = 'Pris pr. m2 (enhedsareal)'
        y_col = 'Enhedsareal'
        room_col = 'Antal Værelser'
        title = f'Areal vs. Pris per m²  (n={len(df)})'
        x_label = 'Pris per m² (kr./m²)'

    colors = {2: '#f59e0b', 3: '#ef4444', 4: '#3b82f6', 5: '#10b981', 6: '#8b5cf6', 7: '#06b6d4'}

    for rooms in sorted(df[room_col].dropna().unique()):
        subset = df[df[room_col] == rooms]
        color = colors.get(int(rooms), '#9ca3af')
        ax.scatter(subset[x_col], subset[y_col],
                  c=color, s=80, alpha=0.7, edgecolors='white', linewidth=0.8,
                  label=f'{int(rooms)} vær. (n={len(subset)})')

    # Trendlinje
    valid = df[[x_col, y_col]].dropna()
    if len(valid) > 2:
        x = valid[x_col].values
        y = valid[y_col].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(x.min(), x.max(), 100)
        y_pred = p(x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        ax.plot(x_line, p(x_line), '--', color='#6b7280', alpha=0.7, linewidth=1.5,
               label=f'Trendlinje (R²={r2:.3f})')

    ax.set_xlabel(x_label, fontsize=11, color='#374151')
    ax.set_ylabel('Areal (m²)', fontsize=11, color='#374151')
    ax.set_title(title, fontsize=13, fontweight='bold', color='#1a1d23', pad=12)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9, edgecolor='#e4e7ec')
    ax.grid(True, alpha=0.4, color='#d1d5db', linewidth=0.7)
    ax.tick_params(colors='#6b7280', labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor('#e4e7ec')

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f0f2f5')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return f"data:image/png;base64,{img_base64}"

def create_heatmap(df, mode='leje'):
    """Genererer heatmap matrix"""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#f0f2f5')
    ax.set_facecolor('#f0f2f5')

    if mode == 'leje':
        price_col = 'Leje/m2'
        room_col = 'Antal værelser'
        areal_col = 'Areal'
        title = 'Gennemsnitlig leje/m² efter areal og antal værelser'
        label = 'Leje/m² (kr.)'
    else:
        price_col = 'Pris pr. m2 (enhedsareal)'
        room_col = 'Antal Værelser'
        areal_col = 'Enhedsareal'
        title = 'Gennemsnitlig pris/m² efter areal og antal værelser'
        label = 'Pris/m² (kr.)'

    df_copy = df.copy()
    bins   = [0, 50, 75, 100, 115, 130, 200]
    labels = ['0-50 m²', '50-75 m²', '75-100 m²', '100-115 m²', '115-130 m²', '130+ m²']
    df_copy['Areal kategori'] = pd.cut(df_copy[areal_col], bins=bins, labels=labels, include_lowest=True)

    pivot = df_copy.groupby(['Areal kategori', room_col])[price_col].agg(['mean', 'count']).reset_index()
    pivot_matrix = pivot.pivot(index='Areal kategori', columns=room_col, values='mean')
    count_matrix = pivot.pivot(index='Areal kategori', columns=room_col, values='count')

    sns.heatmap(pivot_matrix, annot=False, cmap='Blues',
                ax=ax, cbar_kws={'label': label, 'shrink': 0.8},
                linewidths=2, linecolor='#f0f2f5')

    for i, row_label in enumerate(pivot_matrix.index):
        for j, col_label in enumerate(pivot_matrix.columns):
            value = pivot_matrix.iloc[i, j]
            count = count_matrix.iloc[i, j]
            if not pd.isna(value):
                ax.text(j + 0.5, i + 0.5, f'{int(value)}\n(n={int(count)})',
                       ha='center', va='center', fontsize=10, fontweight='600', color='#1a1d23')

    ax.set_xlabel('Antal værelser', fontsize=11, color='#374151')
    ax.set_ylabel('Areal kategori', fontsize=11, color='#374151')
    ax.set_title(title, fontsize=13, fontweight='bold', color='#1a1d23', pad=12)
    ax.tick_params(colors='#6b7280', labelsize=9)

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f0f2f5')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return f"data:image/png;base64,{img_base64}"

def create_summary_table(df, mode='leje'):
    """Genererer summary tabel"""
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor('#f0f2f5')
    ax.set_facecolor('#f0f2f5')
    ax.axis('off')
    
    if mode == 'leje':
        price_m2_col = 'Leje/m2'
        price_total_col = 'Årsleje'
        room_col = 'Antal værelser'
        areal_col = 'Areal'
        extra_col = 'Liggedage'
        title = 'Lejepris analyse'
    else:
        price_m2_col = 'Pris pr. m2 (enhedsareal)'
        price_total_col = 'Pris'
        room_col = 'Antal Værelser'
        areal_col = 'Enhedsareal'
        extra_col = None
        title = 'Salgspris analyse'
    
    # Kategoriser areal
    df_copy = df.copy()
    bins = [0, 50, 75, 100, 115, 130, 200]
    labels = ['0-50 m²', '50-75 m²', '75-100 m²', '100-115 m²', '115-130 m²', '130+ m²']
    df_copy['Areal kategori'] = pd.cut(df_copy[areal_col], bins=bins, labels=labels, include_lowest=True)
    
    # Beregn statistikker
    agg_dict = {
        areal_col: 'count',
        price_m2_col: 'mean',
        price_total_col: lambda x: (x / 12).mean() if mode == 'leje' else x.mean(),
        room_col: 'mean',
    }
    
    if extra_col:
        agg_dict[extra_col] = 'mean'
    
    summary = df_copy.groupby('Areal kategori').agg(agg_dict).reset_index()
    
    cols = ['Areal', 'Antal lejepunkter' if mode == 'leje' else 'Antal salgspunkter', 
            f'Leje pr. m²' if mode == 'leje' else 'Pris pr. m²',
            f'Leje pr. måned' if mode == 'leje' else 'Pris',
            'Antal værelser']
    
    if mode == 'leje':
        cols.append('Liggetid (dage)')
    
    summary.columns = cols
    
    # Format values - med NaN beskyttelse
    pris_m2_col = 'Leje pr. m²' if mode == 'leje' else 'Pris pr. m²'
    pris_col    = 'Leje pr. måned' if mode == 'leje' else 'Pris'
    
    summary[pris_m2_col] = summary[pris_m2_col].apply(lambda x: f'{int(x)} kr.' if pd.notna(x) else '-')
    summary[pris_col]    = summary[pris_col].apply(lambda x: f'{int(x):,} kr.'.replace(',', '.') if pd.notna(x) else '-')
    summary['Antal værelser'] = summary['Antal værelser'].apply(lambda x: f'{x:.1f}' if pd.notna(x) else '-')
    if mode == 'leje':
        summary['Liggetid (dage)'] = summary['Liggetid (dage)'].apply(lambda x: f'{int(x)}' if pd.notna(x) else '-')
    
    # Tilføj total række
    total_row = {
        'Areal': f'Gns. areal: {int(df[areal_col].mean())} m²',
        'Antal lejepunkter' if mode == 'leje' else 'Antal salgspunkter': str(len(df)),
        f'Leje pr. m²' if mode == 'leje' else 'Pris pr. m²': f'{int(df[price_m2_col].mean())} kr.',
        f'Leje pr. måned' if mode == 'leje' else 'Pris': f'{int((df[price_total_col] / 12).mean() if mode == "leje" else df[price_total_col].mean()):,} kr.'.replace(',', '.'),
        'Antal værelser': f'{df[room_col].mean():.1f}',
    }
    if mode == 'leje':
        total_row['Liggetid (dage)'] = str(int(df[extra_col].mean()))
    
    summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)
    
    # Opret tabel
    table = ax.table(cellText=summary.values, colLabels=summary.columns,
                    cellLoc='center', loc='center',
                    colWidths=[0.2, 0.18, 0.16, 0.18, 0.15, 0.13] if mode == 'leje' else [0.25, 0.2, 0.18, 0.2, 0.17])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Header
    for i in range(len(summary.columns)):
        table[(0, i)].set_facecolor('#e4e7ec')
        table[(0, i)].set_text_props(weight='bold', color='#1a1d23')

    # Rækker
    for i in range(1, len(summary) + 1):
        for j in range(len(summary.columns)):
            if i == len(summary):
                table[(i, j)].set_facecolor('#d4d8e0')
                table[(i, j)].set_text_props(weight='bold', color='#1a1d23')
            elif i % 2 == 0:
                table[(i, j)].set_facecolor('#f8f9fa')
                table[(i, j)].set_text_props(color='#1a1d23')
            else:
                table[(i, j)].set_facecolor('#ffffff')
                table[(i, j)].set_text_props(color='#1a1d23')

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f0f2f5')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return f"data:image/png;base64,{img_base64}"

def process_leje_data(excel_path):
    """Læser og behandler lejedata - hardcodede kolonnenavne"""
    try:
        df = pd.read_excel(excel_path, sheet_name='Worksheet', na_values=['-'])
    except:
        df = pd.read_excel(excel_path, na_values=['-'])

    # Erstat '-' og lignende tomme værdier med NaN globalt
    df = df.replace(['-', '', 'N/A', '#N/A', 'None', 'nan'], pd.NA)

    # Tving alle numeriske kolonner til numeric - ugyldige værdier bliver NaN
    for col in ['Areal', 'Leje/m2', 'Årsleje', 'Liggedage', 'Antal værelser', 'Opførelsesår', 'Lat', 'Lng']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # Lejedata kolonner:
    # Adresse, By, Lat, Lng, Areal, Leje/m2, Årsleje, Liggedage, Antal værelser
    # Valgfrit: Opførelsesår, Boligtype

    df['Opførelsesår'] = df['Opførelsesår'] if 'Opførelsesår' in df.columns else None
    df['Boligtype']    = df['Boligtype']    if 'Boligtype'    in df.columns else 'Ikke angivet'
    df['Leje/måned']   = df['Årsleje'] / 12

    # Parse dato
    if 'Dato' in df.columns:
        df['_dato'] = pd.to_datetime(df['Dato'], dayfirst=True, errors='coerce')
        df['_dato_str'] = df['_dato'].dt.strftime('%Y-%m-%d')
        df['_dato_ts']  = df['_dato'].apply(lambda x: int(x.timestamp()) if pd.notna(x) else None)
    else:
        df['_dato_str'] = None
        df['_dato_ts']  = None
    
    # Generer grafer
    print("   Genererer scatter plot...")
    scatter_img = create_scatter_plot(df, mode='leje')
    print("   Genererer heatmap...")
    heatmap_img = create_heatmap(df, mode='leje')
    print("   Genererer tabel...")
    table_img = create_summary_table(df, mode='leje')
    
    # Rens data - fjern NaN værdier før konvertering
    original_count = len(df)
    df = df.dropna(subset=['Adresse', 'By', 'Lat', 'Lng', 'Areal', 'Leje/m2', 'Årsleje', 'Liggedage', 'Antal værelser'])
    dropped = original_count - len(df)
    if dropped > 0:
        print(f"   ⚠️  Fjernet {dropped} rækker med manglende data")
    
    # Konverter til dictionary
    boliger = []
    for _, row in df.iterrows():
        bolig = {
            'adresse': str(row['Adresse']),
            'by': str(row['By']),
            'lat': float(row['Lat']),
            'lng': float(row['Lng']),
            'areal': safe_int(row['Areal'], 0),
            'leje_m2': safe_int(row['Leje/m2'], 0),
            'leje_maned': safe_int(row['Årsleje'] / 12 if safe_float(row['Årsleje']) else 0, 0),
            'liggedage': safe_int(row['Liggedage'], 0),
            'varelser': safe_int(row['Antal værelser'], 0),
            'opfoerelsesaar': safe_int(row['Opførelsesår']),
            'boligtype': str(row['Boligtype']) if pd.notna(row['Boligtype']) and str(row['Boligtype']) not in ('-', 'None') else 'Ikke angivet',
            'dato': str(row['_dato_str']) if row['_dato_str'] is not None and pd.notna(row['_dato_str']) else None,
            'dato_ts': safe_int(row['_dato_ts']),
        }
        boliger.append(bolig)
    
    # Statistikker
    total = len(boliger)
    gns_leje_m2 = int(df['Leje/m2'].mean())
    gns_areal = int(df['Areal'].mean())
    gns_leje = int((df['Årsleje'] / 12).mean())
    median_leje = int((df['Årsleje'] / 12).median())
    center_lat = df['Lat'].mean()
    center_lng = df['Lng'].mean()
    
    vaerelser_counts = df['Antal værelser'].value_counts().sort_index()
    vaerelser_data = [{'varelser': int(k), 'antal': int(v)} for k, v in vaerelser_counts.items()]
    
    by_counts = df['By'].value_counts()
    by_data = [{'by': str(k), 'antal': int(v)} for k, v in by_counts.items()]
    
    return {
        'total_boliger': total,
        'gns_leje_m2': gns_leje_m2,
        'gns_areal': gns_areal,
        'gns_leje': gns_leje,
        'median_leje': median_leje,
        'center_lat': center_lat,
        'center_lng': center_lng,
        'vaerelser_data': vaerelser_data,
        'by_data': by_data,
        'boliger': boliger,
        'scatter_img': scatter_img,
        'heatmap_img': heatmap_img,
        'table_img': table_img
    }

def find_column(df, possible_names):
    """Finder en kolonne baseret på mulige navne"""
    for name in possible_names:
        if name in df.columns:
            return name
    
    # Hvis ikke fundet, vis hjælpsom fejlmeddelelse
    print(f"\n❌ FEJL: Kunne ikke finde nogen af disse kolonner: {possible_names}")
    print(f"\n📋 Tilgængelige kolonner i filen:")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i}. {col}")
    print(f"\n💡 TIP: Tjek at Excel-filen har de rigtige kolonnenavne.")
    raise KeyError(f"Kunne ikke finde nogen af disse kolonner: {possible_names}")

def process_ejer_data(excel_path):
    """Læser og behandler ejerdata - hardcodede kolonnenavne"""
    
    # Stamdata: Handels-ID, Handelsnavn, Handelsdato, Pris, Enhedsareal,
    #           Pris pr. m2 (enhedsareal), Anvendelse
    # Enheder:  Handels-ID, Antal værelser, Latitude, Longitude
    # Ejendomme (valgfri): Handels-ID, Opførelsesår

    excel_file = pd.ExcelFile(excel_path)

    # Læs Stamdata
    df = pd.read_excel(excel_path, sheet_name='Stamdata', na_values=['-'])

    # Erstat '-' og lignende tomme værdier med NaN globalt
    df = df.replace(['-', '', 'N/A', '#N/A', 'None', 'nan'], pd.NA)

    # Merge Enheder - find kolonner fleksibelt
    df_enheder = pd.read_excel(excel_path, sheet_name='Enheder', na_values=['-'])
    df_enheder = df_enheder.replace(['-', '', 'N/A', '#N/A', 'None', 'nan'], pd.NA)
    
    # Find Antal værelser kolonnen (forskellig stavemåde)
    vaerelser_col = None
    for name in ['Antal værelser', 'Antal Værelser', 'AntalVærelser', 'Antal vaerelser', 'Antal Vaerelser', 'Rooms', 'Værelser']:
        if name in df_enheder.columns:
            vaerelser_col = name
            break
    
    # Find koordinat kolonner (forskellig stavemåde)
    lat_col = next((c for c in df_enheder.columns if c.lower() in ['latitude', 'lat', 'breddegrad']), None)
    lng_col = next((c for c in df_enheder.columns if c.lower() in ['longitude', 'lng', 'lon', 'længdegrad', 'laengdegrad']), None)
    
    merge_cols = ['Handels-ID']
    if vaerelser_col: merge_cols.append(vaerelser_col)
    if lat_col:       merge_cols.append(lat_col)
    if lng_col:       merge_cols.append(lng_col)
    
    df = df.merge(df_enheder[merge_cols], on='Handels-ID', how='left')
    
    # Normaliser kolonnenavne
    df['Antal Værelser'] = df[vaerelser_col] if vaerelser_col else None
    df['lat'] = df[lat_col] if lat_col else None
    df['lng'] = df[lng_col] if lng_col else None

    # Merge Ejendomme (valgfri)
    if 'Ejendomme' in excel_file.sheet_names:
        df_ejendomme = pd.read_excel(excel_path, sheet_name='Ejendomme', na_values=['-'])
        aar_col = next((c for c in df_ejendomme.columns if 'opf' in c.lower() or 'bygge' in c.lower() or 'år' in c.lower()), None)
        if aar_col:
            df = df.merge(df_ejendomme[['Handels-ID', aar_col]], on='Handels-ID', how='left')
            if aar_col != 'Opførelsesår':
                df['Opførelsesår'] = df[aar_col]
        else:
            df['Opførelsesår'] = None
    else:
        df['Opførelsesår'] = None

    df['Anvendelse'] = df['Anvendelse'] if 'Anvendelse' in df.columns else 'Ikke angivet'
    df['By']         = df['Handelsnavn'].apply(parse_city_from_handelsnavn)
    df['_dato']      = pd.to_datetime(df['Handelsdato'], errors='coerce')
    df['Handelsdato_str'] = df['_dato'].dt.strftime('%Y-%m-%d')
    df['_dato_ts']   = df['_dato'].apply(lambda x: int(x.timestamp()) if pd.notna(x) else None)

    # Konverter typer sikkert - errors='coerce' gør '-' og ugyldige værdier til NaN
    df['Antal Værelser'] = pd.to_numeric(df['Antal Værelser'], errors='coerce')
    df['Enhedsareal']    = pd.to_numeric(df['Enhedsareal'],    errors='coerce')
    df['Pris']           = pd.to_numeric(df['Pris'],           errors='coerce')
    df['Pris pr. m2 (enhedsareal)'] = pd.to_numeric(df['Pris pr. m2 (enhedsareal)'], errors='coerce')
    if 'Opførelsesår' in df.columns:
        df['Opførelsesår'] = pd.to_numeric(df['Opførelsesår'], errors='coerce')
    if 'lat' in df.columns:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    if 'lng' in df.columns:
        df['lng'] = pd.to_numeric(df['lng'], errors='coerce')

    # Rens data - fjern rækker med manglende vigtige data
    original_count = len(df)
    required = ['Handelsnavn', 'By', 'lat', 'lng', 'Enhedsareal', 'Pris', 'Pris pr. m2 (enhedsareal)', 'Antal Værelser']
    df = df.dropna(subset=required)
    dropped = original_count - len(df)
    if dropped > 0:
        print(f"   ⚠️  Fjernet {dropped} rækker med manglende data")

    # Nu er det sikkert at konvertere til int
    df['Antal Værelser'] = df['Antal Værelser'].astype(int)
    df['Enhedsareal']    = df['Enhedsareal'].astype(int)
    df['Pris']           = df['Pris'].astype(int)
    df['Pris pr. m2 (enhedsareal)'] = df['Pris pr. m2 (enhedsareal)'].astype(int)

    # Generer grafer
    print("   Genererer scatter plot...")
    scatter_img = create_scatter_plot(df, mode='ejer')
    print("   Genererer heatmap...")
    heatmap_img = create_heatmap(df, mode='ejer')
    print("   Genererer tabel...")
    table_img = create_summary_table(df, mode='ejer')
    
    # Konverter til dictionary
    boliger = []
    for _, row in df.iterrows():
        bolig = {
            'handelsnavn': str(row['Handelsnavn']),
            'by': str(row['By']),
            'lat': float(row['lat']),
            'lng': float(row['lng']),
            'areal': safe_int(row['Enhedsareal'], 0),
            'pris': safe_int(row['Pris'], 0),
            'pris_m2': safe_int(row['Pris pr. m2 (enhedsareal)'], 0),
            'varelser': safe_int(row['Antal Værelser'], 0),
            'handelsdato': str(row['Handelsdato_str']),
            'dato_ts': safe_int(row['_dato_ts']),
            'anvendelse': str(row['Anvendelse']) if pd.notna(row['Anvendelse']) and str(row['Anvendelse']) not in ('-', 'None') else 'Ikke angivet',
            'opfoerelsesaar': safe_int(row['Opførelsesår'])
        }
        boliger.append(bolig)
    
    # Statistikker
    total = len(boliger)
    gns_pris_m2 = int(df['Pris pr. m2 (enhedsareal)'].mean())
    gns_areal = int(df['Enhedsareal'].mean())
    gns_pris = int(df['Pris'].mean())
    median_pris = int(df['Pris'].median())
    center_lat = df['lat'].mean()
    center_lng = df['lng'].mean()
    
    vaerelser_counts = df['Antal Værelser'].value_counts().sort_index()
    vaerelser_data = [{'varelser': int(k), 'antal': int(v)} for k, v in vaerelser_counts.items()]
    
    by_counts = df['By'].value_counts()
    by_data = [{'by': str(k), 'antal': int(v)} for k, v in by_counts.items()]
    
    return {
        'total_boliger': total,
        'gns_pris_m2': gns_pris_m2,
        'gns_areal': gns_areal,
        'gns_pris': gns_pris,
        'median_pris': median_pris,
        'center_lat': center_lat,
        'center_lng': center_lng,
        'vaerelser_data': vaerelser_data,
        'by_data': by_data,
        'boliger': boliger,
        'scatter_img': scatter_img,
        'heatmap_img': heatmap_img,
        'table_img': table_img
    }

def generate_html(leje_data, ejer_data, output_path):
    """Genererer HTML dashboardet"""
    
    html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bolig Analyse</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-panel:     #f0f2f5;
            --bg-panel-2:   #e4e7ec;
            --bg-panel-3:   #d4d8e0;
            --border:       rgba(0,0,0,0.08);
            --border-hi:    rgba(0,0,0,0.15);
            --text-primary: #1a1d23;
            --text-secondary: #4b5563;
            --text-muted:   #8b95a3;
            --accent:       #3b82f6;
            --accent-glow:  rgba(59,130,246,0.2);
            --danger:       #ef4444;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            overflow: hidden;
            background: #e8eaed;
            color: var(--text-primary);
        }
        #map { position: fixed; left: 0; top: 0; width: 100%; height: 100vh; }

        /* ── Mode toggle ─────────────────────────────── */
        .mode-toggle {
            position: fixed;
            top: 18px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1001;
            background: var(--bg-panel);
            border: 1px solid var(--border-hi);
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            padding: 4px;
            gap: 2px;
        }
        .mode-btn {
            background: transparent;
            border: none;
            padding: 8px 20px;
            font-size: 12px;
            font-weight: 600;
            font-family: inherit;
            letter-spacing: 0.04em;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s;
            color: var(--text-secondary);
        }
        .mode-btn:hover { color: var(--text-primary); background: var(--bg-panel-2); }
        .mode-btn.active { background: var(--accent); color: white; }
        .mode-divider { width: 1px; height: 20px; background: var(--border-hi); margin: 0 4px; }

        /* ── BI boxes ────────────────────────────────── */
        .bi-boxes {
            position: fixed;
            top: 74px;
            right: 18px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .bi-box {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            padding: 12px;
            width: 200px;
        }
        .bi-box-title {
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 10px;
        }

        /* ── KPI ─────────────────────────────────────── */
        .kpi-compact {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
        }
        .kpi-item { text-align: center; }
        .kpi-item.full {
            grid-column: span 2;
            background: var(--accent);
            padding: 8px;
            border-radius: 6px;
        }
        .kpi-value-small {
            font-size: 17px;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.1;
        }
        .kpi-item.full .kpi-value-small { color: white; }
        .kpi-label-small {
            font-size: 8px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .kpi-item.full .kpi-label-small { color: rgba(255,255,255,0.7); }

        canvas { max-height: 120px !important; }

        /* ── Filters ─────────────────────────────────── */
        .filter-group { margin-bottom: 14px; }
        .filter-label {
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 7px;
            display: block;
        }
        .filter-options { display: flex; flex-wrap: wrap; gap: 5px; }
        .filter-btn {
            background: var(--bg-panel-2);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 4px 11px;
            font-size: 11px;
            font-weight: 500;
            font-family: inherit;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .filter-btn:hover { background: var(--bg-panel-3); color: var(--text-primary); border-color: var(--border-hi); }
        .filter-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

        .reset-btn {
            background: transparent;
            color: var(--danger);
            border: 1px solid rgba(239,68,68,0.3);
            padding: 7px;
            font-size: 10px;
            font-weight: 600;
            font-family: inherit;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            transition: all 0.15s ease;
        }
        .reset-btn:hover { background: rgba(239,68,68,0.1); border-color: var(--danger); }

        #filter-panel { background: var(--bg-panel) !important; border-right: 1px solid var(--border) !important; }

        /* ── Turnkey panel ───────────────────────────── */
        #turnkey-toggle {
            position: fixed;
            bottom: 145px;
            left: 18px;
            z-index: 1001;
            background: var(--bg-panel);
            border: 1px solid var(--border-hi);
            color: var(--text-secondary);
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            font-family: inherit;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            transition: all 0.15s ease;
            display: none;
        }
        #turnkey-toggle:hover { background: var(--bg-panel-2); color: var(--text-primary); }
        #turnkey-toggle.open { background: var(--accent); color: white; border-color: var(--accent); }

        #turnkey-panel {
            position: fixed;
            bottom: 175px;
            left: 18px;
            z-index: 1000;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            width: 460px;
            display: none;
            flex-direction: row;
            gap: 14px;
            align-items: flex-end;
        }
        #turnkey-panel .tk-field { flex: 1; }
        #turnkey-panel .tk-label {
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 6px;
            display: block;
        }
        #turnkey-panel input[type=number] {
            width: 100%;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            color: #1e293b;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 13px;
            font-weight: 600;
            font-family: inherit;
            box-sizing: border-box;
        }
        #turnkey-panel input[type=number]:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 2px var(--accent-glow);
        }
        #turnkey-panel .tk-result {
            flex: 1;
            background: rgba(59,130,246,0.08);
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 8px;
            padding: 10px 12px;
            text-align: center;
        }
        #turnkey-panel .tk-result-label {
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 4px;
        }
        #turnkey-panel .tk-result-value {
            font-size: 20px;
            font-weight: 800;
            color: var(--accent);
            line-height: 1;
        }
        #turnkey-panel .tk-result-unit {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 3px;
        }

        /* ── Overlay ─────────────────────────────────── */
        .overlay {
            display: none; position: fixed; z-index: 2000;
            left: 0; top: 0; width: 100%; height: 100vh;
            background-color: rgba(10,16,30,0.85);
            backdrop-filter: blur(6px);
        }
        .overlay-inner { display: flex; width: 100%; height: 100vh; align-items: stretch; }
        .overlay-filters {
            width: 210px; flex-shrink: 0;
            background: var(--bg-panel) !important;
            border-right: 1px solid var(--border) !important;
            padding: 16px; overflow-y: auto;
        }
        .overlay-filters .filter-group { margin-bottom: 14px; }
        .overlay-filters .filter-label {
            font-size: 9px; letter-spacing: 0.12em; color: var(--text-muted);
            margin-bottom: 7px; font-weight: 700; text-transform: uppercase;
        }
        .overlay-filters .filter-options { display: flex; flex-wrap: wrap; gap: 5px; }
        .overlay-filters .filter-btn {
            background: var(--bg-panel-2); color: var(--text-secondary);
            border: 1px solid var(--border);
            padding: 4px 11px; border-radius: 6px; font-size: 11px;
            font-family: inherit; cursor: pointer; transition: all 0.15s ease;
        }
        .overlay-filters .filter-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
        .overlay-filters .reset-btn {
            width: 100%; background: transparent; color: var(--danger);
            border: 1px solid rgba(239,68,68,0.3);
            padding: 7px; border-radius: 6px; cursor: pointer;
            font-size: 10px; font-weight: 600; font-family: inherit;
            letter-spacing: 0.06em; text-transform: uppercase; margin-top: 10px;
            transition: all 0.15s ease;
        }
        .overlay-filters .reset-btn:hover { background: rgba(239,68,68,0.1); border-color: var(--danger); }
        .overlay-chart { flex: 1; padding: 16px; display: flex; flex-direction: column; background: #e4e7ec; }
        .overlay-chart-inner { flex: 1; background: #f0f2f5; border-radius: 8px; overflow: auto; }
        .close {
            position: absolute; top: 12px; right: 18px;
            color: var(--text-secondary); font-size: 22px; font-weight: 400;
            cursor: pointer; z-index: 2100; line-height: 1;
            font-family: inherit; transition: color 0.15s;
        }
        .close:hover { color: var(--text-primary); }

        /* ── Map popups & legend ─────────────────────── */
        .info-box {
            padding: 14px; background: var(--bg-panel);
            border: 1px solid var(--border-hi);
            border-radius: 8px; color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            min-width: 200px;
        }
        .info-box h3 { margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .info-box p { margin: 4px 0; font-size: 12px; color: var(--text-secondary); }
        .info-box strong { color: var(--text-primary); font-weight: 600; }
        .info-box hr { border: none; border-top: 1px solid var(--border); margin: 8px 0; }

        .legend {
            padding: 10px 12px;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
        }
        .legend h4 { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
        .legend-item { margin: 5px 0; display: flex; align-items: center; font-size: 11px; color: var(--text-secondary); }
        .legend-color { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; flex-shrink: 0; }
        .legend p { font-size: 10px; color: var(--text-muted); margin-top: 8px; font-style: normal; }

        /* ── Sliders ─────────────────────────────────── */
        #sliders-wrapper > div {
            background: var(--bg-panel) !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
            border-radius: 10px !important;
        }
        input[type=range] {
            -webkit-appearance: none; appearance: none;
            height: 3px; background: var(--bg-panel-3);
            border-radius: 2px; outline: none; cursor: pointer;
        }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 14px; height: 14px;
            background: var(--accent); border-radius: 50%; cursor: pointer;
            box-shadow: 0 0 6px var(--accent-glow); transition: transform 0.15s ease;
        }
        input[type=range]::-webkit-slider-thumb:hover { transform: scale(1.25); }
        input[type=range]::-moz-range-thumb {
            width: 14px; height: 14px;
            background: var(--accent); border-radius: 50%; cursor: pointer; border: none;
        }
        #year-slider-min, #year-slider-max {
            pointer-events: none; -webkit-appearance: none; height: 3px; background: transparent;
        }
        #year-slider-min::-webkit-slider-thumb { pointer-events: all; z-index: 4; }
        #year-slider-max::-webkit-slider-thumb { pointer-events: all; z-index: 5; }

        /* ── Thumbnails ──────────────────────────────── */
        .thumbnails {
            position: fixed; bottom: 18px; left: 18px;
            z-index: 1000; display: flex; gap: 10px;
        }
        .thumbnail {
            width: 148px; height: 98px; cursor: pointer;
            border-radius: 8px; overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5);
            transition: all 0.2s; opacity: 0.65;
            border: 1px solid var(--border-hi);
        }
        .thumbnail:hover { opacity: 1; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.6); }
        .thumbnail img { width: 100%; height: 100%; object-fit: cover; }

        /* ── Table ───────────────────────────────────── */
        .analysis-table {
            width: 100%; border-collapse: collapse;
            font-family: 'Inter', sans-serif; font-size: 12px;
        }
        .analysis-table th {
            background: var(--bg-panel-2); color: var(--text-secondary);
            font-size: 9px; font-weight: 700; letter-spacing: 0.1em;
            text-transform: uppercase; padding: 11px 14px;
            border-bottom: 1px solid var(--border-hi); text-align: center;
        }
        .analysis-table th.tk-col {
            background: var(--accent); color: rgba(255,255,255,0.9);
        }
        .analysis-table td {
            padding: 10px 14px; text-align: center;
            border-bottom: 1px solid var(--border);
            color: var(--text-primary);
        }
        .analysis-table tr:last-child td { border-bottom: none; }
        .analysis-table tr.row-even td { background: rgba(0,0,0,0.02); }
        .analysis-table tr.row-odd  td { background: rgba(0,0,0,0.01); }
        .analysis-table tr.total-row td {
            background: var(--bg-panel-2); font-weight: 700;
            color: var(--text-primary); border-top: 1px solid var(--border-hi);
        }
        .analysis-table td.tk-cell {
            color: var(--accent); font-weight: 600;
            background: rgba(59,130,246,0.06) !important;
        }
        .analysis-table td.tk-cell-total {
            color: #93c5fd; font-weight: 700;
            background: rgba(59,130,246,0.15) !important;
        }
    </style>
</head>
<body>
    <!-- Mode Toggle -->
    <div class="mode-toggle">
        <button class="mode-btn active" onclick="switchMode('leje')">Lejeboliger</button>
        <button class="mode-btn" onclick="switchMode('ejer')">Ejerboliger</button>
        <div class="mode-divider"></div>
        <button class="mode-btn" id="map-toggle-btn" style="color:var(--text-secondary);">Satellit</button>
    </div>

    <!-- Turnkey toggle knap -->
    <button id="turnkey-toggle" onclick="toggleTurnkeyPanel()">Turnkey</button>

    <!-- Turnkey flydende panel -->
    <div id="turnkey-panel" style="display:none; flex-direction:row; gap:16px; align-items:flex-end;">
        <div class="tk-field">
            <span class="tk-label">OPEX (kr/m²/år)</span>
            <input id="tk-opex" type="number" value="350" min="0" step="10" oninput="updateTurnkey()">
        </div>
        <div class="tk-field">
            <span class="tk-label">AFKASTKRAV (%)</span>
            <input id="tk-yield" type="number" value="4" min="0.1" max="20" step="0.1" oninput="updateTurnkey()">
        </div>
        <div class="tk-result">
            <div class="tk-result-label">Gns. Turnkey/m²</div>
            <div class="tk-result-value" id="tk-kpi">-</div>
            <div class="tk-result-unit">kr/m²</div>
        </div>
    </div>
    
    <div id="map"></div>
    
    <!-- BI Boxes -->
    <div class="bi-boxes">
        <div class="bi-box">
            <div class="bi-box-title" id="kpi-title">Nøgletal</div>
            <div class="kpi-compact" id="kpi-content"></div>
        </div>
        
        <div class="bi-box">
            <div class="bi-box-title">Værelser</div>
            <canvas id="roomChart"></canvas>
        </div>
        
        <div class="bi-box">
            <div class="bi-box-title">Byer</div>
            <canvas id="byChart"></canvas>
        </div>
        
        <div class="bi-box">
            <div class="bi-box-title">Filtre</div>
            <div id="filter-content"></div>
        </div>
    </div>
    
    
    <!-- Year Range Slider -->
    <div id="sliders-wrapper" style="display: none; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; flex-direction: column; gap: 10px; align-items: center;">
    <div id="dato-slider-container" style="display: none; background: var(--bg-panel); border: 1px solid var(--border-hi); padding: 15px 25px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.12); min-width: 400px;">
        <div style="font-weight: 700; font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; text-align: center;">
            <span id="dato-slider-label">DATO</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="flex: 1;">
                <input type="range" id="dato-slider-min" style="width: 100%; margin: 6px 0;">
                <input type="range" id="dato-slider-max" style="width: 100%; margin: 6px 0;">
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; font-weight: 600;">
            <span style="color:var(--text-muted); font-size:10px;">Fra: </span><span id="dato-value-min" style="color:var(--accent);">-</span>
            <span style="color:var(--text-muted); font-size:10px;">Til: </span><span id="dato-value-max" style="color:var(--accent);">-</span>
        </div>
    </div>
    <div id="year-slider-container" style="display: none; background: var(--bg-panel); border: 1px solid var(--border-hi); padding: 15px 25px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.12); min-width: 400px;">
        <div style="font-weight: 700; font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; text-align: center;">
            OPFØRELSESÅR
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span id="year-min" style="font-size: 11px; color: var(--text-secondary); min-width: 40px;">2000</span>
            <div style="flex: 1; position: relative;">
                <input type="range" id="year-slider-min" style="width: 100%; position: absolute; pointer-events: none; height: 4px; background: transparent; -webkit-appearance: none;">
                <input type="range" id="year-slider-max" style="width: 100%; position: absolute; pointer-events: none; height: 4px; background: transparent; -webkit-appearance: none;">
                <div style="height: 4px; background: var(--bg-panel-3); border-radius: 2px; position: relative; margin: 8px 0;">
                    <div id="year-range-fill" style="position: absolute; height: 100%; background: var(--accent); border-radius: 2px;"></div>
                </div>
            </div>
            <span id="year-max" style="font-size: 11px; color: var(--text-secondary); min-width: 40px; text-align: right;">2025</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px; font-weight: 600;">
            <span><span style="color:var(--text-muted); font-size:10px;">Fra: </span><span id="year-value-min" style="color:var(--accent);">2000</span></span>
            <span><span style="color:var(--text-muted); font-size:10px;">Til: </span><span id="year-value-max" style="color:var(--accent);">2025</span></span>
        </div>
    </div>
    </div>
    
    <!-- Thumbnails -->
    <div class="thumbnails">
        <div class="thumbnail" onclick="openOverlay('overlay1')">
            <img id="thumb1" src="" alt="Scatter Plot">
        </div>
        <div class="thumbnail" onclick="openOverlay('overlay2')">
            <img id="thumb2" src="" alt="Heatmap">
        </div>
        <div class="thumbnail" onclick="openOverlay('overlay3')">
            <img id="thumb3" src="" alt="Tabel">
        </div>
    </div>
    
    <!-- Overlays -->
    <!-- Skjulte render-divs til thumbnail generering -->
    <div id="thumb-render-1" style="position:fixed; left:-9999px; top:0; width:450px; height:300px; visibility:hidden;"></div>
    <div id="thumb-render-2" style="position:fixed; left:-9999px; top:0; width:450px; height:300px; visibility:hidden;"></div>

    <div id="overlay1" class="overlay" onclick="closeOverlay('overlay1')">
        <span class="close" onclick="closeOverlay('overlay1')">&times;</span>
        <div class="overlay-inner" onclick="event.stopPropagation()">
            <div class="overlay-filters" id="overlay-filters-1"></div>
            <div class="overlay-chart">
                <div class="overlay-chart-inner">
                    <div id="scatter-plot" style="width:100%; height:100%;"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="overlay2" class="overlay" onclick="closeOverlay('overlay2')">
        <span class="close" onclick="closeOverlay('overlay2')">&times;</span>
        <div class="overlay-inner" onclick="event.stopPropagation()">
            <div class="overlay-filters" id="overlay-filters-2"></div>
            <div class="overlay-chart">
                <div class="overlay-chart-inner">
                    <div id="heatmap-plot" style="width:100%; height:100%;"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="overlay3" class="overlay" onclick="closeOverlay('overlay3')">
        <span class="close" onclick="closeOverlay('overlay3')">&times;</span>
        <div class="overlay-inner" onclick="event.stopPropagation()">
            <div class="overlay-filters" id="overlay-filters-3"></div>
            <div class="overlay-chart">
                <div class="overlay-chart-inner">
                    <div id="table-plot" style="width:100%; height:100%; padding: 20px;"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var lejeData = __LEJE_DATA__;
        var ejerData = __EJER_DATA__;
        
        var currentMode = 'leje';
        var allBoliger = lejeData.boliger;
        var markers = [];
        var map;
        var roomChart;
        var byChart;
        var legend;
        var selectedFilters = {
            varelser: [],
            by: [],
            aarMin: null,
            aarMax: null,
            datoMin: null,
            datoMax: null,
            type: []
        };
        
        function createScatterPlot(filtered) {
            var mode = currentMode;
            var colors = {2: '#f39c12', 3: '#e74c3c', 4: '#3498db', 5: '#2ecc71', 6: '#9b59b6', 7: '#1abc9c'};
            
            // Grupper efter værelser
            var traces = [];
            var roomNumbers = [...new Set(filtered.map(b => b.varelser))].sort();
            
            roomNumbers.forEach(function(rooms) {
                var subset = filtered.filter(b => b.varelser === rooms);
                var trace = {
                    x: subset.map(b => mode === 'leje' ? b.leje_m2 : b.pris_m2),
                    y: subset.map(b => b.areal),
                    mode: 'markers',
                    type: 'scatter',
                    name: rooms + ' værelser',
                    marker: {
                        color: colors[rooms] || '#95a5a6',
                        size: 12,
                        line: { color: 'white', width: 0.5 }
                    },
                    text: subset.map(b => mode === 'leje' ? 
                        b.adresse + ', ' + b.by + '<br>Areal: ' + b.areal + ' m²<br>Leje/m²: ' + b.leje_m2 + ' kr.<br>Leje/md: ' + b.leje_maned.toLocaleString('da-DK') + ' kr.<br>Liggetid: ' + b.liggedage + ' dage' :
                        b.handelsnavn + '<br>Areal: ' + b.areal + ' m²<br>Pris: ' + b.pris.toLocaleString('da-DK') + ' kr.<br>Pris/m²: ' + b.pris_m2.toLocaleString('da-DK') + ' kr.<br>Dato: ' + b.handelsdato
                    ),
                    hovertemplate: '%{text}<extra></extra>'
                };
                traces.push(trace);
            });
            
            var layout = {
                paper_bgcolor: '#f0f2f5', plot_bgcolor: '#ffffff',
                font: { family: 'Inter, sans-serif', color: '#374151' },
                title: {
                    text: mode === 'leje' ? 
                        'Areal vs. Leje per m²  (n=' + filtered.length + ')' :
                        'Areal vs. Pris per m²  (n=' + filtered.length + ')',
                    font: { size: 16, color: '#1a1d23' }
                },
                xaxis: { title: mode === 'leje' ? 'Leje per m² (kr./m²)' : 'Pris per m² (kr./m²)', gridcolor: '#e5e7eb', zerolinecolor: '#d1d5db' },
                yaxis: { title: 'Areal (m²)', gridcolor: '#e5e7eb', zerolinecolor: '#d1d5db' },
                hovermode: 'closest',
                showlegend: true,
                legend: { x: 1, y: 1, xanchor: 'right', bgcolor: 'rgba(240,242,245,0.9)', bordercolor: '#d1d5db', borderwidth: 1 }
            };
            
            Plotly.newPlot('scatter-plot', traces, layout, {responsive: true});
        }
        
        function createHeatmap(filtered) {
            var mode = currentMode;
            
            // Kategoriser areal
            var categorized = filtered.map(function(b) {
                var category;
                if (b.areal < 50) category = '0-50 m²';
                else if (b.areal < 75) category = '50-75 m²';
                else if (b.areal < 100) category = '75-100 m²';
                else if (b.areal < 115) category = '100-115 m²';
                else if (b.areal < 130) category = '115-130 m²';
                else category = '130+ m²';
                
                return {
                    category: category,
                    varelser: b.varelser,
                    pris_m2: mode === 'leje' ? b.leje_m2 : b.pris_m2
                };
            });
            
            // Aggreger data
            var agg = {};
            categorized.forEach(function(item) {
                var key = item.category + '|' + item.varelser;
                if (!agg[key]) {
                    agg[key] = { sum: 0, count: 0, category: item.category, varelser: item.varelser };
                }
                agg[key].sum += item.pris_m2;
                agg[key].count++;
            });
            
            // Byg matrix
            var categories = ['0-50 m²', '50-75 m²', '75-100 m²', '100-115 m²', '115-130 m²', '130+ m²'];
            var roomNumbers = [...new Set(filtered.map(b => b.varelser))].sort();
            
            var zValues = [];
            var textValues = [];
            
            categories.forEach(function(cat) {
                var row = [];
                var textRow = [];
                roomNumbers.forEach(function(room) {
                    var key = cat + '|' + room;
                    if (agg[key]) {
                        var avg = Math.round(agg[key].sum / agg[key].count);
                        row.push(avg);
                        textRow.push(avg.toLocaleString('da-DK') + ' kr.<br>(n=' + agg[key].count + ')');
                    } else {
                        row.push(null);
                        textRow.push('');
                    }
                });
                zValues.push(row);
                textValues.push(textRow);
            });
            
            var data = [{
                z: zValues,
                x: roomNumbers.map(r => r + ' vær.'),
                y: categories,
                type: 'heatmap',
                colorscale: 'Blues',
                text: textValues,
                hovertemplate: '%{y}<br>%{x}<br>%{text}<extra></extra>',
                showscale: true,
                colorbar: { title: mode === 'leje' ? 'Leje/m² (kr.)' : 'Pris/m² (kr.)' }
            }];
            
            var layout = {
                paper_bgcolor: '#f0f2f5', plot_bgcolor: '#f0f2f5',
                font: { family: 'Inter, sans-serif', color: '#374151' },
                title: {
                    text: mode === 'leje' ?
                        'Gennemsnitlig leje/m² efter areal og værelser' :
                        'Gennemsnitlig pris/m² efter areal og værelser',
                    font: { size: 16, color: '#1a1d23' }
                },
                xaxis: { title: 'Antal værelser', side: 'bottom' },
                yaxis: { title: 'Areal kategori' },
                annotations: []
            };
            
            for (var i = 0; i < categories.length; i++) {
                for (var j = 0; j < roomNumbers.length; j++) {
                    if (zValues[i][j] !== null) {
                        layout.annotations.push({
                            x: roomNumbers[j] + ' vær.',
                            y: categories[i],
                            text: textValues[i][j].replace('<br>', '\\n'),
                            showarrow: false,
                            font: { size: 11, color: '#1a1d23', family: 'Inter, sans-serif' }
                        });
                    }
                }
            }
            
            Plotly.newPlot('heatmap-plot', data, layout, {responsive: true});
        }
        
        function createTable(filtered) {
            var mode = currentMode;

            // Hent turnkey parametre FØR loopen der bruger dem
            var tkOpex = parseFloat(document.getElementById('tk-opex').value) || 0;
            var tkYld  = parseFloat(document.getElementById('tk-yield').value) || 4;
            
            // Kategoriser og aggreger
            var categorized = {};
            filtered.forEach(function(b) {
                var category;
                if (b.areal < 50) category = '0-50 m²';
                else if (b.areal < 75) category = '50-75 m²';
                else if (b.areal < 100) category = '75-100 m²';
                else if (b.areal < 115) category = '100-115 m²';
                else if (b.areal < 130) category = '115-130 m²';
                else category = '130+ m²';
                
                if (!categorized[category]) {
                    categorized[category] = {
                        count: 0,
                        areal_sum: 0,
                        pris_m2_sum: 0,
                        pris_total_sum: 0,
                        varelser_sum: 0,
                        liggedage_sum: 0,
                        turnkey_sum: 0
                    };
                }
                
                var cat = categorized[category];
                cat.count++;
                cat.areal_sum += b.areal;
                cat.pris_m2_sum += (mode === 'leje' ? b.leje_m2 : b.pris_m2);
                cat.pris_total_sum += (mode === 'leje' ? b.leje_maned : b.pris);
                cat.varelser_sum += b.varelser;
                if (mode === 'leje') {
                    cat.liggedage_sum += b.liggedage || 0;
                    if (b.leje_m2 && b.leje_m2 > 0) {
                        cat.turnkey_sum += calcTurnkey(b.leje_m2, tkOpex, tkYld);
                        cat.turnkey_count = (cat.turnkey_count || 0) + 1;
                    }
                }
            });
            
            // Byg tabel HTML med CSS-klasser
            var html = '<table class="analysis-table">';
            html += '<tr>';
            html += '<th>Areal</th>';
            html += '<th>Antal ' + (mode === 'leje' ? 'lejepunkter' : 'salgspunkter') + '</th>';
            html += '<th>' + (mode === 'leje' ? 'Leje pr. m²' : 'Pris pr. m²') + '</th>';
            html += '<th>' + (mode === 'leje' ? 'Leje pr. måned' : 'Pris') + '</th>';
            html += '<th>Antal værelser</th>';
            if (mode === 'leje') {
                html += '<th>Liggetid (dage)</th>';
                html += '<th class="tk-col">Turnkey pr. m²</th>';
            }
            html += '</tr>';

            var categories = ['0-50 m²', '50-75 m²', '75-100 m²', '100-115 m²', '115-130 m²', '130+ m²'];
            var rowIndex = 0;
            categories.forEach(function(cat) {
                if (categorized[cat]) {
                    var data = categorized[cat];
                    var rowClass = rowIndex % 2 === 0 ? 'row-even' : 'row-odd';
                    html += '<tr class="' + rowClass + '">';
                    html += '<td>' + cat + '</td>';
                    html += '<td>' + data.count + '</td>';
                    html += '<td>' + Math.round(data.pris_m2_sum / data.count).toLocaleString('da-DK') + ' kr.</td>';
                    html += '<td>' + Math.round(data.pris_total_sum / data.count).toLocaleString('da-DK') + ' kr.</td>';
                    html += '<td>' + (data.varelser_sum / data.count).toFixed(1) + '</td>';
                    if (mode === 'leje') {
                        html += '<td>' + Math.round(data.liggedage_sum / data.count) + '</td>';
                        var tkCount = data.turnkey_count || 0;
                        var tkVal = tkCount > 0 ? Math.round(data.turnkey_sum / tkCount).toLocaleString('da-DK') + ' kr.' : '-';
                        html += '<td class="tk-cell">' + tkVal + '</td>';
                    }
                    html += '</tr>';
                    rowIndex++;
                }
            });

            // Total række
            html += '<tr class="total-row">';
            html += '<td>Gennemsnit</td>';
            html += '<td>' + filtered.length + '</td>';
            var avgPrisM2 = Math.round(filtered.reduce((s, b) => s + (mode === 'leje' ? b.leje_m2 : b.pris_m2), 0) / filtered.length);
            var avgPrisTotal = Math.round(filtered.reduce((s, b) => s + (mode === 'leje' ? b.leje_maned : b.pris), 0) / filtered.length);
            var avgVarelser = (filtered.reduce((s, b) => s + b.varelser, 0) / filtered.length).toFixed(1);
            html += '<td>' + avgPrisM2.toLocaleString('da-DK') + ' kr.</td>';
            html += '<td>' + avgPrisTotal.toLocaleString('da-DK') + ' kr.</td>';
            html += '<td>' + avgVarelser + '</td>';
            if (mode === 'leje') {
                var validForLiggedage = filtered.filter(b => b.liggedage);
                var avgLiggedage = validForLiggedage.length > 0 ? Math.round(validForLiggedage.reduce((s, b) => s + b.liggedage, 0) / validForLiggedage.length) : '-';
                html += '<td>' + avgLiggedage + '</td>';
                var validForTk = filtered.filter(b => b.leje_m2 && b.leje_m2 > 0);
                var avgTurnkey = validForTk.length > 0 ? Math.round(validForTk.reduce((s, b) => s + calcTurnkey(b.leje_m2, tkOpex, tkYld), 0) / validForTk.length) : null;
                var avgTkDisplay = avgTurnkey !== null ? avgTurnkey.toLocaleString('da-DK') + ' kr.' : '-';
                html += '<td class="tk-cell-total">' + avgTkDisplay + '</td>';
                if (avgTurnkey !== null) document.getElementById('tk-kpi').textContent = avgTurnkey.toLocaleString('da-DK');
            }
            html += '</tr>';
            html += '</table>';

            document.getElementById('table-plot').innerHTML = html;
        }
        
        function updateInteractiveCharts() {
            var filtered = applyFilters(allBoliger);
            createScatterPlot(filtered);
            createHeatmap(filtered);
            createTable(filtered);
            // Render thumbnail-versioner i skjulte divs
            setTimeout(function() {
                renderThumbScatter(filtered);
                renderThumbHeatmap(filtered);
                // Tabel-thumbnail: brug statisk billede
                var d = currentMode === 'leje' ? lejeData : ejerData;
                document.getElementById('thumb3').src = d.table_img;
            }, 100);
        }

        function getThumbLayout(title) {
            return {
                paper_bgcolor: '#f0f2f5', plot_bgcolor: '#ffffff',
                margin: {t: 36, r: 12, b: 40, l: 48},
                font: {family: 'Inter, sans-serif', size: 10, color: '#374151'},
                title: {text: title, font: {size: 12, color: '#1a1d23'}, x: 0.5},
                showlegend: false
            };
        }

        function renderThumbScatter(filtered) {
            var mode = currentMode;
            var colors = {2:'#f59e0b',3:'#ef4444',4:'#3b82f6',5:'#10b981',6:'#8b5cf6',7:'#06b6d4'};
            var traces = [];
            var rooms = [...new Set(filtered.map(b=>b.varelser))].sort();
            rooms.forEach(function(r) {
                var sub = filtered.filter(b=>b.varelser===r);
                traces.push({
                    x: sub.map(b=>mode==='leje'?b.leje_m2:b.pris_m2),
                    y: sub.map(b=>b.areal),
                    mode:'markers', type:'scatter', name:r+' vær.',
                    marker:{color:colors[r]||'#9ca3af', size:6, opacity:0.75}
                });
            });
            var layout = Object.assign(getThumbLayout(mode==='leje'?'Areal vs. Leje/m²':'Areal vs. Pris/m²'), {
                xaxis:{title:{text:mode==='leje'?'Leje/m²':'Pris/m²',font:{size:9}}, gridcolor:'#e5e7eb'},
                yaxis:{title:{text:'Areal (m²)',font:{size:9}}, gridcolor:'#e5e7eb'}
            });
            Plotly.newPlot('thumb-render-1', traces, layout, {staticPlot:true, responsive:false})
                .then(function() {
                    return Plotly.toImage('thumb-render-1', {format:'png', width:450, height:300});
                }).then(function(url) {
                    document.getElementById('thumb1').src = url;
                });
        }

        function renderThumbHeatmap(filtered) {
            var mode = currentMode;
            var priceKey = mode==='leje'?'leje_m2':'pris_m2';
            var cats = ['0-50 m²','50-75 m²','75-100 m²','100-115 m²','115-130 m²','130+ m²'];
            var rooms = [...new Set(filtered.map(b=>b.varelser))].sort();
            var zData = [], yLabels = [];
            cats.forEach(function(cat) {
                var row = rooms.map(function(r) {
                    var sub = filtered.filter(b=>b.varelser===r && arealCat(b.areal)===cat);
                    return sub.length > 0 ? Math.round(sub.reduce((s,b)=>s+b[priceKey],0)/sub.length) : null;
                });
                if (row.some(v=>v!==null)) { zData.push(row); yLabels.push(cat); }
            });
            var layout = Object.assign(getThumbLayout(mode==='leje'?'Leje/m² matrix':'Pris/m² matrix'), {
                xaxis:{tickvals:rooms.map((_,i)=>i), ticktext:rooms.map(r=>r+'vær.'), tickfont:{size:8}},
                yaxis:{tickfont:{size:8}}
            });
            Plotly.newPlot('thumb-render-2', [{
                z:zData, x:rooms.map(r=>r+' vær.'), y:yLabels,
                type:'heatmap', colorscale:'Blues', showscale:false,
                text:zData, texttemplate:'%{z}', textfont:{size:9, color:'#1a1d23'}
            }], layout, {staticPlot:true, responsive:false})
                .then(function() {
                    return Plotly.toImage('thumb-render-2', {format:'png', width:450, height:300});
                }).then(function(url) {
                    document.getElementById('thumb2').src = url;
                });
        }

        function arealCat(a) {
            if (a < 50)  return '0-50 m²';
            if (a < 75)  return '50-75 m²';
            if (a < 100) return '75-100 m²';
            if (a < 115) return '100-115 m²';
            if (a < 130) return '115-130 m²';
            return '130+ m²';
        }

        function updateThumbnails() {
            updateInteractiveCharts();
        }
        
        // ── Turnkey beregning ──────────────────────────────────────────
        function calcTurnkey(lejeM2, opex, yieldPct) {
            return Math.round((lejeM2 - opex) / (yieldPct / 100));
        }

        function toggleTurnkeyPanel() {
            var panel = document.getElementById('turnkey-panel');
            var btn = document.getElementById('turnkey-toggle');
            var isOpen = panel.style.display === 'flex';
            panel.style.display = isOpen ? 'none' : 'flex';
            btn.classList.toggle('open', !isOpen);
        }

        function updateTurnkey() {
            if (currentMode !== 'leje') return;
            var opex  = parseFloat(document.getElementById('tk-opex').value)  || 0;
            var yld   = parseFloat(document.getElementById('tk-yield').value) || 4;
            var filtered = applyFilters(allBoliger);
            if (filtered.length === 0) return;

            var avgTkM2 = Math.round(
                filtered.reduce((s, b) => s + calcTurnkey(b.leje_m2, opex, yld), 0) / filtered.length
            );
            document.getElementById('tk-kpi').textContent = avgTkM2.toLocaleString('da-DK');

            // Opdater popup og tabel med ny beregning
            updateMap(filtered);
            createTable(filtered);
        }

        function switchMode(mode) {
            currentMode = mode;
            allBoliger = mode === 'leje' ? lejeData.boliger : ejerData.boliger;
            
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');

            // Vis/skjul turnkey knap og luk panel ved mode-skift
            var tkToggle = document.getElementById('turnkey-toggle');
            var tkPanel  = document.getElementById('turnkey-panel');
            tkToggle.style.display = mode === 'leje' ? 'block' : 'none';
            tkPanel.style.display  = 'none';
            tkToggle.classList.remove('open');
            
            var data = mode === 'leje' ? lejeData : ejerData;
            map.setView([data.center_lat, data.center_lng], 13);
            
            initializeFilters(data);
            updateKPIContent();
            updateFilterContent();
            updateDisplay();
            updateThumbnails();
        }
        
        function initializeFilters(data) {
            var vaerelser = [...new Set(data.boliger.map(b => b.varelser))].sort((a,b) => a-b);
            selectedFilters.varelser = vaerelser;
            var byer = [...new Set(data.boliger.map(b => b.by))].sort();
            selectedFilters.by = byer;
            var aar = [...new Set(data.boliger.map(b => b.opfoerelsesaar).filter(y => y !== null))].sort((a,b) => a-b);
            if (aar.length > 0) {
                selectedFilters.aarMin = Math.min(...aar);
                selectedFilters.aarMax = Math.max(...aar);
            }
            var typer = [...new Set(data.boliger.map(b => currentMode === 'leje' ? b.boligtype : b.anvendelse))].sort();
            selectedFilters.type = typer;
            // Dato filter
            var datoer = data.boliger.map(b => b.dato_ts).filter(d => d !== null && d !== undefined);
            if (datoer.length > 0) {
                selectedFilters.datoMin = Math.min(...datoer);
                selectedFilters.datoMax = Math.max(...datoer);
            } else {
                selectedFilters.datoMin = null;
                selectedFilters.datoMax = null;
            }
        }
        
        function updateKPIContent() {
            var data = currentMode === 'leje' ? lejeData : ejerData;
            
            if (currentMode === 'leje') {
                document.getElementById('kpi-content').innerHTML = `
                    <div class="kpi-item full">
                        <div class="kpi-value-small" id="kpi-total">${data.total_boliger}</div>
                        <div class="kpi-label-small">BOLIGER</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-pris">${data.gns_leje_m2.toLocaleString('da-DK')}</div>
                        <div class="kpi-label-small">GNS. LEJE/M2</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-areal">${data.gns_areal}</div>
                        <div class="kpi-label-small">GNS. AREAL</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-extra">${Math.round(data.gns_leje/1000)}K</div>
                        <div class="kpi-label-small">GNS. LEJE/MD</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-median">${Math.round(data.median_leje/1000)}K</div>
                        <div class="kpi-label-small">MEDIAN LEJE/MD</div>
                    </div>
                `;
            } else {
                document.getElementById('kpi-content').innerHTML = `
                    <div class="kpi-item full">
                        <div class="kpi-value-small" id="kpi-total">${data.total_boliger}</div>
                        <div class="kpi-label-small">BOLIGER</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-pris">${data.gns_pris_m2.toLocaleString('da-DK')}</div>
                        <div class="kpi-label-small">GNS. PRIS/M2</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-areal">${data.gns_areal}</div>
                        <div class="kpi-label-small">GNS. AREAL</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-extra">${Math.round(data.gns_pris/1000000)}M</div>
                        <div class="kpi-label-small">GNS. PRIS</div>
                    </div>
                    <div class="kpi-item">
                        <div class="kpi-value-small" id="kpi-median">${Math.round(data.median_pris/1000000)}M</div>
                        <div class="kpi-label-small">MEDIAN PRIS</div>
                    </div>
                `;
            }
        }
        
        function updateFilterContent() {
            var data = currentMode === 'leje' ? lejeData : ejerData;
            var vaerelser = [...new Set(data.boliger.map(b => b.varelser))].sort((a,b) => a-b);
            var byer = [...new Set(data.boliger.map(b => b.by))].sort();
            
            // Nye filtre
            var aar = [...new Set(data.boliger.map(b => b.opfoerelsesaar).filter(y => y !== null))].sort((a,b) => a-b);
            var typer = [...new Set(data.boliger.map(b => currentMode === 'leje' ? b.boligtype : b.anvendelse))].sort();
            
            var html = `
                <div class="filter-group">
                    <div class="filter-label">Værelser</div>
                    <div class="filter-options">
                        ${vaerelser.map(v => `
                            <button class="filter-btn ${selectedFilters.varelser.includes(v) ? 'active' : ''}" 
                                    onclick="toggleFilter('varelser', ${v})">${v}</button>
                        `).join('')}
                    </div>
                </div>
                <div class="filter-group">
                    <div class="filter-label">By</div>
                    <div class="filter-options">
                        ${byer.map(b => `
                            <button class="filter-btn ${selectedFilters.by.includes(b) ? 'active' : ''}" 
                                    onclick="toggleFilter('by', '${b}')">${b}</button>
                        `).join('')}
                    </div>
                </div>`;
            
            // Tilføj Boligtype/Anvendelse filter
            if (typer.length > 0 && typer.length < 10) {
                var typeLabel = currentMode === 'leje' ? 'Boligtype' : 'Anvendelse';
                html += `
                <div class="filter-group">
                    <div class="filter-label">${typeLabel}</div>
                    <div class="filter-options">
                        ${typer.map(t => `
                            <button class="filter-btn ${selectedFilters.type.includes(t) ? 'active' : ''}" 
                                    onclick="toggleFilter('type', '${t}')">${t.length > 20 ? t.substring(0, 18) + '...' : t}</button>
                        `).join('')}
                    </div>
                </div>`;
            }
            
            html += `<button class="reset-btn" onclick="resetFilters()">NULSTIL FILTRE</button>`;
            
            document.getElementById('filter-content').innerHTML = html;
            
            // Opdater år-slider hvis data findes
            if (aar.length > 0) {
                var minYear = Math.min(...aar);
                var maxYear = Math.max(...aar);
                selectedFilters.aarMin = selectedFilters.aarMin || minYear;
                selectedFilters.aarMax = selectedFilters.aarMax || maxYear;
                
                document.getElementById('year-slider-container').style.display = 'block';
                document.getElementById('year-min').textContent = minYear;
                document.getElementById('year-max').textContent = maxYear;
                document.getElementById('year-slider-min').min = minYear;
                document.getElementById('year-slider-min').max = maxYear;
                document.getElementById('year-slider-min').value = selectedFilters.aarMin;
                document.getElementById('year-slider-max').min = minYear;
                document.getElementById('year-slider-max').max = maxYear;
                document.getElementById('year-slider-max').value = selectedFilters.aarMax;
                document.getElementById('year-value-min').textContent = selectedFilters.aarMin;
                document.getElementById('year-value-max').textContent = selectedFilters.aarMax;
            } else {
                document.getElementById('year-slider-container').style.display = 'none';
            }

            // Opdater dato-slider
            var datoer = data.boliger.map(b => b.dato_ts).filter(d => d !== null && d !== undefined);
            if (datoer.length > 0) {
                var minTs = Math.min(...datoer);
                var maxTs = Math.max(...datoer);
                selectedFilters.datoMin = selectedFilters.datoMin !== null ? selectedFilters.datoMin : minTs;
                selectedFilters.datoMax = selectedFilters.datoMax !== null ? selectedFilters.datoMax : maxTs;

                document.getElementById('dato-slider-container').style.display = 'block';
                document.getElementById('dato-slider-label').textContent = currentMode === 'leje' ? 'UDLEJNINGSDATO' : 'HANDELSDATO';
                document.getElementById('dato-slider-min').min = minTs;
                document.getElementById('dato-slider-min').max = maxTs;
                document.getElementById('dato-slider-min').value = selectedFilters.datoMin;
                document.getElementById('dato-slider-max').min = minTs;
                document.getElementById('dato-slider-max').max = maxTs;
                document.getElementById('dato-slider-max').value = selectedFilters.datoMax;
                document.getElementById('dato-value-min').textContent = tsToLabel(selectedFilters.datoMin);
                document.getElementById('dato-value-max').textContent = tsToLabel(selectedFilters.datoMax);
            } else {
                document.getElementById('dato-slider-container').style.display = 'none';
            }

            // Vis/skjul wrapper
            var anySlider = document.getElementById('year-slider-container').style.display === 'block' ||
                            document.getElementById('dato-slider-container').style.display === 'block';
            document.getElementById('sliders-wrapper').style.display = anySlider ? 'flex' : 'none';
        }

        function tsToLabel(ts) {
            var d = new Date(ts * 1000);
            return d.toLocaleDateString('da-DK', { month: 'short', year: 'numeric' });
        }
        
        function toggleFilter(type, value) {
            var index = selectedFilters[type].indexOf(value);
            if (index > -1) {
                selectedFilters[type].splice(index, 1);
            } else {
                selectedFilters[type].push(value);
            }
            updateFilterContent();
            updateDisplay();
            // Opdater overlay-filtre hvis et overlay er åbent
            for (var i = 1; i <= 3; i++) {
                var overlay = document.getElementById('overlay' + i);
                if (overlay && overlay.style.display === 'block') {
                    renderOverlayFilters(i);
                }
            }
        }
        
        function resetFilters() {
            var data = currentMode === 'leje' ? lejeData : ejerData;
            initializeFilters(data);  // Aktivér alle filtre igen
            updateFilterContent();
            updateDisplay();
        }
        
        function applyFilters(boliger) {
            return boliger.filter(function(bolig) {
                var varelserMatch = selectedFilters.varelser.includes(bolig.varelser);
                var byMatch = selectedFilters.by.includes(bolig.by);
                var aarMatch = bolig.opfoerelsesaar === null ||
                              (selectedFilters.aarMin === null || bolig.opfoerelsesaar >= selectedFilters.aarMin) &&
                              (selectedFilters.aarMax === null || bolig.opfoerelsesaar <= selectedFilters.aarMax);
                var typeValue = currentMode === 'leje' ? bolig.boligtype : bolig.anvendelse;
                var typeMatch = selectedFilters.type.length === 0 || selectedFilters.type.includes(typeValue);
                var datoMatch = bolig.dato_ts === null || bolig.dato_ts === undefined ||
                               (selectedFilters.datoMin === null || bolig.dato_ts >= selectedFilters.datoMin) &&
                               (selectedFilters.datoMax === null || bolig.dato_ts <= selectedFilters.datoMax);
                return varelserMatch && byMatch && aarMatch && typeMatch && datoMatch;
            });
        }

        function updateDisplay() {
            var filtered = applyFilters(allBoliger);
            updateKPIs(filtered);
            updateMap(filtered);
            updateCharts(filtered);
            updateInteractiveCharts();
            if (currentMode === 'leje') updateTurnkey();
        }
        
        function updateKPIs(filtered) {
            var totalBoliger = filtered.length;
            
            if (totalBoliger === 0) {
                document.getElementById('kpi-total').textContent = '0';
                document.getElementById('kpi-pris').textContent = '0';
                document.getElementById('kpi-areal').textContent = '0';
                document.getElementById('kpi-extra').textContent = '0';
                document.getElementById('kpi-median').textContent = '0';
                return;
            }
            
            if (currentMode === 'leje') {
                var gnsLejeM2 = Math.round(filtered.reduce((s, b) => s + b.leje_m2, 0) / totalBoliger);
                var gnsAreal = Math.round(filtered.reduce((s, b) => s + b.areal, 0) / totalBoliger);
                var gnsLeje = Math.round(filtered.reduce((s, b) => s + b.leje_maned, 0) / totalBoliger / 1000);
                var sortedPrices = filtered.map(b => b.leje_maned).sort((a,b) => a-b);
                var median = Math.round(sortedPrices[Math.floor(sortedPrices.length/2)] / 1000);
                
                document.getElementById('kpi-total').textContent = totalBoliger;
                document.getElementById('kpi-pris').textContent = gnsLejeM2.toLocaleString('da-DK');
                document.getElementById('kpi-areal').textContent = gnsAreal;
                document.getElementById('kpi-extra').textContent = gnsLeje + 'K';
                document.getElementById('kpi-median').textContent = median + 'K';
            } else {
                var gnsPrisM2 = Math.round(filtered.reduce((s, b) => s + b.pris_m2, 0) / totalBoliger);
                var gnsAreal = Math.round(filtered.reduce((s, b) => s + b.areal, 0) / totalBoliger);
                var gnsPris = Math.round(filtered.reduce((s, b) => s + b.pris, 0) / totalBoliger / 1000000);
                var sortedPrices = filtered.map(b => b.pris).sort((a,b) => a-b);
                var median = Math.round(sortedPrices[Math.floor(sortedPrices.length/2)] / 1000000);
                
                document.getElementById('kpi-total').textContent = totalBoliger;
                document.getElementById('kpi-pris').textContent = gnsPrisM2.toLocaleString('da-DK');
                document.getElementById('kpi-areal').textContent = gnsAreal;
                document.getElementById('kpi-extra').textContent = gnsPris + 'M';
                document.getElementById('kpi-median').textContent = median + 'M';
            }
        }
        
        function updateMap(filtered) {
            markers.forEach(m => map.removeLayer(m));
            markers = [];
            
            var colors = {2: '#f39c12', 3: '#e74c3c', 4: '#3498db', 5: '#2ecc71', 6: '#9b59b6', 7: '#1abc9c'};
            
            if (filtered.length === 0) return;
            
            var prices = filtered.map(b => currentMode === 'leje' ? b.leje_m2 : b.pris_m2);
            var minPrice = Math.min(...prices);
            var maxPrice = Math.max(...prices);
            
            filtered.forEach(function(bolig) {
                var price = currentMode === 'leje' ? bolig.leje_m2 : bolig.pris_m2;
                var radius = 8 + ((price - minPrice) / (maxPrice - minPrice)) * 12;
                
                var circle = L.circleMarker([bolig.lat, bolig.lng], {
                    radius: radius,
                    fillColor: colors[bolig.varelser] || '#95a5a6',
                    color: '#000',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.7
                });
                
                var popupContent = currentMode === 'leje' 
                    ? `<div class="info-box">
                        <h3>${bolig.adresse}, ${bolig.by}</h3>
                        <p><strong>Areal:</strong> ${bolig.areal} m²</p>
                        <p><strong>Antal værelser:</strong> ${bolig.varelser}</p>
                        <p><strong>Leje pr. m²:</strong> ${bolig.leje_m2.toLocaleString('da-DK')} kr.</p>
                        <p><strong>Leje pr. måned:</strong> ${bolig.leje_maned.toLocaleString('da-DK')} kr.</p>
                        <p><strong>Liggetid:</strong> ${bolig.liggedage} dage</p>
                        ${(function() {
                            var opex = parseFloat(document.getElementById('tk-opex').value) || 0;
                            var yld  = parseFloat(document.getElementById('tk-yield').value) || 4;
                            var tkM2    = calcTurnkey(bolig.leje_m2, opex, yld);
                            var tkTotal = Math.round(tkM2 * bolig.areal);
                            return '<hr style="border:none;border-top:1px solid #e2e8f0;margin:8px 0;">'
                                 + '<p style="color:#3b82f6;font-weight:700;">Turnkey pr. m²: ' + tkM2.toLocaleString('da-DK') + ' kr.</p>'
                                 + '<p style="color:#3b82f6;font-weight:700;">Turnkey total: ' + tkTotal.toLocaleString('da-DK') + ' kr.</p>';
                        })()}
                    </div>`
                    : `<div class="info-box">
                        <h3>${bolig.handelsnavn}</h3>
                        <p><strong>By:</strong> ${bolig.by}</p>
                        <p><strong>Areal:</strong> ${bolig.areal} m2</p>
                        <p><strong>Antal værelser:</strong> ${bolig.varelser}</p>
                        <p><strong>Salgspris:</strong> ${bolig.pris.toLocaleString('da-DK')} kr.</p>
                        <p><strong>Pris pr. m2:</strong> ${bolig.pris_m2.toLocaleString('da-DK')} kr.</p>
                        <p><strong>Handelsdato:</strong> ${bolig.handelsdato}</p>
                    </div>`;
                
                circle.bindPopup(popupContent);
                circle.addTo(map);
                markers.push(circle);
            });
        }
        
        function updateCharts(filtered) {
            var vaerelseCounts = {};
            filtered.forEach(b => {
                vaerelseCounts[b.varelser] = (vaerelseCounts[b.varelser] || 0) + 1;
            });
            var vaerelsesData = Object.keys(vaerelseCounts).sort().map(k => ({
                varelser: parseInt(k),
                antal: vaerelseCounts[k]
            }));
            
            var byCounts = {};
            filtered.forEach(b => {
                byCounts[b.by] = (byCounts[b.by] || 0) + 1;
            });
            var byData = Object.keys(byCounts).map(k => ({
                by: k,
                antal: byCounts[k]
            }));
            
            var chartColors = {2: '#f39c12', 3: '#e74c3c', 4: '#3498db', 5: '#2ecc71', 6: '#9b59b6', 7: '#1abc9c'};
            var bgColors = vaerelsesData.map(d => chartColors[d.varelser] || '#95a5a6');
            
            roomChart.data.labels = vaerelsesData.map(d => d.varelser + ' vær.');
            roomChart.data.datasets[0].data = vaerelsesData.map(d => d.antal);
            roomChart.data.datasets[0].backgroundColor = bgColors;
            roomChart.update();
            
            byChart.data.labels = byData.map(d => d.by);
            byChart.data.datasets[0].data = byData.map(d => d.antal);
            byChart.update();
        }
        
        // Wrapper funktioner - undgår quote-kollision i onclick attributter
        function ovToggleV(v, num)  { toggleFilter('varelser', v);              renderOverlayFilters(num); }
        function ovToggleB(i, num)  { toggleFilter('by', window._ovByer[i]);    renderOverlayFilters(num); }
        function ovToggleT(i, num)  { toggleFilter('type', window._ovTyper[i]); renderOverlayFilters(num); }
        function ovReset(num)       { resetFilters();                            renderOverlayFilters(num); }
        function ovYearMin(v, num)  { updateYearFromOverlay(v, 'min', num); }
        function ovYearMax(v, num)  { updateYearFromOverlay(v, 'max', num); }

        function renderOverlayFilters(num) {
            var container = document.getElementById('overlay-filters-' + num);
            if (!container) return;
            
            var data = currentMode === 'leje' ? lejeData : ejerData;
            if (!data || !data.boliger || data.boliger.length === 0) {
                container.innerHTML = '<div style="color:#999;font-size:11px;padding:10px;">Ingen data</div>';
                return;
            }
            
            var vaerelser = [...new Set(data.boliger.map(b => b.varelser))].sort((a,b) => a-b);
            var byer      = [...new Set(data.boliger.map(b => b.by))].sort();
            var aar       = [...new Set(data.boliger.map(b => b.opfoerelsesaar).filter(y => y !== null))].sort((a,b) => a-b);
            var typer     = [...new Set(data.boliger.map(b => currentMode === 'leje' ? b.boligtype : b.anvendelse).filter(t => t && t !== 'None'))].sort();
            var typeLabel = currentMode === 'leje' ? 'Boligtype' : 'Anvendelse';

            // Gem i globale arrays saa wrapper-funktioner kan slaa dem op via index
            window._ovByer  = byer;
            window._ovTyper = typer;
            
            var btnActive   = 'background:#3b82f6;color:white;border:1px solid #3b82f6;';
            var btnInactive = 'background:#e4e7ec;color:#4b5563;border:1px solid rgba(0,0,0,0.08);';
            var btnBase     = 'padding:4px 10px;border-radius:6px;font-size:11px;font-family:inherit;cursor:pointer;';
            var labelStyle  = 'font-size:9px;color:#556070;margin-bottom:7px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;display:block;';
            var html = '<div style="font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#556070;margin-bottom:15px;">Filtre</div>';

            // Vaerelser
            html += '<div style="margin-bottom:12px;"><span style="' + labelStyle + '">Vaerelser</span><div style="display:flex;flex-wrap:wrap;gap:5px;">';
            vaerelser.forEach(function(v) {
                var st = selectedFilters.varelser.includes(v) ? btnActive : btnInactive;
                html += '<button style="' + btnBase + st + '" onclick="ovToggleV(' + v + ',' + num + ')">' + v + '</button>';
            });
            html += '</div></div>';

            // By
            html += '<div style="margin-bottom:12px;"><span style="' + labelStyle + '">By</span><div style="display:flex;flex-wrap:wrap;gap:5px;">';
            byer.forEach(function(b, i) {
                var st = selectedFilters.by.includes(b) ? btnActive : btnInactive;
                html += '<button style="' + btnBase + st + '" onclick="ovToggleB(' + i + ',' + num + ')">' + b + '</button>';
            });
            html += '</div></div>';

            // Type
            if (typer.length > 0 && typer.length < 10) {
                html += '<div style="margin-bottom:12px;"><span style="' + labelStyle + '">' + typeLabel + '</span><div style="display:flex;flex-wrap:wrap;gap:5px;">';
                typer.forEach(function(t, i) {
                    var st    = selectedFilters.type.includes(t) ? btnActive : btnInactive;
                    var label = t.length > 18 ? t.substring(0, 16) + '...' : t;
                    html += '<button style="' + btnBase + st + '" onclick="ovToggleT(' + i + ',' + num + ')" title="' + t + '">' + label + '</button>';
                });
                html += '</div></div>';
            }
            
            // Opfoerelsesaar
            if (aar.length > 0) {
                var minYear = Math.min(...aar);
                var maxYear = Math.max(...aar);
                var curMin  = selectedFilters.aarMin !== null ? selectedFilters.aarMin : minYear;
                var curMax  = selectedFilters.aarMax !== null ? selectedFilters.aarMax : maxYear;
                html += '<div style="margin-bottom:12px;"><div style="' + s + '">Opf. aar</div>';
                html += '<div style="font-size:11px;margin-bottom:2px;">Fra: <b><span id="ov-min-' + num + '">' + curMin + '</span></b></div>';
                html += '<input type="range" min="' + minYear + '" max="' + maxYear + '" value="' + curMin + '" style="width:100%;margin:2px 0;" oninput="ovYearMin(this.value,' + num + ')">';
                html += '<div style="font-size:11px;margin-bottom:2px;">Til: <b><span id="ov-max-' + num + '">' + curMax + '</span></b></div>';
                html += '<input type="range" min="' + minYear + '" max="' + maxYear + '" value="' + curMax + '" style="width:100%;margin:2px 0;" oninput="ovYearMax(this.value,' + num + ')">';
                html += '</div>';
            }
            
            html += '<button style="width:100%;background:transparent;color:#ef4444;border:1px solid rgba(239,68,68,0.35);padding:7px;border-radius:6px;cursor:pointer;font-size:10px;font-weight:600;font-family:inherit;letter-spacing:0.06em;text-transform:uppercase;margin-top:8px;" onclick="ovReset(' + num + ')">Nulstil filtre</button>';
            
            container.innerHTML = html;
        }
        
        function updateYearFromOverlay(val, type, num) {
            if (type === 'min') {
                selectedFilters.aarMin = parseInt(val);
                var el = document.getElementById('ov-min-' + num);
                if (el) el.textContent = val;
            } else {
                selectedFilters.aarMax = parseInt(val);
                var el = document.getElementById('ov-max-' + num);
                if (el) el.textContent = val;
            }
            // Sync med hoved-slideren
            var slider = document.getElementById('year-slider-' + type);
            if (slider) slider.value = val;
            updateDisplay();
            updateInteractiveCharts();
        }
        
        function openOverlay(overlayId) {
            var num = overlayId.replace('overlay', '');
            document.getElementById(overlayId).style.display = "flex";
            renderOverlayFilters(num);
            updateInteractiveCharts();
        }
        
        function closeOverlay(overlayId) {
            if (event.target.className === 'overlay' || event.target.className === 'close') {
                document.getElementById(overlayId).style.display = "none";
            }
        }
        
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                document.querySelectorAll('.overlay').forEach(o => o.style.display = 'none');
            }
        });
        
        // Initialiser kort
        map = L.map('map').setView([lejeData.center_lat, lejeData.center_lng], 13);
        
        var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        });
        
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '© Esri, Maxar, Earthstar Geographics',
            maxZoom: 19
        });
        
        var labelsLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
            attribution: '',
            maxZoom: 19,
            opacity: 0.8
        });
        
        osmLayer.addTo(map);
        
        var baseMaps = {
            'Kort': osmLayer,
            'Satellit': L.layerGroup([satelliteLayer, labelsLayer])
        };
        
        L.control.layers(baseMaps, null, { position: 'bottomright', collapsed: false }).addTo(map);
        
        // Skjul Leaflet's eget layer control - vi bruger vores egen knap
        document.querySelector('.leaflet-control-layers').style.display = 'none';
        
        var currentBaseLayer = osmLayer;
        window._baseMaps = baseMaps;
        window._currentBaseKey = 'Kort';
        
        document.getElementById('map-toggle-btn').addEventListener('click', function() {
            var keys = Object.keys(window._baseMaps);
            var nextKey = window._currentBaseKey === keys[0] ? keys[1] : keys[0];
            map.removeLayer(window._baseMaps[window._currentBaseKey]);
            map.addLayer(window._baseMaps[nextKey]);
            window._currentBaseKey = nextKey;
            this.textContent = nextKey === 'Kort' ? 'Satellit' : 'Kort';
        });
        
        // Initialiser charts
        roomChart = new Chart(document.getElementById('roomChart'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { 
                        position: 'bottom', 
                        labels: { 
                            padding: 5, 
                            font: { size: 9 },
                            boxWidth: 10
                        } 
                    }
                }
            }
        });
        
        byChart = new Chart(document.getElementById('byChart'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Antal',
                    data: [],
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { 
                    legend: { display: false }
                },
                scales: { 
                    y: { 
                        beginAtZero: true, 
                        ticks: { 
                            stepSize: 5,
                            font: { size: 9 }
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 9 }
                        }
                    }
                }
            }
        });
        
        legend = L.control({position: 'topleft'});
        legend.onAdd = function(map) {
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<h4 style="margin: 0 0 10px 0;">Antal værelser</h4>';
            div.innerHTML += '<div class="legend-item"><div class="legend-color" style="background: #f39c12;"></div><span>2 værelser</span></div>';
            div.innerHTML += '<div class="legend-item"><div class="legend-color" style="background: #e74c3c;"></div><span>3 værelser</span></div>';
            div.innerHTML += '<div class="legend-item"><div class="legend-color" style="background: #3498db;"></div><span>4 værelser</span></div>';
            div.innerHTML += '<div class="legend-item"><div class="legend-color" style="background: #2ecc71;"></div><span>5 værelser</span></div>';
            div.innerHTML += '<p style="margin-top: 10px; font-size: 11px; color: var(--text-muted);">Punkt-størrelse = Pris/m²</p>';
            return div;
        };
        legend.addTo(map);
        
        
        // Year slider handlers
        function updateYearSlider() {
            var minVal = parseInt(document.getElementById('year-slider-min').value);
            var maxVal = parseInt(document.getElementById('year-slider-max').value);
            
            // Ensure min is always less than max
            if (minVal > maxVal) {
                var tmp = minVal;
                minVal = maxVal;
                maxVal = tmp;
                document.getElementById('year-slider-min').value = minVal;
                document.getElementById('year-slider-max').value = maxVal;
            }
            
            selectedFilters.aarMin = minVal;
            selectedFilters.aarMax = maxVal;
            
            document.getElementById('year-value-min').textContent = minVal;
            document.getElementById('year-value-max').textContent = maxVal;
            
            // Update visual fill
            var minYear = parseInt(document.getElementById('year-slider-min').min);
            var maxYear = parseInt(document.getElementById('year-slider-min').max);
            var range = maxYear - minYear;
            var leftPercent = ((minVal - minYear) / range) * 100;
            var rightPercent = ((maxYear - maxVal) / range) * 100;
            
            var fill = document.getElementById('year-range-fill');
            fill.style.left = leftPercent + '%';
            fill.style.right = rightPercent + '%';
            
            updateDisplay();
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('year-slider-min').addEventListener('input', updateYearSlider);
            document.getElementById('year-slider-max').addEventListener('input', updateYearSlider);
            
            document.getElementById('dato-slider-min').addEventListener('input', function() {
                var val = parseInt(this.value);
                if (val > selectedFilters.datoMax) { this.value = selectedFilters.datoMax; return; }
                selectedFilters.datoMin = val;
                var d = new Date(val * 1000);
                document.getElementById('dato-value-min').textContent = d.toLocaleDateString('da-DK', { month: 'short', year: 'numeric' });
                updateDisplay();
            });
            document.getElementById('dato-slider-max').addEventListener('input', function() {
                var val = parseInt(this.value);
                if (val < selectedFilters.datoMin) { this.value = selectedFilters.datoMin; return; }
                selectedFilters.datoMax = val;
                var d = new Date(val * 1000);
                document.getElementById('dato-value-max').textContent = d.toLocaleDateString('da-DK', { month: 'short', year: 'numeric' });
                updateDisplay();
            });
        });
        
        // Initial setup
        initializeFilters(lejeData);
        updateKPIContent();
        updateFilterContent();
        updateDisplay();
        updateThumbnails();
        // Vis turnkey knap (leje er default)
        document.getElementById('turnkey-toggle').style.display = 'block';
        
        setTimeout(function() { map.invalidateSize(); }, 100);
    </script>
</body>
</html>'''
    
    # Indsæt data - brug ensure_ascii for at undgå problemer med special chars
    leje_json = json.dumps(leje_data, ensure_ascii=False).replace('</', '<\\/')
    ejer_json = json.dumps(ejer_data, ensure_ascii=False).replace('</', '<\\/')
    
    html = html_template.replace('__LEJE_DATA__', leje_json)
    html = html.replace('__EJER_DATA__', ejer_json)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Dashboard genereret: {output_path}")
    print(f"📊 Lejeboliger: {leje_data['total_boliger']}")
    print(f"🏠 Ejerboliger: {ejer_data['total_boliger']}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python generate_dashboard.py <leje_excel> <ejer_excel> <output_html>")
        sys.exit(1)
    
    leje_excel = sys.argv[1]
    ejer_excel = sys.argv[2]
    output_html = sys.argv[3]
    
    try:
        print("🔄 Læser lejedata...")
        leje_data = process_leje_data(leje_excel)
        
        print("🔄 Læser ejerdata...")
        ejer_data = process_ejer_data(ejer_excel)
        
        print("🔄 Genererer dashboard...")
        generate_html(leje_data, ejer_data, output_html)
        
        print("\n✨ Færdig! Åbn filen i din browser for at se dashboardet.")
    except KeyError as e:
        print(f"\n❌ Kolonnen blev ikke fundet: {e}")
        print("\n📝 Sørg for at dine Excel-filer har de rigtige kolonnenavne.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Der opstod en uventet fejl: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
