"""
Voice-Driven Research Reporter — entry point.

Hold the push-to-talk key, ask your question, release. Whisper transcribes
it locally, then it goes into the LangGraph agent: quick questions get a
Tavily-backed spoken answer immediately, "report on X" style questions get
handed off to the CrewAI crew, spoken as a short summary, and saved in full
under reports/.
"""

import os
import keyboard
from dotenv import load_dotenv

from audio_io import record_while_held, transcribe
from tts import speak, speak_summary
from graph import build_graph

load_dotenv()

PUSH_TO_TALK_KEY = os.getenv("PUSH_TO_TALK_KEY", "right ctrl")
THREAD_ID = "voice-session-1"  # swap for a per-user id if you add multi-user support


def main():
    print(f"Voice-Driven Research Reporter ready. Hold [{PUSH_TO_TALK_KEY}] to talk, Ctrl+C to quit.")
    app = build_graph()
    config = {"configurable": {"thread_id": THREAD_ID}}

    while True:
        keyboard.wait(PUSH_TO_TALK_KEY)
        print("Listening...")
        wav_path = record_while_held(lambda: keyboard.is_pressed(PUSH_TO_TALK_KEY))

        question = transcribe(wav_path)
        if not question:
            print("(didn't catch anything)")
            continue

        print(f"You: {question}")

        result = app.invoke({"messages": [("user", question)]}, config=config)
        answer = result["messages"][-1].content

        print(f"Assistant: {answer}\n")

        # Long CrewAI reports get a short spoken summary; the full text was
        # already saved to reports/ inside the crew_research node.
        if len(answer) > 600:
            speak_summary(answer)
        else:
            speak(answer)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
