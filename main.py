import os
import json
import requests
from fastapi import FastAPI, Request, Query
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ====== REQUIRED ENV VARS (set these in your .env file) ======
# WHATSAPP_TOKEN=EAAd3d7RVw0kBQdpTqUhGPk5wjuZBC3EdIKjScFIfS5wBJGSEgZASFLg1NFSFhLW8jJdxEDlYY1rJfDz1C9iGEZAe5hjlnNiMfZA7IzuYI2Bs56m3y9TfuMIyeZAkOC1y0KKqYK5bvYgluuY5l3aZBZAhCDJyxc554wewhjjLnwuIdB6TCZCLR4ZBJ3kuLGZAZA2ztMRNwZDZD
# PHONE_NUMBER_ID=978489455341331
# VERIFY_TOKEN=botworks_verify_123

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "").strip()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "botworks_verify_123").strip()

GRAPH_API_VERSION = "v18.0"

# ====== In-memory appointment state (simple) ======
# states[from_number] = {"step": "ASK_NAME", "service_id": "S_WA_BOT", "name":"", "phone":"", "time":""}
states = {}

# ====== Botworks service + pricing ======
SERVICE_CATALOG = {
    "S_WA_BOT": {
        "title": "WhatsApp Bot",
        "price": "Setup ₹15K one-time + ₹5K/month",
        "detail": (
            "✅ *WhatsApp Bot*\n\n"
            "We build an official WhatsApp bot for your business:\n"
            "• Auto-replies & FAQs\n"
            "• Lead capture (name, phone, requirement)\n"
            "• Human handoff\n"
            "• Integrations (Sheets/CRM) if needed\n\n"
            "💰 Pricing: Setup ₹15,000 one-time + ₹5,000/month\n\n"
            "Would you like to fix a phone appointment?"
        ),
    },
    "S_AD_VIDEOS": {
        "title": "AI Realistic Ad Videos",
        "price": "Starting from ₹6K per video",
        "detail": (
            "🎥 *AI Realistic Ad Videos*\n\n"
            "We create realistic AI ad videos for your brand:\n"
            "• Reels / Ads / Promos\n"
            "• Script + visuals guidance\n\n"
            "💰 Pricing: Starting from ₹6,000 per video\n\n"
            "Would you like to fix a phone appointment?"
        ),
    },
    "S_DIGITAL_TWINS": {
        "title": "AI Digital Twins",
        "price": "Starting from ₹6K per video",
        "detail": (
            "🧑‍💼 *AI Digital Twins*\n\n"
            "We create AI digital twin style content:\n"
            "• Talking avatar videos\n"
            "• Brand-style presentations\n\n"
            "💰 Pricing: Starting from ₹6,000 per video\n\n"
            "Would you like to fix a phone appointment?"
        ),
    },
    "S_SCENE": {
        "title": "AI Scene Creation",
        "price": "Starting from ₹20K",
        "detail": (
            "🎬 *AI Scene Creation*\n\n"
            "We create cinematic AI scenes for ads, promos, and storytelling.\n\n"
            "💰 Pricing: Starting from ₹20,000\n\n"
            "Would you like to fix a phone appointment?"
        ),
    },
    "S_SONG": {
        "title": "AI Song Creation",
        "price": "Starting from ₹20K",
        "detail": (
            "🎵 *AI Song Creation*\n\n"
            "We create AI songs (concept + lyrics + structure) and guide visuals if needed.\n\n"
            "💰 Pricing: Starting from ₹20,000\n\n"
            "Would you like to fix a phone appointment?"
        ),
    },
    "S_AI_ML": {
        "title": "AI / ML Solutions",
        "price": "Custom pricing",
        "detail": (
            "🤖 *AI / ML Solutions*\n\n"
            "We build custom AI solutions based on your requirement:\n"
            "• Automation\n"
            "• AI tools for business\n"
            "• Integrations & workflows\n\n"
            "💰 Pricing: Custom (depends on scope)\n\n"
            "Would you like to fix a phone appointment?"
        ),
    },
}


# ====== WhatsApp Send Helpers ======
def send_whatsapp(payload: dict):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("❌ Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID in .env")
        return

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code >= 300:
        print("❌ Send error:", r.status_code, r.text)
    else:
        print("✅ Sent:", r.text)


