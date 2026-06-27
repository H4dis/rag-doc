import streamlit as st
import requests
from datetime import datetime

API_URL = "http://localhost:8000"
SESSION_ID = "web_user"

st.set_page_config(
    page_title="دستیار دانشگاه پیام نور",
    page_icon="🎓",
    layout="wide"
)

# ========== سایدبار برای تاریخچه ==========
with st.sidebar:
    st.image("https://pnu.ac.ir/Images/logo.png", width=100)
    st.title("📜 تاریخچه مکالمات")

    if st.button("🗑️ پاک کردن تاریخچه"):
        requests.delete(f"{API_URL}/history/{SESSION_ID}")
        st.rerun()

    # نمایش تاریخچه
    try:
        resp = requests.get(f"{API_URL}/history/{SESSION_ID}?limit=20")
        if resp.status_code == 200:
            history = resp.json()["conversations"]
            if history:
                for h in history:
                    time = datetime.fromisoformat(h["timestamp"]).strftime("%H:%M")
                    with st.expander(f"❓ {h['question'][:40]}... ({time})"):
                        st.write(h["answer"])
            else:
                st.info("هنوز سوالی نپرسیده‌اید")
    except:
        st.warning("در حال اتصال به سرور...")

# ========== بخش اصلی چت ==========
st.title("🎓 دستیار هوشمند دانشگاه پیام نور")
st.caption("پاسخگوی سوالات شما در مورد فارغ‌التحصیلی، دروس، ثبت‌نام و ...")

# مقداردهی اولیه تاریخچه جلسه
if "messages" not in st.session_state:
    st.session_state.messages = []

# نمایش پیام‌های قبلی
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            st.caption(f"📚 برگرفته از {msg['sources']} منبع")

# ورودی سوال
if question := st.chat_input("سوال خود را بنویسید..."):
    # اضافه کردن سوال کاربر
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    # درخواست به API
    with st.chat_message("assistant"):
        with st.spinner("در حال جستجو..."):
            try:
                resp = requests.post(
                    f"{API_URL}/ask",
                    json={"question": question, "session_id": SESSION_ID},
                    timeout=30
                )

                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["answer"]
                    source_count = data["source_count"]

                    st.write(answer)
                    st.caption(f"📚 پاسخ بر اساس {source_count} منبع")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": source_count
                    })
                else:
                    st.error("خطا در دریافت پاسخ")
            except Exception as e:
                st.error(f"خطا: {str(e)}")

    st.rerun()

# ========== دکمه‌های سریع ==========
st.divider()
st.caption("📌 سوالات پیشنهادی:")
cols = st.columns(4)
questions = [
    "مراحل فارغ التحصیلی چیست؟",
    "مدارک لازم برای تسویه چیست؟",
    "چطور درخواست تسویه ثبت کنم؟",
    "هزینه فارغ التحصیلی چقدر است؟"
]

for col, q in zip(cols, questions):
    if col.button(q, use_container_width=True):
        # ارسال خودکار سوال
        st.session_state.messages.append({"role": "user", "content": q})
        st.rerun()