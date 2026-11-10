"""L'application tourne en file:// sans AUCUNE requête réseau, et build.py
ne touche jamais aux données personnelles."""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402


def test_app_offline_chromium():
    assert (ROOT / "app" / "index.html").exists(), "lancer build.py d'abord"
    out = subprocess.run(["node", str(ROOT / "tests" / "smoke_app.cjs")],
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stdout + out.stderr


def test_index_sans_ressource_externe():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    for motif in ("<link rel=\"stylesheet\" href=\"http", "src=\"http", "url(http",
                  "@import", "fetch(", "XMLHttpRequest", "navigator.sendBeacon"):
        assert motif not in html, f"motif réseau trouvé : {motif}"


def test_build_necrase_pas_le_personnel(tmp_path):
    perso = sorted((ROOT / "data" / "personal").glob("*.json"))
    avant = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in perso}
    data, seed = build.load_all()
    assert build.validate(data, seed) == []
    build.build_app(data, seed)
    apres = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in perso}
    assert avant == apres
