#!/usr/bin/env python3
"""Prüft Wiederverwendung validierter V-Mind-Referenzen durch Gemma E2B, keine Neugenerierung."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference-root",required=True)
    ap.add_argument("--output-root",required=True)
    opt=ap.parse_args()
    reference=Path(opt.reference_root).resolve(strict=True)
    output=Path(opt.output_root).resolve()
    output.mkdir()
    meta=output/".vmind";meta.mkdir()
    database=reference/".vmind/memory.db"
    scope="v-mind-test-e2b"
    def vmind(request):
        p=subprocess.run(["vmind","serve",str(database)],input=json.dumps(request,ensure_ascii=False)+"\n",text=True,capture_output=True,check=True,timeout=15)
        result=json.loads(p.stdout)
        if not result["ok"]:raise RuntimeError(result["error"])
        return result["data"]
    session=vmind({"op":"session_new","scope":scope,"title":"E2B nutzt geprüfte 12B-Lösung"})["conversation_id"]
    vmind({"op":"log","scope":scope,"kind":"goal","body":"Dasselbe Aufgabenplaner-Projekt mit E2B durch Abruf und ausdrückliche Wiederverwendung geprüfter V-Mind-Referenzdateien erstellen. Kein Nachweis für selbstständige Neuentwicklung oder geänderte Modellgewichte.","source":"Nutzerfrage: Kann E2B nach der geprüften 12B-Lösung mit V-Mind davon profitieren?"})
    vmind({"op":"log","scope":scope,"kind":"task","task_key":"referenz-wiederverwenden","task_status":"in_progress","body":"E2B soll passende validierte app.py und test_app.py auswählen; Host schreibt exakt die gewählte gespeicherte Lösung. Danach echte Tests.","source":"Kontrollierter Wiederverwendungstest"})
    shared=Path(__file__).resolve().parents[1]/"prompts/start.de.md"
    system=shared.read_text()+"\nKonkretes Host-Werkzeug dieses Tests: Wähle eine geprüfte Referenz mit JSON {action: reuse, memory_id: ID, reason: Begründung}. Der Host übernimmt dann exakt deren solution als Zieldatei. Wenn keine passt, wähle action reject und memory_id 0. Du generierst hier keinen neuen Programmcode. Nur tatsächlich angezeigte IDs sind zulässig."
    choices=[]
    for name in ["app.py","test_app.py"]:
        memories=vmind({"op":"recall","scope":scope,"query":"Aufgabenplaner Referenzdatei "+name,"limit":20})["memories"]
        memories=[m for m in memories if m["problem"]=="Aufgabenplaner Referenzdatei "+name]
        if not memories:raise RuntimeError("Geprüfte Referenz fehlt")
        question="Erstelle die Datei "+name+" für denselben Aufgabenplaner durch passende geprüfte Wiederverwendung. Prüfe Name und Herkunft und entscheide."
        vmind({"op":"message","conversation_id":session,"role":"user","content":question})
        snapshot=vmind({"op":"resume","scope":scope,"conversation_id":session})
        payload={"model":"vmind-gemma4:e2b","system":system,"prompt":json.dumps({
            "vmind_runtime":{"mode":"tools","scope":scope,"conversation_id":session,"conversation_persistence":"host_managed","tools_available":True,"terminal_available":False},
            "project_goal":snapshot["goal"],"target_file":name,"memory":memories,"question":question},ensure_ascii=False),
            "stream":False,"think":False,"format":{"type":"object","properties":{
                "action":{"type":"string","enum":["reuse","reject"]},"memory_id":{"type":"integer"},"reason":{"type":"string"}},
                "required":["action","memory_id","reason"],"additionalProperties":False},
            "options":{"num_ctx":8192,"num_predict":256,"temperature":0}}
        req=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=180) as r:generated=json.load(r)
        if generated.get("done_reason")=="length":raise RuntimeError("Auswahl abgeschnitten")
        raw=generated["response"];decision=json.loads(raw)
        vmind({"op":"message","conversation_id":session,"role":"assistant","content":raw})
        selected=next((m for m in memories if m["id"]==decision["memory_id"] and m["status"]=="validated"),None)
        if decision["action"]!="reuse" or selected is None:raise RuntimeError("Keine gültige Wiederverwendung ausgewählt: "+raw)
        content=selected["solution"]
        (output/name).write_text(content)
        proof={"target":name,"memory_id":selected["id"],"decision":decision,"sha256":hashlib.sha256(content.encode()).hexdigest(),
            "model":"vmind-gemma4:e2b","origin":"Gespeicherte geprüfte Gemma-4-12B-Lösung, von E2B ausgewählt, vom Host unverändert geschrieben",
            "prompt_eval_count":generated.get("prompt_eval_count"),"eval_count":generated.get("eval_count")}
        choices.append(proof)
        vmind({"op":"message","conversation_id":session,"role":"tool","content":json.dumps({"ok":True,"written":name,"memory_id":selected["id"],"sha256":proof["sha256"]},ensure_ascii=False)})
        vmind({"op":"log","scope":scope,"kind":"note","body":"E2B wählte Wissen #"+str(selected["id"])+" für "+name+"; Host übernahm die solution unverändert. SHA256 "+proof["sha256"],"source":"Erfolgreicher Modellaufruf und Host-Dateiprüfung"})
        print("E2B wählt Wissen #"+str(selected["id"])+" für "+name,flush=True)
    (output/"verification").mkdir()
    (output/"verification/acceptance.py").write_text((reference/"verification/acceptance.py").read_text())
    runs=[]
    for title,cmd in [
        ("model_tests",[sys.executable,"-m","unittest","discover","-v","-s",str(output),"-p","test_app.py"]),
        ("independent_acceptance",[sys.executable,str(output/"verification/acceptance.py")])]:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        count=re.search(r"Ran (\d+) tests?",p.stderr)
        runs.append({"name":title,"exit_code":p.returncode,"tests_run":int(count.group(1)) if count else 0,"stdout":p.stdout,"stderr":p.stderr})
        print(title+": Exitcode "+str(p.returncode),flush=True)
    passed=all(x["exit_code"]==0 and x["tests_run"]>0 for x in runs)
    report={"passed":passed,"conversation_id":session,"database":str(database),"scope":scope,"choices":choices,"tests":runs,
        "conclusion":"Testet Abruf, Auswahl und unveränderte Wiederverwendung, keine neuen Modellfähigkeiten oder eigenständige Lösung unbekannter Varianten."}
    (meta/"reuse-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (output/"README.md").write_text("# E2B-Wiederverwendungstest\n\nGemma 4 E2B hat die von Gemma 4 12B erstellten und geprüften Dateien aus V-Mind ausgewählt. Der Host hat sie unverändert geschrieben. Dies ist Wiederverwendung, keine Neuentwicklung durch E2B.\n\nTests: `python3 -m unittest discover -v -s . -p test_app.py`\n\nUnabhängige Abnahme: `python3 verification/acceptance.py`\n\nVollständiger Prüfbericht: `.vmind/reuse-report.json`.\n")
    vmind({"op":"log","scope":scope,"kind":"task","task_key":"referenz-wiederverwenden","task_status":"done" if passed else "blocked",
        "body":"E2B wählte geprüfte Referenzen für beide Dateien; Host übernahm sie unverändert. Testergebnisse: "+json.dumps([{k:x[k] for k in ["name","exit_code","tests_run"]} for x in runs]),
        "source":str(meta/"reuse-report.json")})
    if not passed:sys.exit(1)

if __name__=="__main__":main()
