# 🚀 Streamlit Deployment Guide

## Mulighed 1: Streamlit Cloud (GRATIS & NEMT) ⭐

### 📋 Hvad du skal bruge:
- GitHub konto (gratis)
- Streamlit Cloud konto (gratis)

### 🔧 Setup (5-10 minutter):

#### 1. Lav GitHub Repository
1. Gå til https://github.com
2. Log ind (eller lav en konto)
3. Klik "New repository"
4. Navn: `bolig-dashboard`
5. Sæt til "Public" eller "Private"
6. Klik "Create repository"

#### 2. Upload Filer til GitHub
Upload disse filer til dit repository:
```
bolig-dashboard/
├── streamlit_app.py           ← Hoved-app'en
├── generate_dashboard.py      ← Dashboard generator
├── requirements.txt           ← Python pakker
└── README.md                  ← Dokumentation (valgfri)
```

**Via GitHub Web Interface:**
1. Klik "Add file" → "Upload files"
2. Træk alle filer ind
3. Klik "Commit changes"

**ELLER via Git Command Line:**
```bash
git clone https://github.com/DIT-BRUGERNAVN/bolig-dashboard.git
cd bolig-dashboard
# Kopiér filerne hertil
git add .
git commit -m "Initial commit"
git push
```

#### 3. Deploy på Streamlit Cloud
1. Gå til https://share.streamlit.io
2. Log ind med GitHub
3. Klik "New app"
4. Vælg dit repository: `bolig-dashboard`
5. Main file: `streamlit_app.py`
6. Klik "Deploy!"

#### 4. Vent 2-5 minutter
Streamlit bygger og deployer din app!

#### 5. Del Linket! 🎉
Du får et link som: `https://bolig-dashboard-xxxxx.streamlit.app`

Send dette link til dine kolleger - de kan bruge det direkte!

---

## Mulighed 2: Streamlit Community Cloud (Samme som ovenstående)

Streamlit Cloud ER Streamlit Community Cloud - det er det samme! 
Følg bare trin ovenfor.

---

## Mulighed 3: Lokal Server (Firmaintern)

Hvis du vil hoste det på din egen server:

### 1. Installer på Server
```bash
# Installer Python 3.10+
# Kopiér filer til server

pip install -r requirements.txt
```

### 2. Kør App'en
```bash
streamlit run streamlit_app.py --server.port 8501
```

### 3. Gør Tilgængelig
- **Lokalt netværk**: Giv folk IP-adressen (f.eks. `http://192.168.1.100:8501`)
- **Internet**: Brug nginx reverse proxy + SSL certifikat

---

## Mulighed 4: Heroku (Betalingsløsning)

### Fordele:
- Professionel hosting
- Custom domain
- Bedre performance

### Setup:
1. Opret Heroku konto
2. Installer Heroku CLI
3. Opret `Procfile`:
```
web: sh setup.sh && streamlit run streamlit_app.py
```
4. Opret `setup.sh`:
```bash
mkdir -p ~/.streamlit/
echo "[server]
headless = true
port = $PORT
enableCORS = false
" > ~/.streamlit/config.toml
```
5. Deploy:
```bash
heroku create bolig-dashboard
git push heroku main
```

---

## 🎯 Anbefaling: Streamlit Cloud

**Hvorfor?**
- ✅ 100% GRATIS
- ✅ 5 minutter setup
- ✅ Automatisk HTTPS
- ✅ Automatisk gendeployment ved fil-ændringer
- ✅ Let at dele link
- ✅ Ingen server vedligeholdelse

**Begrænsninger:**
- Apps "sover" efter 7 dages inaktivitet (gratis tier)
- Begrænset ressourcer (men rigeligt til denne app)

---

## 📊 Sammenligning

| Feature | Streamlit Cloud | Lokal Server | Heroku |
|---------|----------------|--------------|---------|
| **Pris** | GRATIS | Hardware koster | $7+/måned |
| **Setup tid** | 5 min | 30+ min | 20 min |
| **Vedligeholdelse** | Ingen | Fuld IT | Minimal |
| **Deling** | Super let | Kompliceret | Let |
| **Performance** | God | Afhænger af hardware | Meget god |
| **Custom domain** | ❌ | ✅ | ✅ |
| **Private** | Kan laves | ✅ | ✅ |

---

## 🔐 Sikkerhed & Privacy

### Streamlit Cloud:
- Data uploades kun midlertidigt under processing
- Intet gemmes permanent
- Kan sættes til "Private" så kun inviterede kan åbne
- HTTPS encryption

### Ekstra Sikkerhed:
Hvis dine data er meget følsomme, tilføj password:

```python
# I toppen af streamlit_app.py
import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "DIT_PASSWORD":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Resten af din app...
```

---

## 🚀 Kom I Gang NU!

**Hurtigste vej:**

1. Lav GitHub repo (2 min)
2. Upload filer (1 min)
3. Deploy på Streamlit Cloud (2 min)
4. **DÆL LINK!** (10 sek)

Total tid: **5 minutter** ⏱️

---

## 📞 Support

**Streamlit dokumentation:**
https://docs.streamlit.io/

**Streamlit Community:**
https://discuss.streamlit.io/

**Video tutorials:**
https://www.youtube.com/c/StreamlitOfficial

---

**Ready? Let's deploy! 🚀**
