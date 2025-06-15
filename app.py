from flask import Flask, request, render_template
from dotenv import load_dotenv
import os, datetime, psycopg2
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage

load_dotenv()
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id SERIAL PRIMARY KEY,
            text TEXT,
            image_path TEXT,
            timestamp TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route("/")
def index():
    return "✅ LINE Bot with PostgreSQL is running."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("ERROR:", e)
        return "Error", 400
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    text = None
    image_path = None

    if isinstance(event.message, TextMessage):
        text = event.message.text

    elif isinstance(event.message, ImageMessage):
        message_id = event.message.id
        content = line_bot_api.get_message_content(message_id)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"static/images/image_{timestamp}.jpg"
        with open(filename, "wb") as f:
            f.write(content.content)
        image_path = filename

    if text or image_path:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO records (text, image_path, timestamp) VALUES (%s, %s, %s)",
                    (text, image_path, datetime.datetime.now()))
        conn.commit()
        cur.close()
        conn.close()

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ รับข้อมูลแล้ว (PostgreSQL)")
        )

@app.route("/history")
def history():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT text, image_path, timestamp FROM records ORDER BY id DESC")
    records = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("history.html", records=records)