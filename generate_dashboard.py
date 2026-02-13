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
    
    if mode == 'leje':
        x_col = 'Leje/m2'
        y_col = 'Areal'
        room_col = 'Antal værelser'
        title = f'Boligpriser: Areal vs. Leje per m²\n(farvelagt efter antal værelser, n={len(df)})'
        x_label = 'Leje per m² (kr./m²)'
    else:
        x_col = 'Pris pr. m2 (enhedsareal)'
        y_col = 'Enhedsareal'
        room_col = 'Antal Værelser'
        title = f'Boligpriser: Areal vs. Pris per m²\n(farvelagt efter antal værelser, n={len(df)})'
        x_label = 'Pris per m² (kr./m²)'
    
    # Farver for antal værelser
    colors = {2: '#f39c12', 3: '#e74c3c', 4: '#3498db', 5: '#2ecc71', 6: '#9b59b6', 7: '#1abc9c'}
    
    # Plot hvert værelsesniveau
    for rooms in sorted(df[room_col].unique()):
        subset = df[df[room_col] == rooms]
        color = colors.get(rooms, '#95a5a6')
        ax.scatter(subset[x_col], subset[y_col], 
                  c=color, s=100, alpha=0.6, edgecolors='black', linewidth=1.5,
                  label=f'{rooms} værelser (n={len(subset)})')
    
    # Trendlinje
    x = df[x_col].values
    y = df[y_col].values
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_line = np.linspace(x.min(), x.max(), 100)
    
    # Beregn R²
    y_pred = p(x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)
    
    ax.plot(x_line, p(x_line), '--', color='gray', alpha=0.8, linewidth=2,
           label=f'Trendlinje (R²={r_squared:.3f})')
    
    ax.set_xlabel(x_label, fontsize=12, fontweight='bold')
    ax.set_ylabel('Areal (m²)', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Konverter til base64
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{img_base64}"

def create_heatmap(df, mode='leje'):
    """Genererer heatmap matrix"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if mode == 'leje':
        price_col = 'Leje/m2'
        room_col = 'Antal værelser'
        areal_col = 'Areal'
        title = f'Matrix: Gennemsnitlig leje/m² efter areal og antal værelser\n(Rød = dyr, Grøn = billig)'
        label = 'Leje/m² (kr.)'
    else:
        price_col = 'Pris pr. m2 (enhedsareal)'
        room_col = 'Antal Værelser'
        areal_col = 'Enhedsareal'
        title = f'Matrix: Gennemsnitlig pris/m² efter areal og antal værelser\n(Rød = dyr, Grøn = billig)'
        label = 'Pris/m² (kr.)'
    
    # Kategoriser areal
    df_copy = df.copy()
    bins = [0, 50, 75, 100, 115, 130, 200]
    labels = ['0-50 m²', '50-75 m²', '75-100 m²', '100-115 m²', '115-130 m²', '130+ m²']
    df_copy['Areal kategori'] = pd.cut(df_copy[areal_col], bins=bins, labels=labels, include_lowest=True)
    
    # Pivot tabel
    pivot = df_copy.groupby(['Areal kategori', room_col])[price_col].agg(['mean', 'count']).reset_index()
    pivot_matrix = pivot.pivot(index='Areal kategori', columns=room_col, values='mean')
    count_matrix = pivot.pivot(index='Areal kategori', columns=room_col, values='count')
    
    # Plot heatmap
    sns.heatmap(pivot_matrix, annot=False, fmt='.0f', cmap='RdYlGn_r', 
                ax=ax, cbar_kws={'label': label}, linewidths=2, linecolor='white')
    
    # Tilføj annotations med count
    for i, row_label in enumerate(pivot_matrix.index):
        for j, col_label in enumerate(pivot_matrix.columns):
            value = pivot_matrix.iloc[i, j]
            count = count_matrix.iloc[i, j]
            if not pd.isna(value):
                ax.text(j + 0.5, i + 0.5, f'{int(value)}\n(n={int(count)})',
                       ha='center', va='center', fontsize=11, fontweight='bold', color='black')
    
    ax.set_xlabel('Antal værelser', fontsize=12, fontweight='bold')
    ax.set_ylabel('Areal kategori', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{img_base64}"

def create_summary_table(df, mode='leje'):
    """Genererer summary tabel"""
    fig, ax = plt.subplots(figsize=(12, 4))
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
    
    # Format values
    summary[f'Leje pr. m²' if mode == 'leje' else 'Pris pr. m²'] = summary[f'Leje pr. m²' if mode == 'leje' else 'Pris pr. m²'].apply(lambda x: f'{int(x)} kr.')
    summary[f'Leje pr. måned' if mode == 'leje' else 'Pris'] = summary[f'Leje pr. måned' if mode == 'leje' else 'Pris'].apply(lambda x: f'{int(x):,} kr.'.replace(',', '.'))
    summary['Antal værelser'] = summary['Antal værelser'].apply(lambda x: f'{x:.1f}')
    if mode == 'leje':
        summary['Liggetid (dage)'] = summary['Liggetid (dage)'].apply(lambda x: f'{int(x)}')
    
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
    
    # Styling
    for i in range(len(summary.columns)):
        table[(0, i)].set_facecolor('#34495e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    for i in range(1, len(summary)):
        for j in range(len(summary.columns)):
            if i == len(summary) - 1:
                table[(i, j)].set_facecolor('#ecf0f1')
                table[(i, j)].set_text_props(weight='bold')
            else:
                table[(i, j)].set_facecolor('#95a5a6' if i % 2 == 0 else '#bdc3c7')
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{img_base64}"

def process_leje_data(excel_path):
    """Læser og behandler lejedata fra Excel"""
    try:
        df = pd.read_excel(excel_path, sheet_name='Worksheet')
    except:
        df = pd.read_excel(excel_path)
    
    # Find kolonnenavne
    address_col = find_column(df, ['Adresse', 'Address'])
    city_col = find_column(df, ['By', 'City', 'Postnr.'])
    lat_col = find_column(df, ['Lat', 'Latitude'])
    lng_col = find_column(df, ['Lng', 'Lon', 'Longitude'])
    area_col = find_column(df, ['Areal', 'Area'])
    price_m2_col = find_column(df, ['Leje/m2', 'Leje pr. m2'])
    yearly_rent_col = find_column(df, ['Årsleje', 'Arsleje', 'Yearly rent'])
    days_col = find_column(df, ['Liggedage', 'Days on market'])
    rooms_col = find_column(df, ['Antal værelser', 'Antal Værelser', 'Værelser', 'Rooms'])
    
    # Find nye filter-kolonner (optional)
    year_col = None
    for col_name in ['Opførelsesår', 'Opfoerelsesaar', 'Byggeår', 'Year built']:
        if col_name in df.columns:
            year_col = col_name
            break
    
    type_col = None
    for col_name in ['Boligtype', 'Type', 'Property type']:
        if col_name in df.columns:
            type_col = col_name
            break
    
    # Standardiser kolonnenavne
    df['Adresse'] = df[address_col]
    df['By'] = df[city_col]
    df['Lat'] = df[lat_col]
    df['Lng'] = df[lng_col]
    df['Areal'] = df[area_col]
    df['Leje/m2'] = df[price_m2_col]
    df['Årsleje'] = df[yearly_rent_col]
    df['Liggedage'] = df[days_col]
    df['Antal værelser'] = df[rooms_col]
    
    # Tilføj nye kolonner hvis de findes
    if year_col:
        df['Opførelsesår'] = df[year_col]
        print(f"   ✅ Opførelsesår tilføjet fra kolonne: {year_col}")
    else:
        df['Opførelsesår'] = None
        print(f"   ⚠️  Opførelsesår ikke fundet i data")
    
    if type_col:
        df['Boligtype'] = df[type_col]
        print(f"   ✅ Boligtype tilføjet fra kolonne: {type_col}")
    else:
        df['Boligtype'] = 'Ikke angivet'
        print(f"   ⚠️  Boligtype ikke fundet - bruger 'Ikke angivet'")
    
    # Beregn månedlig leje
    if 'Leje/måned' not in df.columns:
        df['Leje/måned'] = df['Årsleje'] / 12
    
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
            'areal': int(row['Areal']),
            'leje_m2': int(row['Leje/m2']),
            'leje_maned': int(row['Årsleje'] / 12),
            'liggedage': int(row['Liggedage']),
            'varelser': int(row['Antal værelser']),
            'opfoerelsesaar': int(row['Opførelsesår']) if pd.notna(row['Opførelsesår']) else None,
            'boligtype': str(row['Boligtype']) if pd.notna(row['Boligtype']) else 'Ikke angivet'
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
    """Læser og behandler ejerdata fra Excel"""
    
    # Tjek om filen har flere sheets
    excel_file = pd.ExcelFile(excel_path)
    print(f"   📑 Faner i filen: {excel_file.sheet_names}")
    
    # Læs fra første sheet (Stamdata eller hoveddata)
    df = pd.read_excel(excel_path, sheet_name=0)
    
    # Hvis der er en 'Enheder' fane, merge den for at få Antal værelser
    if 'Enheder' in excel_file.sheet_names:
        print(f"   🔗 Merger med 'Enheder' fane...")
        df_enheder = pd.read_excel(excel_path, sheet_name='Enheder')
        
        # Find værelses-kolonnen (kan hedde lidt forskelligt)
        rooms_col_enheder = None
        for col_name in ['Antal værelser', 'Antal Værelser', 'Værelser']:
            if col_name in df_enheder.columns:
                rooms_col_enheder = col_name
                break
        
        # Find koordinat-kolonner i Enheder fanen
        lat_col_enheder = None
        lng_col_enheder = None
        for col_name in ['Latitude', 'Lat', 'latitude']:
            if col_name in df_enheder.columns:
                lat_col_enheder = col_name
                break
        for col_name in ['Longitude', 'Lng', 'Lon', 'longitude']:
            if col_name in df_enheder.columns:
                lng_col_enheder = col_name
                break
        
        if 'Handels-ID' in df_enheder.columns and 'Handels-ID' in df.columns:
            # Byg liste af kolonner at merge
            merge_cols = ['Handels-ID']
            if rooms_col_enheder:
                merge_cols.append(rooms_col_enheder)
            if lat_col_enheder:
                merge_cols.append(lat_col_enheder)
            if lng_col_enheder:
                merge_cols.append(lng_col_enheder)
            
            df = df.merge(
                df_enheder[merge_cols], 
                on='Handels-ID', 
                how='left'
            )
            # Standardiser navnet
            if rooms_col_enheder and rooms_col_enheder != 'Antal Værelser':
                df['Antal Værelser'] = df[rooms_col_enheder]
            if lat_col_enheder:
                df['lat'] = df[lat_col_enheder]
            if lng_col_enheder:
                df['lng'] = df[lng_col_enheder]
            
            has_coords = lat_col_enheder and lng_col_enheder
            print(f"   ✅ Merge lykkedes! Værelses-data{' og koordinater' if has_coords else ''} tilføjet.")
        else:
            print(f"   ⚠️  Kunne ikke merge - mangler kolonner")
    
    print(f"   📋 Tjekker kolonner...")
    
    # Find kolonnenavne (de kan variere lidt)
    price_col = find_column(df, ['Pris', 'Price', 'Salgspris'])
    area_col = find_column(df, ['Enhedsareal', 'Areal', 'Area'])
    price_m2_col = find_column(df, ['Pris pr. m2 (enhedsareal)', 'Pris pr. m2', 'Pris/m2'])
    name_col = find_column(df, ['Handelsnavn', 'Adresse', 'Address'])
    date_col = find_column(df, ['Handelsdato', 'Dato', 'Date'])
    
    # Tjek om vi nu har værelses-data efter merge
    if 'Antal Værelser' not in df.columns:
        # Prøv at finde værelses-kolonne
        room_col = None
        for possible_name in ['Antal værelser', 'Værelser', 'Rooms', 'Antal rum']:
            if possible_name in df.columns:
                room_col = possible_name
                df['Antal Værelser'] = df[room_col]
                break
        
        if room_col is None:
            print(f"   ⚠️  ADVARSEL: 'Antal Værelser' kolonne ikke fundet!")
            print(f"   💡 Estimerer antal værelser baseret på areal...")
            # Estimér antal værelser baseret på areal
            def estimate_rooms(area):
                if area < 50:
                    return 2
                elif area < 75:
                    return 3
                elif area < 100:
                    return 4
                elif area < 125:
                    return 5
                else:
                    return 6
            
            df['Antal Værelser'] = df[area_col].apply(estimate_rooms)
    
    # Geocode kun hvis vi ikke allerede har koordinater
    if 'lat' not in df.columns or 'lng' not in df.columns or df['lat'].isna().any():
        print(f"   📍 Geocoder adresser...")
        coords = df[name_col].apply(geocode_address)
        if 'lat' not in df.columns:
            df['lat'] = coords.apply(lambda x: x[0])
        if 'lng' not in df.columns:
            df['lng'] = coords.apply(lambda x: x[1])
        # Fyld manglende koordinater
        df['lat'] = df['lat'].fillna(coords.apply(lambda x: x[0]))
        df['lng'] = df['lng'].fillna(coords.apply(lambda x: x[1]))
    else:
        print(f"   ✅ Koordinater allerede til stede fra Enheder-fanen")
    
    df['By'] = df[name_col].apply(parse_city_from_handelsnavn)
    df['Handelsdato_str'] = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d')
    
    # Hent Anvendelse (Boligtype) fra Stamdata eller Enheder
    if 'Anvendelse' not in df.columns:
        anvendelse_col = None
        for col_name in ['Anvendelse', 'Ejendomstype', 'Type', 'Enhedens anvendelse']:
            if col_name in df.columns:
                anvendelse_col = col_name
                break
        
        if anvendelse_col:
            df['Anvendelse'] = df[anvendelse_col]
            print(f"   ✅ Anvendelse tilføjet fra kolonne: {anvendelse_col}")
        else:
            df['Anvendelse'] = 'Ikke angivet'
            print(f"   ⚠️  Anvendelse ikke fundet - bruger 'Ikke angivet'")
    
    # Prøv at hente Opførelsesår fra Ejendomme-fanen hvis den findes
    if 'Ejendomme' in excel_file.sheet_names:
        print(f"   🔗 Merger med 'Ejendomme' fane for Opførelsesår...")
        df_ejendomme = pd.read_excel(excel_path, sheet_name='Ejendomme')
        
        year_col_ejend = None
        for col_name in ['Opførelsesår', 'Opfoerelsesaar', 'Byggeår']:
            if col_name in df_ejendomme.columns:
                year_col_ejend = col_name
                break
        
        if year_col_ejend and 'Handels-ID' in df_ejendomme.columns:
            df = df.merge(
                df_ejendomme[['Handels-ID', year_col_ejend]],
                on='Handels-ID',
                how='left'
            )
            df['Opførelsesår'] = df[year_col_ejend]
            print(f"   ✅ Opførelsesår hentet fra Ejendomme-fanen")
        else:
            df['Opførelsesår'] = None
            print(f"   ⚠️  Opførelsesår ikke fundet i Ejendomme-fanen")
    else:
        df['Opførelsesår'] = None
        print(f"   ⚠️  Ejendomme-fane ikke fundet - Opførelsesår ikke tilgængelig")
    
    # Standardiser kolonnenavne til hvad scriptet forventer
    df['Pris'] = df[price_col]
    df['Enhedsareal'] = df[area_col]
    df['Pris pr. m2 (enhedsareal)'] = df[price_m2_col]
    df['Handelsnavn'] = df[name_col]
    df['Handelsdato'] = df[date_col]
    
    # Generer grafer
    print("   Genererer scatter plot...")
    scatter_img = create_scatter_plot(df, mode='ejer')
    print("   Genererer heatmap...")
    heatmap_img = create_heatmap(df, mode='ejer')
    print("   Genererer tabel...")
    table_img = create_summary_table(df, mode='ejer')
    
    # Rens data - fjern rækker med manglende vigtige data
    original_count = len(df)
    df = df.dropna(subset=['Handelsnavn', 'By', 'lat', 'lng', 'Enhedsareal', 'Pris', 'Pris pr. m2 (enhedsareal)', 'Antal Værelser'])
    dropped = original_count - len(df)
    if dropped > 0:
        print(f"   ⚠️  Fjernet {dropped} rækker med manglende data")
    
    # Konverter til dictionary
    boliger = []
    for _, row in df.iterrows():
        bolig = {
            'handelsnavn': str(row['Handelsnavn']),
            'by': str(row['By']),
            'lat': float(row['lat']),
            'lng': float(row['lng']),
            'areal': int(row['Enhedsareal']),
            'pris': int(row['Pris']),
            'pris_m2': int(row['Pris pr. m2 (enhedsareal)']),
            'varelser': int(row['Antal Værelser']),
            'handelsdato': str(row['Handelsdato_str']),
            'anvendelse': str(row['Anvendelse']) if pd.notna(row['Anvendelse']) else 'Ikke angivet',
            'opfoerelsesaar': int(row['Opførelsesår']) if pd.notna(row['Opførelsesår']) else None
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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; }
        #map { position: fixed; left: 0; top: 0; width: 100%; height: 100vh; }
        
        .mode-toggle {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1001;
            background: white;
            border-radius: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            display: flex;
            padding: 4px;
        }
        
        .mode-btn {
            background: transparent;
            border: none;
            padding: 10px 25px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            border-radius: 20px;
            transition: all 0.3s;
            color: #2c3e50;
        }
        
        .mode-btn.active {
            background: #3498db;
            color: white;
        }
        
        .bi-boxes {
            position: fixed; 
            top: 80px; 
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .bi-box {
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            padding: 10px;
            width: 200px;
        }
        
        .bi-box-title {
            font-size: 12px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        
        .kpi-compact {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        
        .kpi-item {
            text-align: center;
        }
        
        .kpi-item.full {
            grid-column: span 2;
            background: #3498db;
            color: white;
            padding: 8px;
            border-radius: 4px;
        }
        
        .kpi-value-small {
            font-size: 18px;
            font-weight: bold;
        }
        
        .kpi-label-small {
            font-size: 9px;
            opacity: 0.7;
        }
        
        canvas {
            max-height: 120px !important;
        }
        
        .filter-group {
            margin-bottom: 8px;
        }
        
        .filter-label {
            font-size: 10px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 4px;
        }
        
        .filter-options {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }
        
        .filter-btn {
            background: #ecf0f1;
            border: 1px solid #bdc3c7;
            padding: 4px 8px;
            font-size: 10px;
            border-radius: 3px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .filter-btn:hover {
            background: #bdc3c7;
        }
        
        .filter-btn.active {
            background: #3498db;
            color: white;
            border-color: #2980b9;
        }
        
        .reset-btn {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 6px;
            font-size: 10px;
            border-radius: 3px;
            cursor: pointer;
            width: 100%;
            margin-top: 8px;
            font-weight: bold;
        }
        
        .reset-btn:hover {
            background: #c0392b;
        }
        
        .thumbnails {
            position: fixed; bottom: 20px; left: 20px;
            z-index: 1000; display: flex; gap: 15px;
        }
        .thumbnail {
            width: 150px; height: 100px; cursor: pointer;
            border-radius: 8px; overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            transition: all 0.3s; opacity: 0.7; border: 3px solid white;
        }
        .thumbnail:hover { 
            opacity: 1; transform: scale(1.05); 
            box-shadow: 0 6px 20px rgba(0,0,0,0.6); 
        }
        .thumbnail img { width: 100%; height: 100%; object-fit: cover; }
        
        .overlay {
            display: none; position: fixed; z-index: 2000;
            left: 0; top: 0; width: 100%; height: 100vh;
            background-color: rgba(0,0,0,0.75); backdrop-filter: blur(5px);
        }
        .overlay-content { 
            position: relative; margin: 2% auto; padding: 20px; 
            max-width: 90%; max-height: 90vh; text-align: center; 
        }
        .overlay-content img { 
            max-width: 100%; max-height: 85vh; border-radius: 10px; 
            box-shadow: 0 8px 30px rgba(0,0,0,0.5); 
        }
        .close {
            position: absolute; top: 10px; right: 35px;
            color: #f1f1f1; font-size: 40px; font-weight: bold;
            cursor: pointer;
        }
        .close:hover { color: #bbb; }
        
        .info-box { padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        .info-box h3 { margin: 0 0 10px 0; color: #2c3e50; }
        .info-box p { margin: 5px 0; font-size: 14px; }
        
        .legend { padding: 10px; background: white; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .legend-item { margin: 5px 0; display: flex; align-items: center; }
        .legend-color { width: 20px; height: 20px; border-radius: 50%; margin-right: 10px; border: 2px solid black; }
        
        /* Range Slider Styling */
        input[type="range"] {
            -webkit-appearance: none;
            appearance: none;
            pointer-events: all;
            cursor: pointer;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            background: #3498db;
            border: 2px solid white;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            pointer-events: all;
            position: relative;
            z-index: 3;
        }
        input[type="range"]::-moz-range-thumb {
            width: 18px;
            height: 18px;
            background: #3498db;
            border: 2px solid white;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        #year-slider-min::-webkit-slider-thumb { z-index: 4; }
        #year-slider-max::-webkit-slider-thumb { z-index: 5; }
    </style>
</head>
<body>
    <!-- Mode Toggle -->
    <div class="mode-toggle">
        <button class="mode-btn active" onclick="switchMode('leje')">Lejeboliger</button>
        <button class="mode-btn" onclick="switchMode('ejer')">Ejerboliger</button>
    </div>
    
    <div id="map"></div>
    
    <!-- BI Boxes -->
    <div class="bi-boxes">
        <div class="bi-box">
            <div class="bi-box-title" id="kpi-title">📊 Nøgletal</div>
            <div class="kpi-compact" id="kpi-content"></div>
        </div>
        
        <div class="bi-box">
            <div class="bi-box-title">🏠 Værelser</div>
            <canvas id="roomChart"></canvas>
        </div>
        
        <div class="bi-box">
            <div class="bi-box-title">📍 Byer</div>
            <canvas id="byChart"></canvas>
        </div>
        
        <div class="bi-box">
            <div class="bi-box-title">🔍 Filtre</div>
            <div id="filter-content"></div>
        </div>
    </div>
    
    
    <!-- Year Range Slider -->
    <div id="year-slider-container" style="display: none; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; background: white; padding: 15px 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); min-width: 400px;">
        <div style="font-weight: bold; font-size: 12px; color: #2c3e50; margin-bottom: 10px; text-align: center;">
            🏗️ OPFØRELSESÅR
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span id="year-min" style="font-size: 11px; color: #7f8c8d; min-width: 40px;">2000</span>
            <div style="flex: 1; position: relative;">
                <input type="range" id="year-slider-min" style="width: 100%; position: absolute; pointer-events: none; -webkit-appearance: none; height: 8px; background: transparent;">
                <input type="range" id="year-slider-max" style="width: 100%; position: absolute; pointer-events: none; -webkit-appearance: none; height: 8px; background: transparent;">
                <div style="height: 8px; background: #ecf0f1; border-radius: 4px; position: relative; margin: 8px 0;">
                    <div id="year-range-fill" style="position: absolute; height: 100%; background: #3498db; border-radius: 4px;"></div>
                </div>
            </div>
            <span id="year-max" style="font-size: 11px; color: #7f8c8d; min-width: 40px; text-align: right;">2025</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 13px; font-weight: bold; color: #2c3e50;">
            <span>Fra: <span id="year-value-min">2000</span></span>
            <span>Til: <span id="year-value-max">2025</span></span>
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
    <div id="overlay1" class="overlay" onclick="closeOverlay('overlay1')">
        <span class="close" onclick="closeOverlay('overlay1')">&times;</span>
        <div class="overlay-content" onclick="event.stopPropagation()">
            <div id="scatter-plot" style="width: 90%; height: 85vh; background: white; border-radius: 10px;"></div>
        </div>
    </div>
    
    <div id="overlay2" class="overlay" onclick="closeOverlay('overlay2')">
        <span class="close" onclick="closeOverlay('overlay2')">&times;</span>
        <div class="overlay-content" onclick="event.stopPropagation()">
            <div id="heatmap-plot" style="width: 90%; height: 85vh; background: white; border-radius: 10px;"></div>
        </div>
    </div>
    
    <div id="overlay3" class="overlay" onclick="closeOverlay('overlay3')">
        <span class="close" onclick="closeOverlay('overlay3')">&times;</span>
        <div class="overlay-content" onclick="event.stopPropagation()">
            <div id="table-plot" style="width: 90%; height: 85vh; background: white; border-radius: 10px; overflow: auto;"></div>
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
                        line: { color: 'black', width: 1 }
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
                title: {
                    text: mode === 'leje' ? 
                        'Lejepriser: Areal vs. Leje per m² (n=' + filtered.length + ')' :
                        'Salgspriser: Areal vs. Pris per m² (n=' + filtered.length + ')',
                    font: { size: 18, weight: 'bold' }
                },
                xaxis: { title: mode === 'leje' ? 'Leje per m² (kr./m²)' : 'Pris per m² (kr./m²)' },
                yaxis: { title: 'Areal (m²)' },
                hovermode: 'closest',
                showlegend: true,
                legend: { x: 1, y: 1, xanchor: 'right' }
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
                colorscale: 'RdYlGn_r',
                text: textValues,
                hovertemplate: '%{y}<br>%{x}<br>%{text}<extra></extra>',
                showscale: true,
                colorbar: {
                    title: mode === 'leje' ? 'Leje/m² (kr.)' : 'Pris/m² (kr.)'
                }
            }];
            
            var layout = {
                title: {
                    text: mode === 'leje' ?
                        'Matrix: Gennemsnitlig leje/m² efter areal og værelser' :
                        'Matrix: Gennemsnitlig pris/m² efter areal og værelser',
                    font: { size: 16 }
                },
                xaxis: { title: 'Antal værelser', side: 'bottom' },
                yaxis: { title: 'Areal kategori' },
                annotations: []
            };
            
            // Tilføj tekst i hver celle
            for (var i = 0; i < categories.length; i++) {
                for (var j = 0; j < roomNumbers.length; j++) {
                    if (zValues[i][j] !== null) {
                        var annotation = {
                            x: roomNumbers[j] + ' vær.',
                            y: categories[i],
                            text: textValues[i][j].replace('<br>', '\\n'),
                            showarrow: false,
                            font: { size: 11, color: 'black', weight: 'bold' }
                        };
                        layout.annotations.push(annotation);
                    }
                }
            }
            
            Plotly.newPlot('heatmap-plot', data, layout, {responsive: true});
        }
        
        function createTable(filtered) {
            var mode = currentMode;
            
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
                        liggedage_sum: 0
                    };
                }
                
                var cat = categorized[category];
                cat.count++;
                cat.areal_sum += b.areal;
                cat.pris_m2_sum += (mode === 'leje' ? b.leje_m2 : b.pris_m2);
                cat.pris_total_sum += (mode === 'leje' ? b.leje_maned : b.pris);
                cat.varelser_sum += b.varelser;
                if (mode === 'leje') cat.liggedage_sum += b.liggedage;
            });
            
            // Byg tabel HTML
            var html = '<table style="width: 100%; border-collapse: collapse; margin: 20px;">';
            html += '<tr style="background: #34495e; color: white;">';
            html += '<th style="padding: 12px; border: 1px solid #ddd;">Areal</th>';
            html += '<th style="padding: 12px; border: 1px solid #ddd;">Antal ' + (mode === 'leje' ? 'lejepunkter' : 'salgspunkter') + '</th>';
            html += '<th style="padding: 12px; border: 1px solid #ddd;">' + (mode === 'leje' ? 'Leje pr. m²' : 'Pris pr. m²') + '</th>';
            html += '<th style="padding: 12px; border: 1px solid #ddd;">' + (mode === 'leje' ? 'Leje pr. måned' : 'Pris') + '</th>';
            html += '<th style="padding: 12px; border: 1px solid #ddd;">Antal værelser</th>';
            if (mode === 'leje') {
                html += '<th style="padding: 12px; border: 1px solid #ddd;">Liggetid (dage)</th>';
            }
            html += '</tr>';
            
            var categories = ['0-50 m²', '50-75 m²', '75-100 m²', '100-115 m²', '115-130 m²', '130+ m²'];
            var rowIndex = 0;
            categories.forEach(function(cat) {
                if (categorized[cat]) {
                    var data = categorized[cat];
                    var bgColor = rowIndex % 2 === 0 ? '#ecf0f1' : '#bdc3c7';
                    
                    html += '<tr style="background: ' + bgColor + ';">';
                    html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + cat + '</td>';
                    html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + data.count + '</td>';
                    html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + Math.round(data.pris_m2_sum / data.count).toLocaleString('da-DK') + ' kr.</td>';
                    html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + Math.round(data.pris_total_sum / data.count).toLocaleString('da-DK') + ' kr.</td>';
                    html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + (data.varelser_sum / data.count).toFixed(1) + '</td>';
                    if (mode === 'leje') {
                        html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + Math.round(data.liggedage_sum / data.count) + '</td>';
                    }
                    html += '</tr>';
                    rowIndex++;
                }
            });
            
            // Total række
            html += '<tr style="background: #95a5a6; font-weight: bold;">';
            html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">Gennemsnit</td>';
            html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + filtered.length + '</td>';
            var avgPrisM2 = Math.round(filtered.reduce((s, b) => s + (mode === 'leje' ? b.leje_m2 : b.pris_m2), 0) / filtered.length);
            var avgPrisTotal = Math.round(filtered.reduce((s, b) => s + (mode === 'leje' ? b.leje_maned : b.pris), 0) / filtered.length);
            var avgVarelser = (filtered.reduce((s, b) => s + b.varelser, 0) / filtered.length).toFixed(1);
            html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + avgPrisM2.toLocaleString('da-DK') + ' kr.</td>';
            html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + avgPrisTotal.toLocaleString('da-DK') + ' kr.</td>';
            html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + avgVarelser + '</td>';
            if (mode === 'leje') {
                var avgLiggedage = Math.round(filtered.reduce((s, b) => s + b.liggedage, 0) / filtered.length);
                html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">' + avgLiggedage + '</td>';
            }
            html += '</tr>';
            
            html += '</table>';
            
            document.getElementById('table-plot').innerHTML = html;
        }
        
        function updateInteractiveCharts() {
            var filtered = allBoliger.filter(function(bolig) {
                var varelserMatch = selectedFilters.varelser.length === 0 || 
                                   selectedFilters.varelser.includes(bolig.varelser);
                var byMatch = selectedFilters.by.length === 0 || 
                             selectedFilters.by.includes(bolig.by);
                var aarMatch = bolig.opfoerelsesaar === null || 
                              (selectedFilters.aarMin === null || bolig.opfoerelsesaar >= selectedFilters.aarMin) &&
                              (selectedFilters.aarMax === null || bolig.opfoerelsesaar <= selectedFilters.aarMax);
                var typeValue = currentMode === 'leje' ? bolig.boligtype : bolig.anvendelse;
                var typeMatch = selectedFilters.type.length === 0 || selectedFilters.type.includes(typeValue);
                
                return varelserMatch && byMatch && aarMatch && typeMatch;
            });
            
            createScatterPlot(filtered);
            createHeatmap(filtered);
            createTable(filtered);
        }
        
        function updateThumbnails() {
            var data = currentMode === 'leje' ? lejeData : ejerData;
            document.getElementById('thumb1').src = data.scatter_img;
            document.getElementById('thumb2').src = data.heatmap_img;
            document.getElementById('thumb3').src = data.table_img;
            // Opdater interaktive grafer
            updateInteractiveCharts();
        }
        
        function switchMode(mode) {
            currentMode = mode;
            allBoliger = mode === 'leje' ? lejeData.boliger : ejerData.boliger;
            
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            var data = mode === 'leje' ? lejeData : ejerData;
            map.setView([data.center_lat, data.center_lng], 13);
            
            initializeFilters(data);  // Dette sætter alle filtre aktive
            updateKPIContent();
            updateFilterContent();
            updateDisplay();
            updateThumbnails();
        }
        
        function initializeFilters(data) {
            var vaerelser = [...new Set(data.boliger.map(b => b.varelser))].sort((a,b) => a-b);
            selectedFilters.varelser = vaerelser;  // Alle aktive som standard
            var byer = [...new Set(data.boliger.map(b => b.by))].sort();
            selectedFilters.by = byer;  // Alle aktive som standard
            var aar = [...new Set(data.boliger.map(b => b.opfoerelsesaar).filter(y => y !== null))].sort((a,b) => a-b);
            if (aar.length > 0) {
                selectedFilters.aarMin = Math.min(...aar);
                selectedFilters.aarMax = Math.max(...aar);
            }
            var typer = [...new Set(data.boliger.map(b => currentMode === 'leje' ? b.boligtype : b.anvendelse))].sort();
            selectedFilters.type = typer;  // Alle aktive som standard
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
        }
        
        function resetFilters() {
            var data = currentMode === 'leje' ? lejeData : ejerData;
            initializeFilters(data);  // Aktivér alle filtre igen
            updateFilterContent();
            updateDisplay();
        }
        
        function updateDisplay() {
            var filtered = allBoliger.filter(function(bolig) {
                // Vis kun boliger hvor værelses-antal ER i de valgte filtre
                var varelserMatch = selectedFilters.varelser.includes(bolig.varelser);
                // Vis kun boliger hvor by ER i de valgte filtre  
                var byMatch = selectedFilters.by.includes(bolig.by);
                // Vis kun boliger hvor opførelsesår er inden for range (eller hvis det er null)
                var aarMatch = bolig.opfoerelsesaar === null || 
                              (selectedFilters.aarMin === null || bolig.opfoerelsesaar >= selectedFilters.aarMin) &&
                              (selectedFilters.aarMax === null || bolig.opfoerelsesaar <= selectedFilters.aarMax);
                // Vis kun boliger hvor type ER i de valgte filtre
                var typeValue = currentMode === 'leje' ? bolig.boligtype : bolig.anvendelse;
                var typeMatch = selectedFilters.type.length === 0 || selectedFilters.type.includes(typeValue);
                
                return varelserMatch && byMatch && aarMatch && typeMatch;
            });
            
            updateKPIs(filtered);
            updateMap(filtered);
            updateCharts(filtered);
            updateInteractiveCharts();  // Opdater de interaktive analyse-grafer
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
                        <p><strong>Areal:</strong> ${bolig.areal} m2</p>
                        <p><strong>Antal værelser:</strong> ${bolig.varelser}</p>
                        <p><strong>Leje pr. m2:</strong> ${bolig.leje_m2} kr.</p>
                        <p><strong>Leje pr. måned:</strong> ${bolig.leje_maned.toLocaleString('da-DK')} kr.</p>
                        <p><strong>Liggetid:</strong> ${bolig.liggedage} dage</p>
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
        
        function openOverlay(overlayId) {
            document.getElementById(overlayId).style.display = "block";
            // Generer grafer når overlay åbnes
            updateInteractiveCharts();
        }
        
        function closeOverlay(overlayId) {
            // Luk kun hvis der klikkes på baggrunden, ikke på grafen selv
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
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
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
            div.innerHTML += '<p style="margin-top: 10px; font-size: 12px; font-style: italic;">Punkt-størrelse = Pris/m2</p>';
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
        });
        
        // Initial setup
        initializeFilters(lejeData);
        updateKPIContent();
        updateFilterContent();
        updateDisplay();
        updateThumbnails();
        
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
