# ShieldTrace MVP

Creat de **Negoiță Milena-Cristina**.

Prototip local pentru produsul SaaS descris: formular de scanare, scor de expunere, raport, recomandari, istoric si monitorizare.

## Deschidere

Deschide `index.html` in browser. Aplicatia este statica si nu are dependinte.

## Scanare cu date reale online

Pentru date reale, porneste backend-ul inclus. Acesta serveste aplicatia si endpointul `/api/scan`.

```bash
cd outputs
GOOGLE_API_KEY=cheia_ta GOOGLE_CX=id_motor_cautare python3 server.py
```

Apoi deschide:

```text
http://127.0.0.1:8787
```

Surse live incluse:

- Google Programmable Search pentru rezultate, profile sociale, documente, emailuri, telefoane si username-uri.
- GitHub API pentru username-uri publice.
- Gravatar pentru emailuri cu profil public.

Fara `GOOGLE_API_KEY` si `GOOGLE_CX`, backend-ul poate verifica doar sursele fara cheie, precum GitHub si Gravatar. Daca backend-ul nu ruleaza, frontend-ul foloseste fallback demonstrativ.

## Export pentru utilizatori

Pentru demo fara date live, aplicatia poate fi publicata ca site static. Pentru date reale, trebuie publicate si backend-ul `server.py` sau o versiune echivalenta serverless.

### Varianta rapida: Netlify Drop

1. Intra pe `https://app.netlify.com/drop`.
2. Trage folderul `outputs` sau arhiva `shieldtrace-mvp.zip` in pagina.
3. Netlify iti genereaza un link public pe care il poti trimite oamenilor.

Aceasta varianta este doar demo static. Pentru rezultate online reale, foloseste un backend deployat separat si configureaza frontend-ul sa apeleze acel API.

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
- Poate rula scanare live prin backend si API-uri publice/legitime.
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
6. AI: LLM pentru explicatii si prioritizarea recomandarilor, nu pentru inventarea datelor.
7. Siguranta: ownership check, rate limiting, redactare PII, termenii de utilizare si proces de stergere.

## Principiu de produs

Produsul nu trebuie sa fie un motor de doxxing. Valoarea lui este sa arate utilizatorului ce risc creeaza datele deja publice despre propria persoana si cum poate reduce expunerea.
