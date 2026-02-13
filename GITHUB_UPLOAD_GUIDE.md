# 📤 Hurtig Guide: Upload til GitHub & Deploy

## 🎯 Mål
Deploy din Streamlit app på 5 minutter og få et link du kan dele!

---

## 📋 Trin-for-Trin

### 1️⃣ Lav GitHub Konto (hvis du ikke har en)
1. Gå til https://github.com
2. Klik "Sign up"
3. Følg instruktionerne
4. Bekræft din email

**Har du allerede en konto?** → Spring til trin 2

---

### 2️⃣ Lav Nyt Repository

1. **Log ind på GitHub**

2. **Klik på "+" i top-højre hjørne**
   - Vælg "New repository"

3. **Udfyld informationen:**
   ```
   Repository name: bolig-dashboard
   Description: Bolig analyse dashboard med interaktive grafer
   Visibility: Public (så Streamlit Cloud kan se den)
   ✅ Add a README file (valgfri)
   ```

4. **Klik "Create repository"**

---

### 3️⃣ Upload Filerne

**Metode A: Via Browser (Nemt!) 🌐**

1. **Udpak `BoligDashboard_Streamlit.zip`** på din computer

2. **I dit GitHub repository, klik "Add file" → "Upload files"**

3. **Træk ALLE filer ind** fra den udpakkede mappe:
   ```
   ✅ streamlit_app.py
   ✅ generate_dashboard.py
   ✅ requirements.txt
   ✅ README.md
   ✅ .streamlit/config.toml
   ✅ .gitignore
   ```
   
   **VIGTIGT:** Træk også mappen `.streamlit` ind!

4. **I bunden af siden:**
   - Commit message: "Initial upload"
   - Klik "Commit changes"

5. **Vent 5 sekunder** mens filerne uploader

✅ **Done!** Dine filer er nu på GitHub!

---

**Metode B: Via Git (Avanceret) 💻**

Kun hvis du kender Git:
```bash
git clone https://github.com/DIT-BRUGERNAVN/bolig-dashboard.git
cd bolig-dashboard

# Kopiér alle filer fra BoligDashboard_Streamlit mappen hertil

git add .
git commit -m "Initial upload"
git push
```

---

### 4️⃣ Deploy på Streamlit Cloud

1. **Gå til https://share.streamlit.io**

2. **Klik "Sign in" i top-højre hjørne**
   - Vælg "Continue with GitHub"
   - Godkend adgang

3. **Klik "New app"** (stor blå knap)

4. **Udfyld deployment settings:**
   ```
   Repository: [DIT-BRUGERNAVN]/bolig-dashboard
   Branch: main
   Main file path: streamlit_app.py
   ```

5. **Klik "Deploy!"**

6. **Vent 2-5 minutter** ⏳
   - Du ser en "Building..." besked
   - Streamlit installerer alle pakker
   - Første gang tager det længst

7. **DONE!** 🎉
   - Din app er nu live!
   - Du får et link som: `https://bolig-dashboard-xxxxx.streamlit.app`

---

### 5️⃣ Del Linket!

**Send linket til dine kolleger:**

```
Hej team!

Jeg har lavet en bolig analyse tool. Upload jeres Excel-filer her:
https://bolig-dashboard-xxxxx.streamlit.app

Bare upload lejedata og ejerdata, så genereres dashboardet automatisk!

Mvh
```

---

## 🔄 Opdater App'en Senere

**Når du laver ændringer:**

1. Gå til dit GitHub repository
2. Klik på filen du vil ændre (f.eks. `streamlit_app.py`)
3. Klik "✏️ Edit" (blyant-ikon)
4. Lav dine ændringer
5. Klik "Commit changes"

**Streamlit Cloud re-deployer automatisk!** 🚀
Det tager 1-2 minutter.

---

## 🎨 Customization

### Ændre Farver
Redigér `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#3498db"      ← Din farve
backgroundColor = "#ffffff"
textColor = "#2c3e50"
```

### Tilføj Logo
Upload dit logo til GitHub, så tilføj i `streamlit_app.py`:
```python
st.image("logo.png", width=200)
```

### Ændre Titel
I `streamlit_app.py`, find:
```python
st.title("🏠 Bolig Dashboard Generator")
```
Ændre til dit firma navn!

---

## ❓ Problemer?

### "Repository not found"
→ Tjek at repository er sat til "Public" (ikke Private)

### "Module not found"
→ Tjek at `requirements.txt` er uploaded korrekt

### "App crashed"
→ Klik på "Logs" i Streamlit Cloud for at se fejlen

### "File upload fails"
→ Tjek at Excel-filerne ikke er for store (max 200 MB)

---

## 🔐 Gør App'en Privat

**Gratis tier:** Kun 1 privat app tilladt

**Sådan:**
1. Gå til Streamlit Cloud dashboard
2. Klik på din app
3. Settings → Sharing
4. Vælg "Restricted"
5. Tilføj email-adresser på hvem der må se den

**ELLER:**
Tilføj password (se STREAMLIT_DEPLOYMENT.md)

---

## 🎯 Næste Skridt

✅ **App deployed**  
✅ **Link delt**  
🎉 **Kolleger kan nu bruge det!**

**Vil du gøre det endnu bedre?**
- Tilføj dit firma logo
- Customise farver
- Tilføj flere features

Se `streamlit_app.py` for koden!

---

**Total tid brugt: ~5 minutter** ⏱️  
**Links delt: Uendeligt** ∞  
**Glæde skabt: Maksimal** 😄

---

**God fornøjelse!** 🚀
