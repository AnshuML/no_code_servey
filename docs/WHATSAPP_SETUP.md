# WhatsApp survey — Meta Cloud API setup (step by step)

## DNS_PROBE_FINISHED_NXDOMAIN (browser error)

Iska matlab: tumne jo **poora URL** address bar mein likha, uska **hostname resolve nahi ho raha** — domain Internet par exist nahi karta (typo, **placeholder** jaise `your-ngrok-url`, ya **band / expired ngrok** link).

**Fix:** Pehle `python -m survey_system.whatsapp_server` chalao, phir browser mein sirf **`http://127.0.0.1:8080/health`** check karo (ya `http://localhost:8080/health`).  
**`http://0.0.0.0:8080`** address bar mein **mat likho** — server log mein `0.0.0.0` sirf “har interface par suno” hai; Chrome/Edge is par **`ERR_ADDRESS_INVALID`** dikhate hain.  
Meta ke liye **`ngrok http 8080`** se jo **naya `https://….ngrok-free.app`** aaye **wahi** Callback URL mein lagao — purana URL copy mat karo.

Webhook path browser se randomly open karne par bhi server par **help HTML** milega: `GET /webhook/whatsapp` (bina `hub.mode` query ke).

---

Ye project ab **FastAPI webhook** deta hai: har user ka apna WhatsApp number (`from` id) alag **survey session** (2–3 log ya zyada).

## 1) Server local chalana

Project root se:

```bash
pip install -e .
python -m survey_system.whatsapp_server
```

Default: `http://0.0.0.0:8080`  
Health check: `GET http://localhost:8080/health`

## 2) Internet par HTTPS URL (Meta ke liye zaroori)

Meta sirf **HTTPS** webhook accept karti hai. Local test ke liye **ngrok** (ya Cloudflare Tunnel):

```bash
ngrok http 8080
```

Jo **https://....ngrok-free.app** mile, uske aage path lagao:

`https://YOUR_SUBDOMAIN.ngrok-free.app/webhook/whatsapp`

## 3) Meta Developer dashboard

1. [developers.facebook.com](https://developers.facebook.com) → **Create app** → type **Business**.
2. Product **WhatsApp** add karo.
3. **API Setup** / **Getting started**:
   - **Temporary access token** copy karo → `.env` mein `WHATSAPP_ACCESS_TOKEN`
   - **Phone number ID** copy karo → `WHATSAPP_PHONE_NUMBER_ID`
4. **App settings → Basic → App secret** (optional) → `WHATSAPP_APP_SECRET` (signature verify ke liye).

## 4) Webhook subscribe

1. WhatsApp → **Configuration** → **Webhook** section.
2. **Callback URL**: `https://.../webhook/whatsapp`
3. **Verify token**: koi bhi random string jo tumne `.env` mein `WHATSAPP_VERIFY_TOKEN` rakhi ho **bilkul wahi**.
4. **Verify and save** dabao — Meta **GET** request bhejegi; server `hub.challenge` return karega.

## 5) `.env` minimal example

```env
GROQ_API_KEY=your_groq_key

WHATSAPP_VERIFY_TOKEN=my_random_verify_string
WHATSAPP_ACCESS_TOKEN=EAAxxxx...
WHATSAPP_PHONE_NUMBER_ID=1234567890
# WHATSAPP_APP_SECRET=...   # recommended in prod
# WHATSAPP_SURVEY_JSON=C:\path\to\survey.json   # optional; default family survey
```

Server restart karo har `.env` change ke baad.

## 6) Apne phone se test

1. Meta **WhatsApp → API Setup** mein **test number** tumhare personal WhatsApp par **jodo** (QR / invite flow — dashboard mein diya rehta hai).
2. Us **business / test number** ko message bhejo (jaise `RESET` ya seedha pehla jawab).
3. Jawab **us number se** aayega jo Meta ne app ko diya hai (Cloud API).

**Generic multi-user:** jis bhi user ka `from` id alag hoga, code mein **alag `SurveyChatSession`** use hota hai — 2 ya 3 users = 2 ya 3 parallel sessions.

## 7) Custom survey (kisiko bhi same flow)

`WHATSAPP_SURVEY_JSON` mein **wahi JSON structure** do jo Streamlit / `survey_from_dict` use karta hai (`id`, `title`, `questions[]`).  
File UTF-8 honi chahiye. Empty = bundled **Parivar** demo.

## 8) User commands

- **`RESET`** (ya `/reset`, `restart`, `नया`, …) — naya survey session usi user ke liye.

## 9) Production notes

- Token **long-lived** / system user — Meta docs follow karo.
- `WHATSAPP_APP_SECRET` + signature verify **prod mein on** rakho.
- Session memory abhi **RAM** mein hai; scale par **Redis + DB** adapter same `ResponsePersistence` pattern se.
