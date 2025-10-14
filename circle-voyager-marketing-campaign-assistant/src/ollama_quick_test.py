#!/usr/bin/env python3
"""
Quick sanity test for a local Ollama server.
Tries the official 'ollama' client first, then falls back to raw HTTP.
"""

MODEL = "llama3.1"

def run_with_client():
    from ollama import Client
    client = Client(host="http://localhost:11434")
    messages = [
        {"role": "system", "content": "You are concise."},
        {"role": "user", "content": "Say hi in exactly five words."}
    ]
    r = client.chat(model=MODEL, messages=messages)
    print("OLLAMA CLIENT:", r["message"]["content"].strip())

def run_with_http():
    import requests
    BASE = "http://localhost:11434"
    payload = {"model": MODEL, "prompt": "Say hi in exactly five words.", "stream": False}
    r = requests.post(f"{BASE}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    print("HTTP FALLBACK:", r.json().get("response", "").strip())

if __name__ == "__main__":
    try:
        run_with_client()
    except Exception as e1:
        print(f"[info] ollama client path failed: {e1}")
        try:
            run_with_http()
        except Exception as e2:
            import sys, traceback
            print("[error] both client and HTTP calls failed.", file=sys.stderr)
            print(" client error:", e1, file=sys.stderr)
            print(" http error  :", e2, file=sys.stderr)
            sys.exit(1)
