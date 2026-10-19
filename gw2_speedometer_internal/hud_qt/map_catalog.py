"""Catálogo de mapas para el selector (SOLO LECTURA).

Replica cómo obtiene la lista la app actual (speedometer.py, ``changeCup``/``__init__``):
  * copas:  GET https://www.beetlerank.com/api/cups        -> {"cups": [...]} (+ "OWN MAPS FOLDER")
  * mapas:  GET https://www.beetlerank.com/api/maps/<copa> -> {"maps": [...]}
  * local:  maps/*.csv (copa "OWN MAPS FOLDER"); sin red la app usa subcarpetas de maps/ como copas
  * al elegir, speedometer.py carga los checkpoints de
      online -> https://www.beetlerank.com/uploads/checkpoints/<mapa>.csv
      local  -> maps/<sanitize_map_name(mapa)>.csv
    y guarda cup.txt / guildhall.txt. Aquí sólo se CALCULA esa referencia; no se carga nada,
    no se escriben ficheros y no se toca la lógica de checkpoints ni de logs.
Si no hay red se usa ``data/beetlerank_maps_snapshot.json`` (instantánea de ejemplo).
"""

import json
import os
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
API = "https://www.beetlerank.com/api"
CHECKPOINTS_URL = "https://www.beetlerank.com/uploads/checkpoints/"
SNAPSHOT = os.path.join(HERE, "data", "beetlerank_maps_snapshot.json")
HEADERS = {"Origin": "null", "Referer": "null", "Accept": "application/json"}
TIMEOUT = (3.05, 8)  # (connect, read) como HTTP_TIMEOUT de speedometer.py
LOCAL_CUP = "OWN MAPS FOLDER"
ALL_CUP = "ALL MAPS"


@dataclass
class MapEntry:
    name: str
    cup: str
    source: str  # "online" | "local"

    @property
    def checkpoints_ref(self) -> str:
        if self.source == "local":
            return os.path.join(APP_DIR, "maps", _sanitize(self.name) + ".csv")
        url = CHECKPOINTS_URL + self.name + ".csv"
        try:  # igual que speedometer.py: requests.utils.requote_uri
            from requests.utils import requote_uri

            return requote_uri(url)
        except ImportError:
            return quote(url, safe=":/[]()-_.~'!*,&+%")

    def key(self):
        return (self.source, self.cup, self.name)


@dataclass
class MapGroup:
    title: str
    source: str
    maps: list[MapEntry] = field(default_factory=list)


@dataclass
class Catalog:
    groups: list[MapGroup]
    origin: str          # "live" | "snapshot" | "offline"
    detail: str = ""

    def count(self, source=None):
        return sum(len(g.maps) for g in self.groups if source in (None, g.source))


def _sanitize(name):
    try:  # mismo saneado que usa la app, si está disponible
        import pathutils

        return pathutils.sanitize_map_name(name)
    except (ImportError, AttributeError):
        return "".join(c for c in name if c not in '<>:"/\\|?*').strip()


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in t if not unicodedata.combining(c)).casefold()


def _get_json(url, attempts=3):
    """GET de solo lectura con timeout; reintenta (el servidor corta a veces la conexión TLS)."""
    for i in range(attempts):
        try:
            return _get_json_once(url)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(0.4 * (i + 1))
    return None


def _get_json_once(url):
    try:
        import requests

        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except ImportError:
        import urllib.request

        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT[1]) as fh:
            return json.load(fh)


def fetch_online():
    cups = _get_json(f"{API}/cups")["cups"]

    def one(cup):
        return cup, _get_json(f"{API}/maps/{quote(cup)}").get("maps", [])

    with ThreadPoolExecutor(max_workers=4) as ex:
        maps = dict(ex.map(one, cups))
    return cups, maps


def load_snapshot():
    with open(SNAPSHOT, encoding="utf-8") as fh:
        d = json.load(fh)
    return d["cups"], d["maps"], d.get("fetched", "?")


def local_groups():
    root = os.path.join(APP_DIR, "maps")
    groups = []
    try:
        files = sorted(f[:-4] for f in os.listdir(root) if f.lower().endswith(".csv"))
    except OSError:
        files = []
    groups.append(MapGroup(LOCAL_CUP, "local", [MapEntry(n, LOCAL_CUP, "local") for n in files]))
    try:
        subdirs = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    except OSError:
        subdirs = []
    for d in subdirs:
        names = sorted(f[:-4] for f in os.listdir(os.path.join(root, d)) if f.lower().endswith(".csv"))
        if names:
            groups.append(MapGroup(d, "local", [MapEntry(n, d, "local") for n in names]))
    return [g for g in groups if g.maps]


def _online_groups(cups, maps):
    groups, seen = [], set()
    for cup in cups:
        if cup == ALL_CUP:
            continue
        names = [n for n in maps.get(cup, []) if isinstance(n, str)]
        seen.update(names)
        if names:
            groups.append(MapGroup(cup, "online", [MapEntry(n, cup, "online") for n in names]))
    rest = sorted((n for n in maps.get(ALL_CUP, []) if n not in seen), key=normalize)
    if rest:  # mapas que sólo están en "ALL MAPS"
        groups.append(MapGroup(f"{ALL_CUP} · OTROS", "online", [MapEntry(n, ALL_CUP, "online") for n in rest]))
    return groups


def load_catalog(online=True) -> Catalog:
    loc = local_groups()
    if online:
        try:
            cups, maps = fetch_online()
            n = sum(len(v) for k, v in maps.items() if k == ALL_CUP)
            return Catalog(_online_groups(cups, maps) + loc, "live",
                           f"beetlerank.com · {len(cups)} copas · {n} mapas · en vivo")
        except Exception as exc:  # noqa: BLE001 - sin red / API caída -> instantánea
            err = type(exc).__name__
        else:
            err = ""
    else:
        err = "offline"
    try:
        cups, maps, when = load_snapshot()
        return Catalog(_online_groups(cups, maps) + loc, "snapshot",
                       f"sin conexión ({err}) · instantánea de EJEMPLO del {when}")
    except (OSError, ValueError, KeyError):
        return Catalog(loc, "offline", "sin conexión · sólo mapas locales")


def current_selection() -> MapEntry | None:
    """Lee (sin modificar) cup.txt / guildhall.txt que guarda speedometer.py."""
    try:
        with open(os.path.join(APP_DIR, "cup.txt"), encoding="utf-8") as fh:
            cup = fh.read().strip()
        with open(os.path.join(APP_DIR, "guildhall.txt"), encoding="utf-8") as fh:
            name = fh.read().strip()
    except OSError:
        return None
    if not name or name in ("-", "SELECT MAP"):
        return None
    return MapEntry(name, cup, "local" if cup == LOCAL_CUP else "online")
