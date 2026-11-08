"""Studio ZIP format verifier: R-07/R-08/R-11/R-12; never executes payload code."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import urllib.parse
import urllib.request
import zipfile

MAX_ARCHIVE = 8 * 1024 * 1024
PAYLOAD = {'code/client.py', 'code/client.ts', 'code/request.sh', 'code/siliq-graph.json',
           'fixtures/response.json', 'flow.json', 'teach.json', 'tools.json',
           'transforms/post.zs', 'transforms/pre.zs'}
MANIFEST = ('$schema', 'name', 'displayName', 'version', 'author', 'license',
            'description', 'category', 'entryFlow', 'toolsCount', 'inventory', 'createdAt')

class BundleError(ValueError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def loads(data: bytes | str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise BundleError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)

def encoded(value, pretty=False) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      **({'indent': 2} if pretty else {'separators': (',', ':')})).encode()

def verify_archive(data: bytes, expected_digest: str, expected_archive: str) -> dict:
    if len(data) > MAX_ARCHIVE or sha(data) != expected_archive:
        raise BundleError('Archive checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)) or set(names) != PAYLOAD | {'manifest.json'}:
            raise BundleError('Unexpected or duplicate archive entry')
        if sum(i.file_size for i in infos) > MAX_ARCHIVE or any(i.flag_bits & 1 or i.file_size > MAX_ARCHIVE or stat.S_ISLNK(i.external_attr >> 16) for i in infos):
            raise BundleError('Unsupported archive entry')
        files = {name: archive.read(name) for name in names}
    manifest = loads(files['manifest.json'])
    if set(manifest) != set(MANIFEST) | {'bundleSha256'}:
        raise BundleError('Unsupported manifest contract')
    canonical = {key: manifest[key] for key in MANIFEST}
    canonical['bundleSha256'] = manifest['bundleSha256']
    if files['manifest.json'] != encoded(canonical, True):
        raise BundleError('Noncanonical manifest bytes')
    root = sha(encoded({key: manifest[key] for key in MANIFEST}))
    if root != expected_digest or manifest['bundleSha256'] != root:
        raise BundleError('Bundle checksum mismatch')
    inventory = manifest['inventory']
    if not isinstance(inventory, list) or len(inventory) != len(PAYLOAD) or [i['path'] for i in inventory] != sorted(PAYLOAD):
        raise BundleError('Invalid payload inventory')
    for item in inventory:
        raw = files[item['path']]
        if set(item) != {'path', 'byteLength', 'sha256'} or len(raw) != item['byteLength'] or sha(raw) != item['sha256']:
            raise BundleError('Payload checksum mismatch')
    # Reject deployment capabilities and recognizable secret values without
    # printing matching source text, provider responses, or bearer credentials.
    text = '\n'.join(raw.decode('utf-8') for raw in files.values())
    if re.search(r'vault://|macOS Keychain|"(?:credential_ref|integration_auth|tokenFile)"|(?:Basic|Bearer)\s+[A-Za-z0-9_+/=.\-]{16,}|(?:ghp_|sk-)[A-Za-z0-9_\-]{20,}|eyJ[A-Za-z0-9_\-]{25,}', text):
        raise BundleError('Deployment credential or secret pattern in archive')
    tools = loads(files['tools.json'])
    if not isinstance(tools, list) or len(tools) != manifest['toolsCount'] or not tools:
        raise BundleError('Tool inventory mismatch')
    tool_names = set()
    for tool in tools:
        function = tool.get('function', {})
        name = function.get('name', '')
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]{0,127}', name) or name in tool_names:
            raise BundleError('Invalid or duplicate tool name')
        tool_names.add(name)
        http = tool.get('_meta', {}).get('sqr/http') or function.get('_meta', {}).get('sqr/http')
        if http:
            auth = http.get('authentication', {})
            if auth.get('format') != 'siliqun-authentication/1' or auth.get('endpointRequired') is not True or http.get('server') != f"https://{auth.get('slot')}.invalid":
                raise BundleError('Portable authentication declaration required')
    return {'manifest': manifest, 'tools': tools, 'flow': loads(files['flow.json']),
            'transforms': {'pre': files['transforms/pre.zs'].decode(), 'post': files['transforms/post.zs'].decode()},
            'fixtures': loads(files['fixtures/response.json']), 'teach': loads(files['teach.json']),
            'code': {'python': files['code/client.py'].decode(), 'typescript': files['code/client.ts'].decode(),
                     'curl': files['code/request.sh'].decode(), 'graphJson': files['code/siliq-graph.json'].decode()}}

if __name__ == '__main__':
    import sys
    base = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    release = loads((base / 'release.json').read_bytes())
    data = (base / release['archive']).read_bytes()
    result = verify_archive(data, release['bundleSha256'], release['archiveSha256'])
    print('Verified archive, canonical manifest, every payload byte and portable authentication:', len(result['tools']), 'tools')
