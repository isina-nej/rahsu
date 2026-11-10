from pathlib import Path
from scripts.preflight import parse_env

ROOT=Path(__file__).resolve().parents[1]

def test_osrm_builder_and_compose_use_same_pinned_image():
    value=parse_env(ROOT/'.env.example')['OSRM_IMAGE']
    assert value.startswith('ghcr.io/project-osrm/osrm-backend:')
    assert '@sha256:' in value
    assert len(value.split('@sha256:')[1])==64
    assert value in (ROOT/'docker-compose.yml').read_text(encoding='utf-8')
    assert value in (ROOT/'scripts/prepare_osrm.sh').read_text(encoding='utf-8')
    assert ':latest' not in (ROOT/'scripts/prepare_osrm.sh').read_text(encoding='utf-8')
