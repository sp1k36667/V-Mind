#!/usr/bin/env python3
"""Kontrollierter E2B-Neustartvergleich: generierter Code, keine Host-Übernahme von Referenzdateien."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

MODEL="vmind-gemma4:e2b"
SPEC="""Erstelle einen deutschen Aufgabenplaner ausschließlich mit der Python-Standardbibliothek.
app.py exportiert TaskStore(path) mit add(text)->int, list()->list[dict], done(id)->None,
remove(id)->None. Aufgaben: {id:int,text:str,done:bool}. Dauerhafte JSON-Speicherung an genau dem
übergebenen DATEI-Pfad. IDs steigen auch nach Löschung weiter. Leerer/Whitespace-Text und
unbekannte IDs müssen ValueError auslösen. Beschädigte vorhandene JSON-Dateien müssen
ValueError auslösen und dürfen nicht überschrieben werden. done/remove müssen gespeichert werden.
CLI: python3 app.py --file DATEI add TEXT / list / done ID / remove ID.
list zeigt ID [ ] TEXT oder ID [x] TEXT. CLI-Fehler: Exitcode ungleich null.
Tests in test_app.py mit unittest und TemporaryDirectory; noch nicht vorhandene Dateipfade.
Prüfe Persistenz nach Wiederöffnung, stabile IDs, done/remove, leeren Text und beschädigtes JSON.
Nicht auf eine bestimmte Fehlermeldung testen, nur auf ValueError. Keine zusätzlichen Pakete."""

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",required=True);ap.add_argument("--rounds",type=int,default=2)
    opt=ap.parse_args();root=Path(opt.root).resolve(strict=True);meta=root/".vmind"
    setup=json.loads((meta/"restart-setup.json").read_text())
    acceptance=Path(setup["acceptance_source"]).read_text()
    database=meta/"memory.db"
    prompt_source=Path(__file__).resolve().parents[1]/"prompts/start.de.md"
    system=prompt_source.read_text()+"\nDieser Hostschritt ist Dateigenerierung. Antworte ausschließlich mit dem vollständigen Inhalt der angeforderten Datei, ohne Markdown, Werkzeug-JSON oder Erklärungen. Der Host schreibt und prüft deine Ausgabe. Schreibe kompakt, ohne lange Kommentare, app.py höchstens 110 Zeilen, Tests höchstens 90 Zeilen. Nutze bereitgestelltes geprüftes Wissen, sofern es passt. Keine Platzhalter, keine Aussagen über nicht ausgeführte Tests."
    def vmind(req):
        p=subprocess.run(["vmind","serve",str(database)],input=json.dumps(req,ensure_ascii=False)+"\n",text=True,capture_output=True,check=True,timeout=15)
        out=json.loads(p.stdout)
        if not out["ok"]:raise RuntimeError(out["error"])
        return out["data"]
    def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    def generate(scope,session,filename,current,knowledge,errors,folder):
        content={"vmind_runtime":{"mode":"context_only","scope":scope,"conversation_persistence":"host_managed","tools_available":False},
            "project_goal":SPEC,"target_file":filename,"instruction":"Gib nur die vollständige Datei aus.",
            "memory":knowledge,"test_feedback":errors}
        if filename=="test_app.py":content["current_app"]=current
        payload={"model":MODEL,"system":system,"prompt":json.dumps(content,ensure_ascii=False),"stream":False,"think":False,
            "options":{"num_ctx":8192,"num_predict":2400,"temperature":0,"seed":42}}
        vmind({"op":"message","conversation_id":session,"role":"user","content":json.dumps({"target_file":filename,"scope":scope,"memory_ids":[m['id'] for m in knowledge],"feedback":errors},ensure_ascii=False)})
        req=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=180) as r:result=json.load(r)
        save(folder/(filename+".generation.json"),{"request":payload,"response":result})
        raw=result.get("response","")
        vmind({"op":"message","conversation_id":session,"role":"assistant","content":raw or "[Leere Modellantwort]"})
        if not result.get("done") or result.get("done_reason")=="length":
            return {"written":False,"error":"Modellantwort abgeschnitten","prompt_eval_count":result.get("prompt_eval_count"),"eval_count":result.get("eval_count")}
        code=raw.strip()
        if code.startswith("```"):code=code.split("\n",1)[1].rsplit("```",1)[0].rstrip()
        target=folder/filename
        target.write_text(code+"\n")
        return {"written":True,"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"prompt_eval_count":result.get("prompt_eval_count"),"eval_count":result.get("eval_count")}
    def run_test(cmd,cwd):
        try:
            p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=30)
            text=p.stderr+p.stdout
            count=re.search(r"Ran (\d+) tests?",text)
            ran=int(count.group(1)) if count else 0
            fail=re.search(r"failures=(\d+)",text);err=re.search(r"errors=(\d+)",text)
            failures=int(fail.group(1)) if fail else 0;errors=int(err.group(1)) if err else 0
            return {"exit_code":p.returncode,"tests_run":ran,"passed":max(0,ran-failures-errors) if ran else 0,"stdout":p.stdout,"stderr":p.stderr}
        except subprocess.TimeoutExpired:
            return {"exit_code":124,"tests_run":0,"passed":0,"stdout":"","stderr":"Zeitlimit von 30 Sekunden überschritten"}
    outcomes=[]
    for use_memory in [False,True]:
        arm="mit_vmind" if use_memory else "ohne_vmind"
        target=root if use_memory else meta/"kontrolle"
        target.mkdir(exist_ok=True)
        records=meta/arm;records.mkdir()
        check=target/"verification";check.mkdir(exist_ok=True)
        (check/"acceptance.py").write_text(acceptance)
        scope="e2b-neustart-"+arm
        session=vmind({"op":"session_new","scope":scope,"title":"E2B-Neugenerierung "+arm})["conversation_id"]
        vmind({"op":"log","scope":scope,"kind":"goal","body":SPEC,"source":"Identischer Auftrag für beide E2B-Vergleichsläufe"})
        vmind({"op":"log","scope":scope,"kind":"task","task_key":"neu-erstellen","task_status":"in_progress","body":"Neuer Quelltext durch E2B; gespeichertes Wissen "+("zugänglich" if use_memory else "nicht im Modellkontext"),"source":"Kontrollierter Testhost; gleiche Einstellungen"})
        attempts=[];feedback="";generations=[]
        for round_index in range(1,opt.rounds+1):
            round_dir=records/("versuch-"+str(round_index));round_dir.mkdir()
            print(arm+" Versuch "+str(round_index)+": E2B erzeugt app.py",flush=True)
            for filename in ["app.py","test_app.py"]:
                memory=[]
                if use_memory:
                    found=vmind({"op":"recall","scope":scope,"query":"Aufgabenplaner Referenzdatei "+filename,"limit":20})["memories"]
                    memory=[{k:m[k] for k in ["id","problem","solution","source","status","evidence"]} for m in found if m["problem"]=="Aufgabenplaner Referenzdatei "+filename]
                current=(round_dir/"app.py").read_text() if (round_dir/"app.py").exists() else ""
                gen=generate(scope,session,filename,current,memory,feedback,round_dir)
                gen.update({"file":filename,"memory_ids":[m['id'] for m in memory]});generations.append(gen)
                if gen["written"]:(target/filename).write_bytes((round_dir/filename).read_bytes())
                else:
                    (target/filename).unlink(missing_ok=True)
                    print(arm+" "+filename+": "+gen['error'],flush=True)
            own=run_test([sys.executable,"-I","-m","unittest","discover","-v","-s",str(target),"-p","test_app.py"],target)
            independent=run_test([sys.executable,str(check/"acceptance.py")],target)
            passed=own['exit_code']==0 and own['tests_run']>0 and independent['exit_code']==0 and independent['tests_run']==7
            result={"round":round_index,"passed":passed,"model_tests":own,"independent_acceptance":independent}
            save(round_dir/"tests.json",result);attempts.append(result)
            print(arm+": Abnahme "+str(independent['passed'])+"/7; eigene Tests "+str(own['passed'])+"/"+str(own['tests_run']),flush=True)
            vmind({"op":"message","conversation_id":session,"role":"tool","content":json.dumps(result,ensure_ascii=False)[:30000]})
            if passed:break
            feedback="Vorheriger Versuch fehlgeschlagen. Verbessere selbst, ohne falsches Verhalten in Tests zu erlauben. Unabhängige Prüfung:\n"+independent['stderr'][-1800:]+"\nEigene Tests:\n"+own['stderr'][-1200:]
        outcome={"arm":arm,"scope":scope,"session":session,"attempts":attempts,"generations":generations,"passed":attempts[-1]['passed'],"directory":str(target)}
        save(records/"result.json",outcome);outcomes.append(outcome)
        vmind({"op":"log","scope":scope,"kind":"task","task_key":"neu-erstellen","task_status":"done" if outcome['passed'] else "blocked","body":"E2B-Neugenerierung beendet: "+json.dumps({"passed":outcome['passed'],"independent_passed":attempts[-1]['independent_acceptance']['passed'],"own_tests":attempts[-1]['model_tests']['tests_run']}),"source":str(records/"result.json")})
    report={"model":MODEL,"settings":{"num_ctx":8192,"num_predict":2400,"temperature":0,"seed":42},"setup":setup,"arms":outcomes,
        "limitations":"Je ein Durchlauf pro Bedingung mit maximal zwei Versuchen; gleicher Prompt und gleiche Prüfungen. Mit Wissen können vollständige Referenzen reproduziert werden. Keine Aussage über allgemeines Lernen oder neue Aufgaben."}
    save(meta/"regeneration-comparison.json",report)
    print("Vergleich vollständig gespeichert.",flush=True)

if __name__=="__main__":main()
