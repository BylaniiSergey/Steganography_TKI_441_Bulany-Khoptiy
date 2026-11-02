"""Проверка 10 PNG в запущенном официальном StegoRevealer API v25.7.34."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'stegorevealer'
OUT.mkdir(exist_ok=True)
rows = []
def request(image, method):
    url = 'http://localhost:11038/api/sa/' + method + '?' + urlencode({'path': str(image)})
    try:
        with urlopen(url, timeout=120) as response:
            return json.load(response)
    except HTTPError as error:
        return {'http_error': error.code, 'body': error.read().decode('utf-8', errors='replace')}

for container in ['uniform', 'gradient', 'edges', 'texture', 'black']:
    for kind in ['cover', 'stego']:
        image = ROOT / 'results' / container / (kind + '.png')
        result = request(image, 'fullAnalysis')
        if 'http_error' in result:
            result['individual_methods'] = {method: request(image, method) for method in ['csa', 'rs', 'spa', 'fan', 'zca', 'ckzha', 'statm', 'getDecision']}
        (OUT / f'{container}_{kind}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        failed = [k for k, v in result.items() if isinstance(v, dict) and (v.get('hasErrors') or v.get('methodSuccessful') is False)]
        individual = result.get('individual_methods', {})
        overall = result.get('complexSaMethodResults', individual.get('getDecision', {}))
        csa = result.get('chiSquareResult', individual.get('csa', {}))
        rs = result.get('rsResult', individual.get('rs', {}))
        statm = result.get('statmResult', individual.get('statm', {}))
        failed += [k for k, v in individual.items() if 'http_error' in v or v.get('hasErrors')]
        if csa.get('hasErrors') or csa.get('methodSuccessful') is False:
            csa = {}
        if rs.get('hasErrors') or rs.get('methodSuccessful') is False:
            rs = {}
        rows.append({'container': container, 'kind': kind,
                     'csa_blue': csa.get('messageRelativeVolumesByChannels', {}).get('Blue'),
                     'rs_blue': rs.get('messageRelativeVolumesByChannels', {}).get('Blue'),
                     'noise': statm.get('noiseValue'),
                     'entropy': statm.get('entropyValues', {}).get('shennon'),
                     'detected': overall.get('isHidingDetected'),
                     'full_http_error': result.get('http_error'),
                     'failed_methods': ';'.join(failed),
                     'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest()})
        print(container, kind, 'detected:', overall.get('isHidingDetected'), 'errors:', failed, flush=True)
with (OUT / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
metadata = {'version': 'v25.7.34', 'release': 'https://github.com/eihnast/StegoRevealer/releases/tag/v25.7.34',
            'asset': 'StegoRevealerAPI.exe', 'asset_sha256': '046E120B176AFD03E14E1B0F7FEEF604E48B129E453F6EC97C82EAB24269A79A',
            'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'endpoint': '/api/sa/fullAnalysis',
            'configuration': 'GET endpoint defaults, no analysis parameter overrides', 'results': rows}
(OUT / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
