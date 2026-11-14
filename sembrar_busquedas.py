# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and run by the team. See "Use of SI" in README.md.
"""
Guarda en cache/busquedas/ la lista de exposiciones de SPHEREx que cubren cada
objetivo del reto, para que la app no dependa de IRSA al mostrarlos.

Uso:  python sembrar_busquedas.py            (salta los que ya existen)
      python sembrar_busquedas.py --rehacer  (vuelve a consultar todos)

Hace una sola consulta a IRSA por objetivo (todas las bandas a la vez), por el
servicio SIA. Si IRSA está caído, reintenta cada 20 segundos hasta MINUTOS_MAXIMOS.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import datos

# Posiciones aproximadas de catálogo (J2000), salvo WISE 0855, que es la cadena
# literal del enunciado. Solo sirven para saber qué exposiciones cubren la zona:
# cada exposición mide 3.5 grados, así que unos minutos de arco no cambian la lista.
# Las posiciones precisas y actuales van en objetivos.yaml.
OBJETIVOS = [
    {"nombre": "barnard", "titulo": "Barnard's Star", "ra": 269.4521, "dec": 4.6934},
    {"nombre": "wise0855", "titulo": "WISE 0855-0714", "ra": 133.79513, "dec": -7.24515},
    {"nombre": "eps_indi_b", "titulo": "Epsilon Indi B", "ra": 331.044, "dec": -56.783},
    {"nombre": "rw_aur", "titulo": "RW Aurigae", "ra": 76.9564, "dec": 30.4014},
    {"nombre": "r_dra", "titulo": "R Draconis", "ra": 248.1675, "dec": 66.7550},
]

MINUTOS_MAXIMOS = 45
ESPERA_SEGUNDOS = 20

rehacer = "--rehacer" in sys.argv
limite = time.time() + MINUTOS_MAXIMOS * 60
os.makedirs(datos.DIR_SEMILLAS, exist_ok=True)

for objetivo in OBJETIVOS:
    ruta = os.path.join(datos.DIR_SEMILLAS, objetivo["nombre"] + ".json")
    if os.path.exists(ruta) and not rehacer:
        print(f"{objetivo['titulo']}: ya existe, se salta")
        continue
    inicio = time.time()
    exposiciones = []
    while not exposiciones and time.time() < limite:
        try:
            exposiciones = datos._buscar_sia(objetivo["ra"], objetivo["dec"])
        except Exception as error:
            print(f"{objetivo['titulo']}: IRSA no responde ({str(error)[:60]}); reintento...", flush=True)
            time.sleep(ESPERA_SEGUNDOS)
    if not exposiciones:
        print(f"{objetivo['titulo']}: SIN RESULTADO tras {time.time() - inicio:.0f} s", flush=True)
        continue
    por_banda = {}
    for exp in exposiciones:
        por_banda[exp["detector"]] = por_banda.get(exp["detector"], 0) + 1
    semilla = {
        **objetivo,
        "consultado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "fuente": "IRSA SIA, colecciones " + ", ".join(datos.COLECCIONES_SIA),
        "exposiciones": [
            {"fecha": e["fecha"], "detector": e["detector"], "url": e["url"]} for e in exposiciones
        ],
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(semilla, f)
    print(f"{objetivo['titulo']}: {len(exposiciones)} exposiciones en {time.time() - inicio:.0f} s  {por_banda}", flush=True)
