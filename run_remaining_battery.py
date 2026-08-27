#!/usr/bin/env python3
"""Run remaining 9-arm battery with LLM-enhanced simulation."""
import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Remaining scenarios (naive_28d already done)
SCENARIOS = [
    ("SNI_28d", "SNI_28d.yaml", 28),
    ("CCI_28d", "CCI_28d.yaml", 28),
    ("CIPN_28d", "CIPN_28d.yaml", 28),
    ("SNI_28d_CLP257", "SNI_28d_CLP257.yaml", 28),
    ("SNI_28d_XPRO1595", "SNI_28d_XPRO1595.yaml", 28),
    ("SNI_28d_FASUDIL", "SNI_28d_FASUDIL.yaml", 28),
    ("SNI_28d_DRIVE_DECAY", "SNI_28d_DRIVE_DECAY.yaml", 28),
    ("naive_180d", "naive_180d.yaml", 180),
    ("SNI_180d", "SNI_180d.yaml", 180),
]

BASE_DIR = Path("simulator")
CARDS_DIR = BASE_DIR / "cards"
SCENARIO_DIR = BASE_DIR / "scenarios"
OUT_DIR = BASE_DIR / "out" / "llm_battery_20260827"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LLM_ENDPOINT = "http://192.168.1.13:1234"
LLM_MODEL = "qwen/qwen3.8-27b"
LLM_MAX_TOKENS = "4096"
SEED = "42"

def run_scenario(name, yaml_file, days):
    scenario_path = SCENARIO_DIR / yaml_file
    out_path = OUT_DIR / f"{name}_LLM"
    log_path = OUT_DIR / f"{name}_LLM.log"
    
    cmd = [
        sys.executable, "-m", "simulator.engine.orchestrator",
        "--scenario", str(scenario_path),
        "--cards", str(CARDS_DIR),
        "--out", str(out_path),
        "--llm-endpoint", LLM_ENDPOINT,
        "--llm-model", LLM_MODEL,
        "--llm-max-tokens", LLM_MAX_TOKENS,
        "--seed", SEED,
    ]
    
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting {name} ({days}d)")
    print(f"{'='*60}")
    
    start = time.time()
    with open(log_path, 'w') as logf:
        logf.write(f"Command: {' '.join(cmd)}\n")
        logf.write(f"Started: {datetime.now().isoformat()}\n\n")
        logf.flush()
        
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True
        )
        
        for line in proc.stdout:
            print(line, end='')
            logf.write(line)
            logf.flush()
        
        proc.wait()
    
    elapsed = time.time() - start
    
    manifest_path = out_path / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        pain = manifest.get("manifest", {}).get("pain_score", "N/A")
        llm_calls = manifest.get("manifest", {}).get("llm_calls_made", "N/A")
        llm_deferred = manifest.get("manifest", {}).get("llm_calls_deferred", "N/A")
    else:
        pain = llm_calls = llm_deferred = "N/A"
    
    result = {
        "name": name,
        "days": days,
        "elapsed_sec": elapsed,
        "elapsed_min": elapsed / 60,
        "pain": pain,
        "llm_calls": llm_calls,
        "llm_deferred": llm_deferred,
        "returncode": proc.returncode,
        "log": str(log_path),
        "output": str(out_path),
    }
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {name} COMPLETE in {elapsed/60:.1f} min")
    print(f"  Pain: {pain}, LLM calls: {llm_calls}, Deferred: {llm_deferred}")
    print(f"  Return code: {proc.returncode}")
    
    return result

def main():
    print(f"Starting Remaining LLM Battery at {datetime.now().isoformat()}")
    print(f"Endpoint: {LLM_ENDPOINT} ({LLM_MODEL})")
    print(f"Output dir: {OUT_DIR}")
    print(f"Scenarios: {len(SCENARIOS)}")
    
    results = []
    total_start = time.time()
    
    for i, (name, yaml_file, days) in enumerate(SCENARIOS, 1):
        print(f"\n>>> Arm {i}/{len(SCENARIOS)}: {name}")
        try:
            result = run_scenario(name, yaml_file, days)
            results.append(result)
        except Exception as e:
            print(f"ERROR running {name}: {e}")
            results.append({"name": name, "error": str(e)})
        
        with open(OUT_DIR / "battery_results.json", 'w') as f:
            json.dump({
                "started": datetime.fromtimestamp(total_start).isoformat(),
                "endpoint": LLM_ENDPOINT,
                "model": LLM_MODEL,
                "results": results,
            }, f, indent=2)
        
        if i < len(SCENARIOS):
            print("  Cooling down 60s...")
            time.sleep(60)
    
    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"BATTERY COMPLETE in {total_elapsed/3600:.1f} hours")
    print(f"{'='*60}")
    
    print(f"\n{'Scenario':<25} {'Days':>4} {'Time(min)':>8} {'Pain':>8} {'LLM':>5} {'Deferred':>8} {'Status'}")
    print("-" * 70)
    for r in results:
        if "error" in r:
            print(f"{r['name']:<25} {'-':>4} {'-':>8} {'-':>8} {'-':>5} {'-':>8} FAILED")
        else:
            print(f"{r['name']:<25} {r['days']:>4} {r['elapsed_min']:>8.1f} {str(r['pain']):>8} {str(r['llm_calls']):>5} {str(r['llm_deferred']):>8} OK")

if __name__ == "__main__":
    main()
