"""Teste de carga do robô ALO — motor, latência, throughput, soak e batch.

Uso:
    ROBO_ALO_BASE=http://127.0.0.1:5501 \
    ROBO_ALO_API_KEY=suachave \
    python scripts/loadtest_alo.py

Rode contra uma instância com rate-limit alto (ROBO_ALO_RATE_LIMIT grande),
senão a própria proteção limita o teste. Mede a capacidade do motor, não deve
ser apontado para produção sob tráfego real.
"""
from __future__ import annotations

import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.getenv("ROBO_ALO_BASE", "http://127.0.0.1:5501")
KEY = os.getenv("ROBO_ALO_API_KEY", "")
H = {"X-API-Key": KEY, "Content-Type": "application/json"}
SOAK_SEG = int(os.getenv("LOADTEST_SOAK_SEG", "30"))

CASOS = [
    {"operadora": "Claro", "amd": "Humano", "duracao_total_seg": 38,
     "tempo_ate_conexao_seg": 4.3, "tempo_silencio_seg": 2.8, "transferencia": True,
     "turnos": [{"falante": "cliente", "texto": "Alô?", "inicio_seg": 1.2},
                {"falante": "cliente", "texto": "Tem alguém aí?", "inicio_seg": 4.5},
                {"falante": "agente", "texto": "Boa tarde, falo com a senhora Maria?", "inicio_seg": 6.0}]},
    {"operadora": "Vivo", "amd": "Maquina", "transcricao": "URA: Deixe sua mensagem após o sinal."},
    {"operadora": "Tim", "silence_time": 9.5, "duracao_total_seg": 10, "transcricao": ""},
    {"operadora": "Claro", "causa_sip": "486 Busy Here", "codigo_encerramento": "busy"},
]


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p / 100))]


def rss_mb(pid):
    try:
        for ln in open(f"/proc/{pid}/status"):
            if ln.startswith("VmRSS:"):
                return int(ln.split()[1]) / 1024
    except Exception:
        return None


def achar_pid():
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            cl = open(f"/proc/{d}/cmdline", "rb").read().replace(b"\x00", b" ").decode()
            if "main.py alo" in cl or "alo_server" in cl:
                return int(d)
        except Exception:
            pass
    return None


def _uma(i):
    c = CASOS[i % len(CASOS)]
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}/alo/analisar", headers=H, json=c, timeout=15)
    return r.status_code, (time.perf_counter() - t0) * 1000


def teste_latencia(n=500):
    print("\n== LATÊNCIA HTTP (sequencial) ==")
    lat = []
    for i in range(n):
        c = CASOS[i % len(CASOS)]
        t0 = time.perf_counter()
        r = requests.post(f"{BASE}/alo/analisar", headers=H, json=c, timeout=10)
        lat.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200, r.status_code
    print(f"   p50={statistics.median(lat):.1f}ms p95={pct(lat,95):.1f}ms "
          f"p99={pct(lat,99):.1f}ms max={max(lat):.1f}ms")


def teste_throughput(n=2000):
    print("\n== THROUGHPUT CONCORRENTE ==")
    for C in (1, 10, 25, 50, 100):
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=C) as ex:
            res = list(ex.map(_uma, range(n)))
        dt = time.perf_counter() - t0
        lat = [l for _, l in res]
        ok = [s for s, _ in res].count(200)
        print(f"   conc={C:>3} {n/dt:>8,.0f} req/s ok={ok}/{n} "
              f"p95={pct(lat,95):.0f}ms p99={pct(lat,99):.0f}ms")


def teste_soak(seg):
    print(f"\n== SOAK {seg}s (conc=50) + memória ==")
    pid = achar_pid()
    r0 = rss_mb(pid) if pid else None
    fim = time.time() + seg
    total, erros = [0], [0]

    def w():
        while time.time() < fim:
            try:
                s, _ = _uma(total[0]); total[0] += 1
                if s != 200:
                    erros[0] += 1
            except Exception:
                erros[0] += 1
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=50) as ex:
        [ex.submit(w) for _ in range(50)]
    dt = time.perf_counter() - t0
    r1 = rss_mb(pid) if pid else None
    print(f"   {total[0]:,} req em {dt:.0f}s → {total[0]/dt:,.0f} req/s erros={erros[0]}")
    if r0 and r1:
        print(f"   RSS {r0:.1f}→{r1:.1f} MB ({r1-r0:+.1f} MB)")


def teste_batch(n=5000):
    print(f"\n== BATCH /alo/lote ({n} ligações) ==")
    chamadas = [dict(CASOS[i % len(CASOS)], id=f"cc{i}") for i in range(n)]
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}/alo/lote", headers=H,
                      json={"chamadas": chamadas, "usar_ia": False}, timeout=300)
    dt = time.perf_counter() - t0
    d = r.json()
    print(f"   HTTP {r.status_code} {d['processadas']} em {dt:.1f}s → {d['processadas']/dt:,.0f} lig/s "
          f"persistidas={d['persistidas']}")


if __name__ == "__main__":
    if not KEY:
        sys.exit("Defina ROBO_ALO_API_KEY no ambiente.")
    print(f"Alvo: {BASE}")
    teste_latencia()
    teste_throughput()
    teste_soak(SOAK_SEG)
    teste_batch()
    print("\nConcluído.")
