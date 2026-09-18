"""
Push-to-talk voice agent: mic -> Whisper (speech-to-text) -> LangGraph
agent (with web search) -> pyttsx3 (text-to-speech).

Setup:
    pip install -r requirements.txt
    Install ffmpeg (required by Whisper) and make sure it's on your PATH.
    Put GROQ_API_KEY and TAVILY_API_KEY in a .env file in this folder.

Run:
    python voice_agent.py
"""

from langchain_core.messages import HumanMessage, SystemMessage
import pyttsx3
import whisper

from recorder import record_on_spacebar, SAMPLE_RATE
from agent import graph, SYSTEM_PROMPT

CONFIG = {"configurable": {"thread_id": "voice-session-1"}}


def speak(engine, text: str):
    engine.say(text)
    engine.runAndWait()


def main():
    print("Loading Whisper model (this only happens once)...")
    stt_model = whisper.load_model("base")  # try "small"/"medium" for better accuracy

    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", 175)

    first_turn = True

    while True:
        audio = record_on_spacebar()
        if audio is None:
            print("Goodbye!")
            break
        if audio.size == 0:
            continue

        result = stt_model.transcribe(audio, fp16=False)
        user_text = result["text"].strip()
        if not user_text:
            print("(didn't catch that, try again)")
            continue

        print(f"You said: {user_text}")

        messages = []
        if first_turn:
            messages.append(SystemMessage(content=SYSTEM_PROMPT))
            first_turn = False
        messages.append(HumanMessage(content=user_text))

        response = graph.invoke({"messages": messages}, CONFIG)
        reply = response["messages"][-1].content

        print(f"Assistant: {reply}")
        speak(tts_engine, reply)


if __name__ == "__main__":
    main()
