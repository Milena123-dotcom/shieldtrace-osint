# ShieldTrace

Creat de **Negoiță Milena-Cristina**.

Aplicatie pentru scanari OSINT pe baza de consimtamant: formular de scanare, scor de expunere, raport, recomandari, istoric si monitorizare.

## Deschidere

Aplicatia trebuie rulata prin backend pentru a obtine rezultate reale.

## Scanare cu date reale online

Porneste backend-ul inclus. Acesta serveste aplicatia si endpointul `/api/scan`.

```bash
cd outputs
BRAVE_API_KEY=cheia_ta python3 server.py
```

Apoi deschide:

```text
http://127.0.0.1:8787
```

Surse live incluse:

- Brave Search API pentru rezultate web, profile sociale, documente, emailuri si telefoane.
- GitHub REST API pentru username-uri publice.
- Gravatar pentru profiluri publice asociate emailurilor.

Fara `BRAVE_API_KEY`, scannerul Brave returneaza `[]`, dar GitHub si Gravatar pot rula in continuare daca utilizatorul introduce username/email. Daca nu sunt gasite rezultate reale, interfata afiseaza: "Nu au fost găsite informații publice."

Interogarile rulate pentru fiecare utilizator:

- `"Nume Prenume"`
- `"Nume Prenume" site:linkedin.com`
- `"Nume Prenume" site:facebook.com`
- `"Nume Prenume" site:instagram.com`
- `"Nume Prenume" filetype:pdf`
- `"Nume Prenume" CV`
- `"Nume Prenume" email`
- `"Nume Prenume" telefon`

## Cum obtii cheia Brave Search API

1. Deschide `https://api-dashboard.search.brave.com/`.
2. Creeaza un cont sau autentifica-te.
3. Creeaza o aplicatie/subscriptie pentru Web Search API.
4. Copiaza cheia API si seteaz-o ca variabila `BRAVE_API_KEY`.

Brave foloseste endpointul `https://api.search.brave.com/res/v1/web/search`, iar autentificarea se face cu headerul `X-Subscription-Token`.

## Testare locala

Porneste serverul:

```bash
cd outputs
BRAVE_API_KEY=cheia_ta python3 server.py
```

Testeaza endpointul:

```bash
curl -X POST http://127.0.0.1:8787/api/scan \
  -H "Content-Type: application/json" \
  -d '{"fullName":"Nume Prenume","country":"Romania","city":"","email":"emailul_tau","phone":"","usernames":["username_github"],"domain":"","modules":["google","social","documents","email","username"],"consent":true}'
```

Daca nu exista rezultate reale sau cheia nu este configurata, raspunsul contine:

```json
{"evidence":[]}
```

## Publicare pe Render

1. Creeaza un repository cu folderul `outputs`.
2. In Render, creeaza un Web Service nou.
3. Seteaza root directory la `outputs`.
4. Seteaza start command:

```bash
python3 server.py
```

5. Adauga variabila de mediu:

```text
BRAVE_API_KEY=cheia_ta
```

6. Publica serviciul si noteaza URL-ul Render.

## Publicare pe Vercel + Render

1. Publica backend-ul pe Render folosind pasii de mai sus.
2. Publica frontend-ul din folderul `outputs` pe Vercel.
3. Configureaza in Vercel o regula de rewrite/proxy pentru `/api/scan` catre endpointul Render `/api/scan`.
4. Pastreaza `BRAVE_API_KEY` doar in Render, nu in Vercel si nu in browser.

## Export pentru utilizatori

Pentru utilizatori reali, publica backend-ul `server.py` sau o versiune echivalenta serverless impreuna cu fisierele frontend.

### Varianta GitHub Pages

1. Creeaza un repository nou.
2. Urca fisierele `index.html`, `styles.css`, `app.js` si `README.md`.
3. Activeaza GitHub Pages din Settings -> Pages.
4. Alege branch-ul principal si folderul root.

### Varianta Vercel

1. Creeaza un proiect nou in Vercel.
2. Urca folderul `outputs`.
3. Seteaza framework-ul ca `Other`.
4. Publica proiectul.

## Ce face versiunea curenta

- Colecteaza inputul de baza: nume, tara, oras, email, telefon, username-uri si domeniu.
- Ruleaza in paralel scanari live prin Brave Search API, GitHub REST API si Gravatar.
- Afiseaza "date gasite online": sursa, URL, fragment, valoare extrasa, incredere si puncte de risc.
- Calculeaza un Identity Exposure Score si un coeficient de posibilitate de furt de identitate pe baza evidentelor.
- Genereaza recomandari personalizate, fiecare legata de datele gasite in analiza.
- Exporta raportul in JSON.

Important: foloseste scanarea doar pentru propria persoana sau cu acord explicit. Produsul trebuie sa pastreze audit de consimtamant si sa ofere stergerea datelor.

## Directia pentru produs real

1. Frontend: Next.js, autentificare, dashboard si export PDF.
2. API: FastAPI cu endpointuri pentru scanari, rapoarte, monitorizare si billing.
3. Queue: Celery/RQ pentru joburi asincrone si scanari saptamanale.
4. Date: PostgreSQL pentru profiluri, scanari, findings, recomandari si audit log.
5. Colectare: doar surse publice, API-uri legitime si fluxuri cu consimtamant.
6. AI: LLM pentru explicatii si prioritizarea recomandarilor, nu pentru completari neconfirmate.
7. Siguranta: ownership check, rate limiting, redactare PII, termenii de utilizare si proces de stergere.

## Principiu de produs

Produsul nu trebuie sa fie un motor de doxxing. Valoarea lui este sa arate utilizatorului ce risc creeaza datele deja publice despre propria persoana si cum poate reduce expunerea.