def send_text(to: str, text: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    send_whatsapp(payload)


def build_list_services(to: str):
    rows = []
    for sid, s in SERVICE_CATALOG.items():
        rows.append({
            "id": sid,
            "title": s["title"],
            "description": s["price"]
        })

    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Thanks for reaching *Botworks* 👋\nHow can we help you today?\n\nPlease choose a service:"},
            "action": {
                "button": "Choose a Service",
                "sections": [
                    {"title": "Botworks Services", "rows": rows}
                ]
            }
        }
    }


def build_yes_no_buttons(to: str, text: str):
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "BOOK_YES", "title": "Yes"}},
                    {"type": "reply", "reply": {"id": "BOOK_NO", "title": "No"}}
                ]
            }
        }
    }


# ====== Webhook Verification (GET) ======
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return {"status": "verification failed"}


# ====== Webhook Receiver (POST) ======
@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    print("Incoming webhook:", json.dumps(data))

    try:
        entry = data.get("entry", [])
        if not entry:
            return {"status": "ok"}

        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ok"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ok"}

        msg = messages[0]
        from_number = msg.get("from")  # user's WA number (wa_id)

        # --------- Extract user input ----------
        user_text = None
        interactive_id = None

        msg_type = msg.get("type")
        if msg_type == "text":
            user_text = msg["text"]["body"].strip()
        elif msg_type == "interactive":
            inter = msg.get("interactive", {})
            if inter.get("type") == "list_reply":
                interactive_id = inter["list_reply"]["id"]
            elif inter.get("type") == "button_reply":
                interactive_id = inter["button_reply"]["id"]

        # --------- If user is in appointment flow ----------
        if from_number in states:
            st = states[from_number]
            step = st["step"]

            if step == "ASK_NAME":
                if user_text:
                    st["name"] = user_text
                    st["step"] = "ASK_PHONE"
                    send_text(from_number, "Great ✅ Please share your *phone number* (for calling):")
                    return {"status": "ok"}
                else:
                    send_text(from_number, "Please type your *name*.")
                    return {"status": "ok"}

            if step == "ASK_PHONE":
                if user_text:
                    st["phone"] = user_text
                    st["step"] = "ASK_TIME"
                    send_text(from_number, "Good ✅ What is your *preferred time* for a call? (Example: Today 6pm / Tomorrow 11am)")
                    return {"status": "ok"}
                else:
                    send_text(from_number, "Please type your *phone number*.")
                    return {"status": "ok"}

            if step == "ASK_TIME":
                if user_text:
                    st["time"] = user_text
                    service_title = SERVICE_CATALOG.get(st["service_id"], {}).get("title", "Service")
                    confirm = (
                        f"Thanks *{st['name']}* ✅\n\n"
                        f"Service: *{service_title}*\n"
                        f"Phone: *{st['phone']}*\n"
                        f"Preferred time: *{st['time']}*\n\n"
                        "Our team will contact you.\n"
                        "If you want, share your requirement in 1 line now."
                    )
                    send_text(from_number, confirm)
                    # end flow
                    states.pop(from_number, None)
                    return {"status": "ok"}
                else:
                    send_text(from_number, "Please type your preferred *time*.")
                    return {"status": "ok"}

        # --------- Normal flow ----------
        # 1) Hi -> show list
        if user_text and user_text.lower() in ["hi", "hello", "hey", "hai"]:
            send_whatsapp(build_list_services(from_number))
            return {"status": "ok"}

        # 2) If user picked a service from list -> show details + Yes/No buttons
        if interactive_id in SERVICE_CATALOG:
            service = SERVICE_CATALOG[interactive_id]
            text = service["detail"]
            send_whatsapp(build_yes_no_buttons(from_number, text))
            # store last selected service in state (only when they click yes later)
            states[from_number] = {"step": "WAIT_BOOK", "service_id": interactive_id, "name": "", "phone": "", "time": ""}
            return {"status": "ok"}

        # 3) Handle Yes/No buttons (appointment)
        if interactive_id == "BOOK_YES":
            if from_number not in states:
                states[from_number] = {"step": "ASK_NAME", "service_id": "S_WA_BOT", "name": "", "phone": "", "time": ""}
            else:
                states[from_number]["step"] = "ASK_NAME"
            send_text(from_number, "Sure ✅ What is your *name*?")
            return {"status": "ok"}

        if interactive_id == "BOOK_NO":
            states.pop(from_number, None)
            send_text(from_number, "No problem 🙂 If you want, type *Hi* anytime to view services again.")
            return {"status": "ok"}

        # 4) Fallback
        send_text(from_number, "Type *Hi* to view our services menu.")
        return {"status": "ok"}

    except Exception as e:
        print("❌ Error:", str(e))
        return {"status": "error"}
