import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
 
FAKE_ARGS = {"topic": "it_support"}  # matches the enum in the starter's FAQ_TOOL
 
FAKE_OPENAI = r'''
import json, os
LOG = os.environ["FAKE_LOG"]
MODE = os.environ.get("FAKE_MODE", "")
_n = 0
 
def _ser(o):
    if isinstance(o, dict):
        return {k: _ser(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_ser(v) for v in o]
    if hasattr(o, "__dict__"):
        return {k: _ser(v) for k, v in vars(o).items()}
    return o
 
class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)
 
class _Responses:
    def create(self, **kw):
        global _n
        _n += 1
        with open(LOG, "a") as f:
            f.write(json.dumps({"n": _n, "kwargs": _ser(kw)}, default=str) + "\n")
        already_has_output = "function_call_output" in json.dumps(_ser(kw.get("input")), default=str)
        if MODE in ("tool", "followup") and kw.get("tools") and not already_has_output:
            out = [_Obj(type="function_call", name="lookup_campus_faq",
                        arguments=json.dumps(__ARGS__), call_id="call_test_123", id="fc_1")]
            text = ""
        else:
            out = [_Obj(type="message", content=[_Obj(type="output_text", text="FAKE: Tech Hall, Room 120")])]
            text = "FAKE: Tech Hall, Room 120"
        return _Obj(id="resp_%d" % _n, output=out, output_text=text, model=kw.get("model"))
 
class OpenAI:
    def __init__(self, *a, **k):
        self.responses = _Responses()
'''.replace("__ARGS__", repr(FAKE_ARGS))
 
 
def run_mode(student_file, mode, workdir):
    log = Path(workdir) / f"log_{mode}.jsonl"
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(Path(workdir) / "fake") + os.pathsep + env.get("PYTHONPATH", ""),
        FAKE_LOG=str(log),
        FAKE_MODE=mode,
        OPENAI_API_KEY="sk-fake-for-grading",
    )
    student_file = Path(student_file).resolve()
    p = subprocess.run(
        [sys.executable, str(student_file), "--mode", mode],
        cwd=student_file.parent, env=env, capture_output=True, text=True, timeout=60,
    )
    calls = []
    if log.exists():
        calls = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    return p, calls
 
 
def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    student_file = sys.argv[1]
    results = []
 
    def check(name, ok, detail=""):
        results.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not ok else ""))
 
    src = Path(student_file).read_text()
    check("No hardcoded API key", not re.search(r"sk-[A-Za-z0-9_\-]{10,}", src))
 
    with tempfile.TemporaryDirectory() as wd:
        (Path(wd) / "fake").mkdir()
        (Path(wd) / "fake" / "openai.py").write_text(FAKE_OPENAI)
 
        # ---- basic ----
        print("\n== TODO 1: basic ==")
        p, calls = run_mode(student_file, "basic", wd)
        check("Script runs without error", p.returncode == 0, p.stderr.strip()[-300:])
        check("Made a responses.create call", len(calls) >= 1)
        if calls:
            kw = calls[0]["kwargs"]
            check("Passes model", bool(kw.get("model")))
            check("Passes instructions", bool(kw.get("instructions")))
            check("Passes input", bool(kw.get("input")))
        check("Prints/returns output_text", "FAKE" in p.stdout, "output_text not shown")
 
        # ---- tool ----
        print("\n== TODO 2: tool ==")
        p, calls = run_mode(student_file, "tool", wd)
        check("Script runs without error", p.returncode == 0, p.stderr.strip()[-300:])
        check("Made at least 2 create calls", len(calls) >= 2, f"made {len(calls)}")
        if len(calls) >= 2:
            first, second = calls[0]["kwargs"], calls[1]["kwargs"]
            check("1st call offers the tool and requires it", bool(first.get("tools")) and first.get("tool_choice") == "required")
            blob = json.dumps(second.get("input"), default=str)
            check("2nd call contains function_call_output", "function_call_output" in blob)
            check("call_id matches the model's call_id", "call_test_123" in blob)
            outs = [i for i in (second.get("input") or [])
                    if isinstance(i, dict) and i.get("type") == "function_call_output"]
            check("output is a JSON string (json.dumps)",
                  bool(outs) and all(isinstance(o.get("output"), str) for o in outs))
            check("Tool output came from the real lookup (Tech Hall, Room 120)", "Room 120" in blob)
            check("2nd call links to 1st via previous_response_id=resp_1",
                  second.get("previous_response_id") == "resp_1", f"got {second.get('previous_response_id')}")
            check("2nd call keeps model + instructions", bool(second.get("model")) and bool(second.get("instructions")))
            check("2nd call uses tool_choice='none'", second.get("tool_choice") == "none", f"got {second.get('tool_choice')}")
        check("Final answer printed", "FAKE" in p.stdout)
 
        # ---- followup ----
        print("\n== TODO 3: followup ==")
        p, calls = run_mode(student_file, "followup", wd)
        check("Script runs without error", p.returncode == 0, p.stderr.strip()[-300:])
        check("Made 4 create calls (2 per question)", len(calls) == 4, f"made {len(calls)}")
        if len(calls) >= 3:
            q1_first = calls[0]["kwargs"].get("previous_response_id")
            q2_first = calls[2]["kwargs"].get("previous_response_id")
            check("Question 1 does NOT send a previous_response_id", not q1_first, f"got {q1_first}")
            check("Question 2's FIRST request carries previous_response_id = answer 1's id (resp_2)",
                  q2_first == "resp_2", f"got {q2_first}")
        if len(calls) >= 4:
            check("Question 2's second request chains to its own first call (resp_3)",
                  calls[3]["kwargs"].get("previous_response_id") == "resp_3",
                  f"got {calls[3]['kwargs'].get('previous_response_id')}")
 
    print(f"\n{sum(results)}/{len(results)} checks passed")
    print("Still check manually: reflection answers (function_call vs function_call_output, "
          "call_id, one limitation) and a run against a different FAQ topic.")
 
 
if __name__ == "__main__":
    main()
 
