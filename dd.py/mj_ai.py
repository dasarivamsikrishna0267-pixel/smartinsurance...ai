import os
from openai import OpenAI
import pyttsx3
import speech_recognition as sr

# ================= API KEY =================
# Set in terminal: setx OPENAI_API_KEY "your_key_here"
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ API key not found. Set OPENAI_API_KEY first.")
    exit()

client = OpenAI(api_key=api_key)

# ================= VOICE =================
engine = pyttsx3.init()
recognizer = sr.Recognizer()

def speak(text):
    print("MJ:", text)
    try:
        engine.say(text)
        engine.runAndWait()
    except:
        pass

# ================= MJ PERSONALITY =================
MJ_PERSONALITY = """
You are MJ (Michelle Jones-Watson).
Sarcastic, witty, smart, short replies (1–2 lines).
"""

# ================= AI RESPONSE =================
def ask_mj(user_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": MJ_PERSONALITY},
                {"role": "user", "content": user_input}
            ],
            timeout=10
        )
        return response.choices[0].message.content
    except Exception as e:
        print("⚠️ API Error:", e)
        return "Something went wrong."

# ================= LISTEN =================
def listen():
    try:
        with sr.Microphone() as source:
            print("🎤 Speak (5 sec)...")
            recognizer.adjust_for_ambient_noise(source, duration=1)

            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio)

            print("You:", text)
            return text

    except sr.WaitTimeoutError:
        return input("⌨️ Type instead: ")
    except:
        return input("⌨️ Mic error, type: ")

# ================= MAIN =================
print("🤖 MJ AI Ready (type 'exit' to stop)\n")

while True:
    user_input = listen()

    if not user_input:
        continue

    if user_input.lower() in ["exit", "quit", "stop"]:
        speak("Finally. Peace.")
        break

    reply = ask_mj(user_input)
    speak(reply)
