#!/usr/bin/env python3
"""Experimenteller, vom Host geführter Gemma-Projekttest. Quelltexte erzeugt das Modell; der Host führt feste Datei-/Testschritte aus."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ALLOWED = {"app.py", "test_app.py", "README.md"}
SCOPE = "v-mind-test"
TASK = """Erstelle einen kleinen deutschen Aufgabenplaner in Python mit ausschließlich der Standardbibliothek.
Dateien: app.py, test_app.py, README.md. app.py exportiert TaskStore(path) mit add(text)->int,
list()->list[dict], done(id)->None und remove(id)->None. Jede Aufgabe hat id:int, text:str, done:bool.
Speichere Aufgaben dauerhaft in JSON. IDs steigen auch nach Löschungen weiter an.
Leerer Text und unbekannte IDs führen zu ValueError. Beschädigte vorhandene JSON-Daten führen
zu ValueError und dürfen nicht überschrieben werden. CLI: python3 app.py --file DATEI add TEXT,
list, done ID oder remove ID. list zeigt pro Aufgabe ID [ ] TEXT bzw. ID [x] TEXT.
CLI-Fehler müssen einen von null verschiedenen Exitcode liefern. Erstelle aussagekräftige
unittest-Tests mit temporären Dateien und eine deutsche README. Nutze V-Mind für Planung,
Entscheidungen und tatsächlich ausgeführte Tests. Behaupte keine ungeprüften Ergebnisse."""

SCHEMA = {"type":"object","properties":{
    "tool":{"type":"string","enum":["vmind","write_file","read_file","run_tests","finish"]},
    "args":{"type":"object","properties":{
        "op":{"type":"string"},"scope":{"type":"string"},"limit":{"type":"integer"},
        "query":{"type":"string"},"kind":{"type":"string"},"body":{"type":"string"},
        "source":{"type":"string"},"task_key":{"type":"string"},"task_status":{"type":"string"},
        "path":{"type":"string"},"content":{"type":"string"},"lines":{"type":"array","items":{"type":"string"}},"conversation_id":{"type":"string"},
        "memory_id":{"type":"integer"},"after":{"type":"integer"},"title":{"type":"string"}
    },"additionalProperties":False}},"required":["tool","args"],"additionalProperties":False}
CONTRACT = """
Host-Werkzeuge für diesen Test: Antworte ausschließlich mit einem JSON-Werkzeugaufruf
nach dem vorgegebenen Schema, ohne Markdown. tool=vmind: args ist eine V-Mind-Anfrage, z.B.
{\"op\":\"describe\"} oder {\"op\":\"resume\",\"scope\":\"v-mind-test\"}.
tool=write_file: args {path,lines}; lines ist ein Array einzelner Codezeilen. Nur app.py, test_app.py oder README.md. Gib vollständige kompakte Dateien ohne Platzhalter aus. app.py höchstens 90 Zeilen, test_app.py höchstens 80 Zeilen. Keine langen Kommentare oder Docstrings. Verwende für Dateien bevorzugt lines statt content, um doppelt maskierte Zeilenumbrüche zu vermeiden.
tool=read_file: args {path}. tool=run_tests: args {}; führt fest unittest -v aus.
tool=finish: args {content: kurze Zusammenfassung}; erst nach erfolgreichen Tests und Projektprotokoll.
Du hast KEIN freies Terminal, keine Webwerkzeuge und keinen Zugriff auf andere Projektordner.
Beginne jede neue Sitzung mit describe und resume. Lies bei Fortsetzung vorhandene Dateien.
Du musst die Dateien selbst per write_file erstellen; der Host führt deine Aufrufe aus.
Arbeite zügig, schreibe nicht dieselbe Planung mehrfach. Nutze stabile Aufgabenschlüssel.
Verwende keine message/session_new-Operationen: Der Host speichert das Gespräch bereits.
Bei einem Fehler korrigiere die Datei und führe Tests erneut aus. Speichere einen nächsten Schritt.
"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--model",default=None,help="Modell für einen neuen Lauf; Standard gemma-4-local:latest")
    ap.add_argument("--resume",action="store_true")
    ap.add_argument("--pause-after-write",action="store_true")
    ap.add_argument("--turns",type=int,default=24)
    opt=ap.parse_args()
    root=Path(opt.root).resolve(strict=True)
    meta=root/".vmind";meta.mkdir(exist_ok=True)
    database=meta/"memory.db"
    def vmind(request):
        request=dict(request)
        if request.get("op") in {"resume","recall","propose","pending","stats","journal","log","sessions"}:
            if request.get("scope",SCOPE)!=SCOPE: raise ValueError("Falscher Projektbereich")
            request["scope"]=SCOPE
        p=subprocess.run(["vmind","serve",str(database)],input=json.dumps(request)+"\n",capture_output=True,text=True,timeout=15,check=True)
        result=json.loads(p.stdout)
        if not result["ok"]: raise ValueError(result["error"])
        return result["data"]
    statefile=meta/"host.json"
    if not opt.resume:
        if statefile.exists() or any((root/name).exists() for name in ALLOWED):
            raise ValueError("Testprojekt existiert bereits; --resume verwenden")
        subprocess.run(["vmind","init",str(database)],check=True,capture_output=True,text=True)
        session=vmind({"op":"session_new","scope":SCOPE,"title":"Gemma erstellt Aufgabenplaner"})["conversation_id"]
        state={"session":session,"model":opt.model or "gemma-4-local:latest","generation_calls":0}
        statefile.write_text(json.dumps(state,indent=2))
        vmind({"op":"log","kind":"goal","body":TASK,"source":"Vom Nutzer autorisierter, von Codex konkretisierter Gemma-Projektauftrag"})
        user="Lade zuerst describe und resume. Erstelle danach das im Projektziel beschriebene Programm."
    else:
        state=json.loads(statefile.read_text());session=state["session"]
        user="Der Host wurde beendet und neu gestartet. Lade zuerst describe und resume für v-mind-test. Prüfe die bereits gespeicherten Arbeitsschritte und Dateien. Führe das angefangene Projekt zu Ende, teste es und protokolliere das Ergebnis."
    vmind({"op":"message","conversation_id":session,"role":"user","content":user})
    shared=Path(__file__).resolve().parents[1]/"prompts/start.de.md"
    system=shared.read_text()+CONTRACT
    bootstrap=set()
    read_files=set()
    for _ in range(opt.turns):
        if (meta/"pause-request").exists():
            (meta/"pause-request").unlink()
            print("Host nach laufendem Schritt angehalten; Verlauf bleibt gespeichert.",flush=True)
            return
        snapshot=vmind({"op":"resume","conversation_id":session})
        # Aktuelles vollständiges Ziel, kompakter Arbeitsstand und letzte Werkzeugantworten.
        def brief(e):
            if not e:return None
            return {k:(v[:220] if isinstance(v,str) else v) for k,v in e.items() if k in {"id","kind","task_key","task_status","body"}}
        project={"goal":snapshot["goal"],"tasks":[brief(t) for t in snapshot["tasks"][:6]],
            "next_step":brief(snapshot["next_step"]),"total_events":snapshot["total_events"],
            "files_on_disk":sorted(n for n in ALLOWED if (root/n).exists())}
        recent=[]
        for n,m in enumerate(snapshot["chat_tail"][-3:]):
            text=m["content"]
            cap=3000 if n==len(snapshot["chat_tail"][-3:])-1 and '"read_file"' in text else 800
            recent.append({"role":m["role"],"content":text[:cap]})
        def syntax_error(name):
            try:compile((root/name).read_text(),name,"exec")
            except SyntaxError as error:return str(error)
            return None
        if "describe" not in bootstrap:
            instruction="Rufe jetzt ausschließlich vmind describe auf."
        elif "resume" not in bootstrap:
            instruction="describe war erfolgreich. Rufe jetzt genau einmal vmind resume für v-mind-test auf."
        elif not (root/"app.py").exists():
            instruction="describe und resume wurden in dieser Sitzung erfolgreich abgeschlossen. Wiederhole sie nicht. Erstelle jetzt app.py mit write_file entsprechend dem vollständigen Projektziel."
        elif "app.py" not in read_files:
            instruction='Projektstand ist geladen. Führe genau {"tool":"read_file","args":{"path":"app.py"}} aus. read_file ist ein eigenes Werkzeug, KEINE vmind-Operation.'
        elif syntax_error("app.py"):
            instruction="Erstelle jetzt app.py vollständig neu als kompakte korrekte Datei mit write_file und lines-Array (höchstens 90 Zeilen, ohne Docstrings). Syntaxfehler: "+syntax_error("app.py")+". Erfülle alle Anforderungen aus goal, besonders next_id persistent, list liefert dicts, unbekannte IDs ValueError."
        elif not (root/"test_app.py").exists():
            instruction="Erstelle jetzt test_app.py mit write_file, passend zur gelesenen Implementierung und allen Anforderungen des gespeicherten Projektziels."
        elif syntax_error("test_app.py"):
            instruction="Erstelle jetzt test_app.py vollständig neu mit write_file und lines-Array (höchstens 65 Zeilen). Keine wörtlichen Backslash-n für Zeilenumbrüche. Keine langen Kommentare. Syntaxfehler: "+syntax_error("test_app.py")+". Teste die echte Spezifikation aus goal."
        elif not (root/"README.md").exists():
            instruction="Erstelle jetzt README.md auf Deutsch mit write_file. Beschreibe CLI-Befehle und Testaufruf, behaupte noch keine bestandenen Tests."
        elif not (meta/"last-tests.json").exists():
            instruction="Dateien sind vorhanden. Führe jetzt run_tests aus."
        else:
            last=json.loads((meta/"last-tests.json").read_text())
            if last["exit_code"]!=0 or last.get("tests_run",0)<1:
                instruction="Die Tests sind fehlgeschlagen. Korrigiere jetzt die fehlerhafte Datei per write_file mit lines-Array. Halte app.py unter 90 und Tests unter 80 Zeilen, ohne lange Kommentare. Prüfe alle Anforderungen im goal: list liefert dicts, unbekannte IDs ValueError, next_id wird dauerhaft gespeichert. Teste niemals absichtlich falsches Verhalten als korrekt. Tatsächliche Fehler: "+last["stderr"][-1600:]
            elif not any(t["task_key"]=="aufgabenplaner" and t["task_status"]=="done" for t in snapshot["tasks"]):
                instruction="Tests sind tatsächlich bestanden. Protokolliere jetzt mit vmind log kind task, task_key aufgabenplaner, task_status done, body Zusammenfassung und source tatsächliches Testergebnis."
            elif not snapshot["next_step"]:
                instruction="Tests und Erledigt-Status sind gespeichert. Hinterlege jetzt vmind log kind next_step mit dem nächsten sinnvollen Schritt und Quelle."
            else:
                instruction="Dateien, erfolgreiche Tests und Projektprotokoll sind vorhanden. Verwende jetzt finish mit einer kurzen ehrlichen Zusammenfassung."
        payload={"model":state["model"],"system":system,"prompt":json.dumps({
            "vmind_runtime":{"mode":"tools","scope":SCOPE,"conversation_id":session,
                "conversation_persistence":"host_managed","tools_available":True,"terminal_available":False},
            "project_context":project,"recent_messages":recent,"instruction":instruction},ensure_ascii=False),
            "stream":False,"think":False,"format":SCHEMA,"options":{"num_ctx":8192,"num_predict":6144,"temperature":0.1}}
        file_target=None
        for name in ["app.py","test_app.py","README.md"]:
            if instruction.startswith("Erstelle jetzt "+name):file_target=name
        if instruction.startswith("Die Tests sind fehlgeschlagen"):
            file_target="test_app.py" if last.get("tests_run",0)==0 or "self.self" in last.get("stderr","") else "app.py"
        if file_target and (meta/"review.json").exists():
            override=json.loads((meta/"review.json").read_text()).get("repair_target")
            if override in ALLOWED and instruction.startswith("Die Tests sind fehlgeschlagen"):file_target=override
        if file_target:
            payload.pop("format",None)
            payload["system"]=shared.read_text()+"\nFür diesen Host-Schritt bist du Dateigenerator. Gib ausschließlich den vollständigen Inhalt der angeforderten Datei aus, ohne Markdown, ohne Werkzeug-JSON, ohne Erklärungen. Der Host schreibt die Datei und protokolliert das Ergebnis. Schreibe kompakten korrekten Python-Code ohne unnötige Kommentare."
            file_context={"vmind_runtime":{"mode":"context_only","scope":SCOPE,"tools_available":False,"conversation_persistence":"host_managed"},
                "project_goal":snapshot["goal"],"target_file":file_target,"instruction":instruction}
            if file_target=="test_app.py":file_context["current_app"]=(root/"app.py").read_text()
            if file_target=="app.py" and (meta/"last-tests.json").exists():
                file_context["test_errors"]=json.loads((meta/"last-tests.json").read_text())["stderr"][-1800:]
            if (meta/"review.json").exists():file_context["external_review"]=json.loads((meta/"review.json").read_text())
            payload["prompt"]=json.dumps(file_context,ensure_ascii=False)
            payload["options"]["num_predict"]=3000
        origin="gemma" if file_target else "host"
        if file_target:
            req=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req,timeout=240) as response:generated=json.load(response)
            if not generated.get("done") or generated.get("done_reason")=="length":
                with (meta/"incomplete-generations.jsonl").open("a") as f:f.write(json.dumps(generated,ensure_ascii=False)+"\n")
                raise RuntimeError("Modellantwort unvollständig; kein Werkzeug ausgeführt")
            raw=generated["response"]
            vmind({"op":"message","conversation_id":session,"role":"assistant","content":raw})
            state["generation_calls"]+=1
            statefile.write_text(json.dumps(state,indent=2))
            source=raw.strip()
            if source.startswith("```"):source=source.split("\n",1)[1].rsplit("```",1)[0].rstrip()
            action={"tool":"write_file","args":{"path":file_target,"content":source+"\n"}}
        else:
            generated={}
            if "describe" not in bootstrap:action={"tool":"vmind","args":{"op":"describe"}}
            elif "resume" not in bootstrap:action={"tool":"vmind","args":{"op":"resume"}}
            elif "app.py" not in read_files:action={"tool":"read_file","args":{"path":"app.py"}}
            elif not (meta/"last-tests.json").exists():action={"tool":"run_tests","args":{}}
            elif not any(t["task_key"]=="aufgabenplaner" and t["task_status"]=="done" for t in snapshot["tasks"]):
                action={"tool":"vmind","args":{"op":"log","kind":"task","task_key":"aufgabenplaner","task_status":"done",
                    "body":"Gemma hat app.py, test_app.py und README.md erstellt; die vom Host ausgeführten Modelltests sind bestanden. Unabhängige Abnahme steht noch aus.",
                    "source":"Host-Testprotokoll: "+str(last["tests_run"])+" Tests, Exitcode "+str(last["exit_code"])}}
            elif not snapshot["next_step"]:action={"tool":"vmind","args":{"op":"log","kind":"next_step","body":"Unabhängige Abnahme der Anforderungen durch Codex ausführen; Fehler als Rückmeldung an Gemma geben.","source":"Testhost nach bestandenem Modell-Testlauf"}}
            else:action={"tool":"finish","args":{"content":"Dateien von Gemma erstellt; Modelltests bestanden. Unabhängige Abnahme folgt."}}
            vmind({"op":"message","conversation_id":session,"role":"tool","content":json.dumps({"host_dispatch":action},ensure_ascii=False)})
        tool=action["tool"];args=action["args"]
        # Einige Modelle benennen den Werkzeug-Namensraum statt des konkreten Werkzeugs.
        if tool=="vmind" and args.get("op") in {"read_file","write_file","run_tests","finish"}:
            tool=args.pop("op")
            action={"tool":tool,"args":args}
        print(f"{origin}-Schritt ({state['generation_calls']} Modellaufrufe): {tool} {args.get('op',args.get('path',''))}",flush=True)
        wrote=False;finished=False
        try:
            if tool=="vmind":
                if args.get("op") not in {"describe","resume","recall","get","journal","log","pending","stats"}:
                    raise ValueError("Operation in diesem Test nicht freigegeben")
                if args.get("op")=="resume": args["conversation_id"]=session
                if args.get("op")=="log" and args.get("task_status")=="done":
                    test=json.loads((meta/"last-tests.json").read_text())
                    if test["exit_code"]!=0 or test.get("tests_run",0)<1:raise ValueError("Erledigt-Meldung ohne bestandene Tests")
                result=vmind(args)
                if args.get("op") in {"describe","resume"}:bootstrap.add(args["op"])
                if args.get("op")=="resume":
                    result["chat_tail"]=[{"id":m["id"],"role":m["role"],"content":m["content"][:600]} for m in result["chat_tail"][-3:] if m["role"]!="tool"]
            elif tool in {"read_file","write_file"}:
                name=args["path"]
                if name not in ALLOWED: raise ValueError("Datei außerhalb der freigegebenen Liste")
                path=root/name
                if path.is_symlink() or path.resolve().parent!=root: raise ValueError("Ungültiger Dateipfad")
                if tool=="read_file":
                    result={"path":name,"content":path.read_text()}
                    read_files.add(name)
                else:
                    content="\n".join(args["lines"])+"\n" if "lines" in args else args["content"]
                    if len(content.encode())>100000: raise ValueError("Datei zu groß")
                    path.write_text(content)
                    result={"path":name,"bytes":len(content.encode()),"sha256":hashlib.sha256(content.encode()).hexdigest()}
                    vmind({"op":"log","kind":"note","body":"Datei durch Gemma erstellt/aktualisiert: "+name+" SHA256 "+result["sha256"],"source":"Vom Host bestätigter write_file-Aufruf"})
                    (meta/"last-tests.json").unlink(missing_ok=True)
                    wrote=True
            elif tool=="run_tests":
                if not (root/"test_app.py").is_file(): raise ValueError("test_app.py fehlt")
                p=subprocess.run([sys.executable,"-I","-m","unittest","discover","-v","-s",str(root),"-p","test_app.py"],cwd=root,capture_output=True,text=True,timeout=30)
                match=re.search(r"Ran (\d+) tests?",p.stderr)
                result={"exit_code":p.returncode,"tests_run":int(match.group(1)) if match else 0,"stdout":p.stdout[-10000:],"stderr":p.stderr[-10000:]}
                (meta/"last-tests.json").write_text(json.dumps(result,indent=2))
            elif tool=="finish":
                last=json.loads((meta/"last-tests.json").read_text())
                if last["exit_code"]!=0 or last.get("tests_run",0)<1 or not all((root/n).is_file() for n in ALLOWED):
                    raise ValueError("Projekt oder erfolgreiche Tests fehlen")
                result={"summary":args.get("content",""),"tests_exit_code":last["exit_code"]};finished=True
                (meta/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
            else: raise ValueError("Unbekanntes Werkzeug")
            response={"ok":True,"tool":tool,"result":result}
        except (ValueError,OSError,subprocess.SubprocessError) as error:
            response={"ok":False,"tool":tool,"error":str(error)}
        vmind({"op":"message","conversation_id":session,"role":"tool","content":json.dumps(response,ensure_ascii=False)[:30000]})
        with (meta/"trace.jsonl").open("a") as trace:
            trace.write(json.dumps({"time":time.time(),"model":state["model"],"origin":origin,"action":action,"response":response,
                "prompt_eval_count":generated.get("prompt_eval_count"),"eval_count":generated.get("eval_count")},ensure_ascii=False)+"\n")
        if response["ok"] and tool=="run_tests":print("Tests: Exitcode",response["result"]["exit_code"],flush=True)
        if finished:return
        if wrote and opt.pause_after_write:
            print("Host planmäßig nach erstem Dateischreibvorgang beendet. Fortsetzung mit --resume.",flush=True)
            return
    raise RuntimeError("Maximale Werkzeugschritte erreicht; Verlauf ist gespeichert")

if __name__=="__main__":main()
