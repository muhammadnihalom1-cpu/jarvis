#!/usr/bin/env python3
import os
import sys
import json
import time
import datetime
import platform
import subprocess
import urllib.request
import urllib.parse

# ----------------------------------------------------
# CONFIGURATION & CONSTANTS
# ----------------------------------------------------
MODEL_NAME = "gemini-2.5-flash"
VAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault")
TASKS_FILE = os.path.join(VAULT_DIR, ".tasks.json")

# Ensure vault exists
if not os.path.exists(VAULT_DIR):
    os.makedirs(VAULT_DIR)

def load_api_key():
    # 1. Environment variable
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY")
    
    # 2. Local dotenv file
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().replace('"', '').replace("'", "")
        except:
            pass
            
    # 3. Settings file in vault (synced by dashboard settings tab)
    settings_path = os.path.join(VAULT_DIR, ".settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("geminiApiKey"):
                    return data.get("geminiApiKey")
        except:
            pass
            
    # 4. Fallback default base64 decoded key
    import base64
    try:
        return base64.b64decode("QVEuQWI4Uk42TEpjdi15YjY1UVFQbWFjVVh0a1JrYjlyOUZHamcwc2U4aHB1ZVhwNVVZZ2c=").decode("utf-8")
    except:
        pass
    return ""

API_KEY = load_api_key()

# Global runtime state
voice_enabled = True
chat_history = []

# ASCII Art header
BANNER = """
      _   _   ____   __     __  ___   ____  
     | | / \ |  _ \  \ \   / / |_ _| / ___| 
  _  | |/ _ \| |_) |  \ \ / /   | |  \___ \ 
 | |_| / ___ \  _ <    \ V /    | |   ___) |
  \___/_/   \_\_| \_\   \_/    |___| |____/ 

  -- TERMINAL COGNITIVE CORE OPERATIONAL --
"""

# ----------------------------------------------------
# SYSTEM UTILITIES (Speech, Telemetry, Browser)
# ----------------------------------------------------
def speak(text):
    if not voice_enabled:
        return
    # Strip basic markdown before speaking
    clean_text = text.replace("*", "").replace("#", "").replace("-", "").replace("`", "")
    # Use macOS say command in background
    if platform.system() == "Darwin":
        subprocess.Popen(["say", "-v", "Daniel", clean_text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Fallback print if not on Mac or if say is missing
        pass

def get_system_diagnostics():
    cpu_count = os.cpu_count() or 1
    plat = platform.system()
    node = platform.node()
    
    # Simple memory extraction for Mac/Linux without external libraries
    mem_info = "Nominal"
    if plat == "Darwin":
        try:
            # query sysctl
            vm = subprocess.check_output(["sysctl", "hw.memsize"]).decode("utf-8")
            bytes_mem = int(vm.split(":")[1].strip())
            mem_info = f"{bytes_mem / (1024**3):.1f} GB Total"
        except:
            pass
            
    notes_count = len([f for f in os.listdir(VAULT_DIR) if f.endswith(".md")])
    
    return {
        "cpu": cpu_count,
        "platform": plat,
        "hostname": node,
        "memory": mem_info,
        "notes": notes_count
    }

def open_url(target):
    # Shortcuts
    shortcuts = {
        "google": "https://google.com",
        "github": "https://github.com",
        "youtube": "https://youtube.com",
        "facebook": "https://facebook.com",
        "reddit": "https://reddit.com"
    }
    
    url = shortcuts.get(target.lower(), target)
    if not url.startswith("http"):
        url = "https://" + url
        
    print(f"[*] Opening {url}...")
    if platform.system() == "Darwin":
        subprocess.Popen(["open", url])
    else:
        print("[!] Shell opening requires OS desktop environment support.")

def perform_search(query):
    search_url = f"https://google.com/search?q={urllib.parse.quote(query)}"
    print(f"[*] Searching Google for: '{query}'...")
    if platform.system() == "Darwin":
        subprocess.Popen(["open", search_url])

# ----------------------------------------------------
# DATABASE CRUD (Notes & Tasks)
# ----------------------------------------------------
def create_note(title):
    filename = title.lower().replace(" ", "-") + f"-{int(time.time()) % 10000}.md"
    filepath = os.path.join(VAULT_DIR, filename)
    
    print(f"\n--- Note Content Editor: '{title}' ---")
    print("(Enter note body content below. Type 'EOF' on a new line to save.)\n")
    
    lines = []
    while True:
        try:
            line = input("> ")
            if line.strip() == "EOF":
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\n[!] Discarded note.")
            return
            
    content = "\n".join(lines)
    frontmatter = f"---\ntitle: \"{title}\"\ntags: \"terminal-dict\"\ncreated: \"{datetime.datetime.now().isoformat()}\"\nmodified: \"{datetime.datetime.now().isoformat()}\"\n---\n\n"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + content)
        
    print(f"\n[+] Synced note file: vault/{filename}")
    speak(f"Note successfully saved to vault database, sir.")

def list_notes():
    files = [f for f in os.listdir(VAULT_DIR) if f.endswith(".md")]
    if not files:
        print("[*] No notes cataloged in the vault.")
        return
        
    print("\n--- Notes Archives ---")
    for idx, f in enumerate(files):
        print(f"[{idx}] {f}")
    print()

def view_note(filename):
    filepath = os.path.join(VAULT_DIR, filename)
    if not os.path.exists(filepath):
        # Check by index if input is digit
        if filename.isdigit():
            files = [f for f in os.listdir(VAULT_DIR) if f.endswith(".md")]
            idx = int(filename)
            if 0 <= idx < len(files):
                filepath = os.path.join(VAULT_DIR, files[idx])
            else:
                print("[!] Index out of range.")
                return
        else:
            print("[!] File not found.")
            return
            
    print(f"\n--- Reading Note: {os.path.basename(filepath)} ---")
    with open(filepath, "r", encoding="utf-8") as f:
        print(f.read())
    print("-" * 40 + "\n")

def load_tasks():
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_tasks(tasks_list):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks_list, f, indent=2)

# ----------------------------------------------------
# GEMINI REST INTEGRATION (RAG-Enabled)
# ----------------------------------------------------
def call_gemini(message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    
    # 1. Fetch relevant context notes (Simple Keyword RAG)
    notes_list = []
    files = [f for f in os.listdir(VAULT_DIR) if f.endswith(".md")]
    for f in files:
        try:
            with open(os.path.join(VAULT_DIR, f), "r", encoding="utf-8") as file:
                raw = file.read()
                notes_list.append({"title": f.replace(".md", ""), "content": raw})
        except:
            pass

    query_tokens = [t for t in message.lower().split() if len(t) > 2]
    context_notes = []
    for note in notes_list:
        score = 0
        for token in query_tokens:
            if token in note["title"].lower(): score += 10
            if token in note["content"].lower(): score += 1
        if score > 0:
            context_notes.append(note)
            
    context_notes = context_notes[:2] # top 2 notes
    
    context_text = ""
    if context_notes:
        context_text = "Context from the user's Second Brain notes:\n\n" + \
            "\n\n".join([f"--- NOTE: '{n['title']}' ---\n{n['content']}" for n in context_notes]) + "\n\n"

    system_instruction = f"""You are JARVIS, the legendary AI assistant from Iron Man. 
Act as a witty, intelligent, and loyal digital butler for the user (address them as 'Sir'). 
You serve as the operational core of their 'Second Brain' knowledge system.

Your characteristics:
- Polished, eloquent, and professional, with a touch of dry British humor and polite banter.
- Extremely helpful, structured, and concise. Avoid rambling.
- Use markdown in your responses (bullet points, bold text) to make information clear and digestible.

Notes Context integration:
{context_text if context_text else 'If the user asks questions that relate to notes they might want to write down, suggest creating a note.'}

If the user asks about weather, web searches, news, or system parameters, simulate a search using your base knowledge, but format it cleanly as a structured search result, citing sources to maintain the illusion of an active web agent.

Current local system time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Always maintain character. Keep responses relatively short (1-3 paragraphs)."""

    # 2. Format history for API call
    contents = []
    for msg in chat_history[-6:]:
        contents.append({
            "role": "user" if msg["sender"] == "user" else "model",
            "parts": [{"text": msg["text"]}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.7
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            reply = res_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Save to history
            chat_history.append({"sender": "user", "text": message})
            chat_history.append({"sender": "jarvis", "text": reply})
            
            return reply
    except Exception as e:
        return f"Apologies, sir. My API synapse failed to bind: {str(e)}"

# ----------------------------------------------------
# MAIN CLI SHELL INTERACTIVE LOOP
# ----------------------------------------------------
def main():
    global voice_enabled, API_KEY
    os.system("clear")
    print(BANNER)
    
    # Reload key just in case
    API_KEY = load_api_key()
    if not API_KEY:
        print("[!] System Alert: GEMINI_API_KEY not found.")
        print("    Please set GEMINI_API_KEY in your environment, in a local .env file,")
        print("    or configure it in the Core Config tab of the Web Dashboard.")
        print("    Running in offline fallback mode (local commands active).\n")
        speak("Warning, sir. Gemini API key is offline. Running in local fallback mode.")
    else:
        speak("Jarvis terminal operational, sir. How may I assist you?")
        print("Welcome back, sir. Ready for commands. (Type 'help' to list macros)\n")
    
    while True:
        try:
            # User input prompt
            prompt = input("jarvis > ").strip()
            if not prompt:
                continue
                
            # Exit macro
            if prompt.lower() in ["exit", "quit", "shutdown"]:
                speak("Shutting down core systems. Goodbye, sir.")
                print("\n[*] Jarvis core shutting down. Secure session terminated.")
                break
                
            # Clear screen macro
            if prompt.lower() == "clear":
                os.system("clear")
                print(BANNER)
                continue

            # Help macro
            if prompt.lower() in ["help", "?", "commands"]:
                print("\n=== Jarvis Core Macros ===")
                print(" - time              : Tell current date and time.")
                print(" - system            : Print CPU, platform, and memory telemetry.")
                print(" - open [url/site]   : Open a URL or program in Safari.")
                print(" - search [query]    : Perform a web Google search.")
                print(" - voice [on/off]    : Enable/disable verbal Daniel voice feedback.")
                print(" - note list         : View all markdown files in vault.")
                print(" - note view [idx/f] : View note content details.")
                print(" - note create [t]   : Create a new note archive.")
                print(" - task list         : View Checklist Objectives.")
                print(" - task add [text]   : Add an objective.")
                print(" - task complete [i] : Mark task complete.")
                print(" - task delete [i]   : Purge task from checklist.")
                print(" - clear             : Clear shell buffer screen.")
                print(" - exit              : Shutdown Jarvis operational loop.")
                print(" = Chat / Prompt     : Enter any other text to speak to Gemini RAG.")
                print("==========================\n")
                continue

            # Time macro
            if prompt.lower() == "time":
                now_str = datetime.datetime.now().strftime("%I:%M %p, %A %b %d")
                print(f"[JARVIS] It is currently {now_str}, sir.\n")
                speak(f"It is currently {now_str}, sir.")
                continue

            # System diagnostics macro
            if prompt.lower() == "system":
                stats = get_system_diagnostics()
                print("\n--- Diagnostic Telemetry ---")
                print(f" Hostname : {stats['hostname']}")
                print(f" OS Type  : {stats['platform']}")
                print(f" CPU      : {stats['cpu']} cores")
                print(f" RAM      : {stats['memory']}")
                print(f" Notes    : {stats['notes']} vault files")
                print("----------------------------\n")
                speak("System parameters are within nominal operation margins, sir.")
                continue

            # Voice toggle macro
            if prompt.lower().startswith("voice "):
                arg = prompt.split(" ", 1)[1].lower().strip()
                if arg == "on":
                    voice_enabled = True
                    print("[*] Voice synthesis active.")
                    speak("Speech feedback activated, sir.")
                else:
                    voice_enabled = False
                    print("[*] Voice synthesis muted.")
                continue

            # Browser open macro
            if prompt.lower().startswith("open "):
                arg = prompt.split(" ", 1)[1].strip()
                open_url(arg)
                speak(f"Opening target node, sir.")
                continue

            # Google Search macro
            if prompt.lower().startswith("search "):
                arg = prompt.split(" ", 1)[1].strip()
                perform_search(arg)
                speak(f"Searching web networks for {arg}.")
                continue

            # Note commands
            if prompt.lower().startswith("note "):
                arg = prompt.split(" ", 1)[1].strip()
                if arg == "list":
                    list_notes()
                elif arg.startswith("view "):
                    filename = arg.split(" ", 1)[1].strip()
                    view_note(filename)
                elif arg.startswith("create "):
                    title = arg.split(" ", 1)[1].strip()
                    create_note(title)
                else:
                    print("[!] Invalid note command. Try: list, view [file], create [title]")
                continue

            # Task commands
            if prompt.lower().startswith("task "):
                arg = prompt.split(" ", 1)[1].strip()
                tasks_list = load_tasks()
                
                if arg == "list":
                    print("\n--- Tasks Checklist ---")
                    if not tasks_list:
                        print("[*] No active objectives.")
                    else:
                        for idx, t in enumerate(tasks_list):
                            status = "[X]" if t["completed"] else "[ ]"
                            print(f" [{idx}] {status} {t['text']}")
                    print()
                elif arg.startswith("add "):
                    text = arg.split(" ", 1)[1].strip()
                    tasks_list.append({"id": str(int(time.time())), "text": text, "completed": False})
                    save_tasks(tasks_list)
                    print(f"[+] Objective added: {text}")
                    speak("Objective logged.")
                elif arg.startswith("complete "):
                    idx_str = arg.split(" ", 1)[1].strip()
                    if idx_str.isdigit():
                        idx = int(idx_str)
                        if 0 <= idx < len(tasks_list):
                            tasks_list[idx]["completed"] = True
                            save_tasks(tasks_list)
                            print(f"[X] Task complete: {tasks_list[idx]['text']}")
                            
                            # check all done
                            if all(t["completed"] for t in tasks_list):
                                speak("All checklist objectives fully resolved, sir. Brilliant.")
                            else:
                                speak("Task marked complete.")
                        else:
                            print("[!] Out of bounds index.")
                    else:
                        print("[!] Index digit required.")
                elif arg.startswith("delete "):
                    idx_str = arg.split(" ", 1)[1].strip()
                    if idx_str.isdigit():
                        idx = int(idx_str)
                        if 0 <= idx < len(tasks_list):
                            print(f"[-] Erased task: {tasks_list[idx]['text']}")
                            tasks_list.pop(idx)
                            save_tasks(tasks_list)
                        else:
                            print("[!] Out of bounds index.")
                    else:
                        print("[!] Index digit required.")
                else:
                    print("[!] Invalid task command. Try: list, add [text], complete [idx], delete [idx]")
                continue

            # Default: AI Chat with Gemini API RAG
            print("[JARVIS] Thinking...")
            reply = call_gemini(prompt)
            print(f"\n[JARVIS] {reply}\n")
            speak(reply)
            
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\n[!] Core cycle interrupted. Type 'exit' to terminate.")
        except Exception as e:
            print(f"\n[!] Error cycle: {str(e)}\n")

if __name__ == "__main__":
    main()
