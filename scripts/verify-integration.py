"""Studio ZIP format verifier: R-07/R-08/R-11/R-12; never executes payload code."""
from __future__ import annotations
import base64
import zlib
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
        if len(names) != len(set(names)) or len(names) > 141 or not PAYLOAD | {'manifest.json'} <= set(names) or any(name not in PAYLOAD | {'manifest.json', 'catalogue/index.json', 'catalogue/strategy.json'} and not re.fullmatch(r'catalogue/chunks/[0-9a-f]{64}\.json', name) for name in names):
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
    v2 = manifest['$schema'] == 'https://sqrengine.com/schemas/bundle/v2.json'
    if manifest['$schema'] not in ('https://sqrengine.com/schemas/bundle/v1.json', 'https://sqrengine.com/schemas/bundle/v2.json'):
        raise BundleError('Unsupported bundle schema')
    extras = set(files) - PAYLOAD - {'manifest.json'}
    if (not v2 and extras) or (v2 and (not {'catalogue/index.json', 'catalogue/strategy.json'} <= extras or not 3 <= len(extras) <= 130)):
        raise BundleError('Unsupported catalogue inventory')
    payload = set(files) - {'manifest.json'}
    inventory = manifest['inventory']
    if not isinstance(inventory, list) or len(inventory) != len(payload) or [i['path'] for i in inventory] != sorted(payload):
        raise BundleError('Invalid payload inventory')
    for item in inventory:
        raw = files[item['path']]
        if set(item) != {'path', 'byteLength', 'sha256'} or len(raw) != item['byteLength'] or sha(raw) != item['sha256']:
            raise BundleError('Payload checksum mismatch')
    # Reject deployment capabilities and recognizable secret values without
    # printing matching source text, provider responses, or bearer credentials.
    text = '\n'.join(raw.decode('utf-8') for name, raw in files.items() if not name.startswith('catalogue/chunks/'))
    if re.search(r'vault://|macOS Keychain|"(?:credential_ref|integration_auth|tokenFile)"|(?:Basic|Bearer)\s+[A-Za-z0-9_+/=.\-]{16,}|(?:ghp_|sk-)[A-Za-z0-9_\-]{20,}|eyJ[A-Za-z0-9_\-]{25,}', text):
        raise BundleError('Deployment credential or secret pattern in archive')
    tools = loads(files['tools.json'])
    if not isinstance(tools, list) or len(tools) != manifest['toolsCount'] or (not tools and not v2):
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
    catalogue = None
    if v2:
        index, strategy = loads(files['catalogue/index.json']), loads(files['catalogue/strategy.json'])
        chunks = []
        for name in sorted(extras):
            if name.startswith('catalogue/chunks/'):
                chunk = loads(files[name])
                if name != f"catalogue/chunks/{chunk.get('sha256')}.json":
                    raise BundleError('Schema chunk path mismatch')
                chunks.append(chunk)
        catalogue = {'index': index, 'strategy': strategy, 'chunks': chunks}
        verify_catalogue(catalogue)
        catalogue['chunks'].sort(key=lambda chunk: index['chunks'].index(chunk['sha256']))
    return {'manifest': manifest, 'tools': tools, **({'catalogue': catalogue} if catalogue else {}), 'flow': loads(files['flow.json']),
            'transforms': {'pre': files['transforms/pre.zs'].decode(), 'post': files['transforms/post.zs'].decode()},
            'fixtures': loads(files['fixtures/response.json']), 'teach': loads(files['teach.json']),
            'code': {'python': files['code/client.py'].decode(), 'typescript': files['code/client.ts'].decode(),
                     'curl': files['code/request.sh'].decode(), 'graphJson': files['code/siliq-graph.json'].decode()}}

def decode_chunk(chunk):
    if chunk.get('format') != 'sqr-tool-schema-chunk/1' or chunk.get('encoding') != 'gzip-base64' or type(chunk.get('bytes')) is not int or not 2 <= chunk['bytes'] <= 512 * 1024 or not re.fullmatch('[0-9a-f]{64}', chunk.get('sha256', '')) or not isinstance(chunk.get('data'), str) or len(chunk['data']) > 1024 * 1024:
        raise BundleError('Invalid schema chunk')
    compressed = base64.b64decode(chunk['data'], validate=True)
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    raw = decoder.decompress(compressed, chunk['bytes'] + 1)
    if len(raw) != chunk['bytes'] or decoder.unconsumed_tail or decoder.unused_data or not decoder.eof or sha(raw) != chunk['sha256']:
        raise BundleError('Schema chunk decoded size or checksum mismatch')
    tools = loads(raw)
    if not isinstance(tools, list) or not 1 <= len(tools) <= 32:
        raise BundleError('Invalid schema chunk operation count')
    return tools

def canonical_hash(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode())

def verify_catalogue(catalogue):
    index, strategy, chunks = catalogue['index'], catalogue['strategy'], catalogue['chunks']
    if index.get('format') != 'sqr-tool-catalogue/1' or not isinstance(index.get('operations'), list) or not 1 <= len(index['operations']) <= 1024 or not isinstance(index.get('chunks'), list) or not 1 <= len(index['chunks']) <= 128 or len(index['chunks']) != len(chunks):
        raise BundleError('Invalid catalogue index')
    identity = {key: index[key] for key in ('sourceSha256', 'sourceUrl', 'title', 'chunks', 'operations')}
    if canonical_hash(identity) != index.get('id'):
        raise BundleError('Catalogue identity mismatch')
    if strategy.get('mode') not in ('manual', 'on-demand') or type(strategy.get('maxCandidates')) is not int or not 1 <= strategy['maxCandidates'] <= 8 or type(strategy.get('metadataBytes')) is not int or not 1024 <= strategy['metadataBytes'] <= 65536 or type(strategy.get('schemaBytes')) is not int or not 4096 <= strategy['schemaBytes'] <= 1024 * 1024 or not isinstance(strategy.get('effects'), list) or not strategy['effects'] or any(effect not in ('read', 'act') for effect in strategy['effects']):
        raise BundleError('Invalid catalogue strategy')
    entries = {entry['name']: entry for entry in index['operations']}
    if len(entries) != len(index['operations']):
        raise BundleError('Duplicate catalogue metadata')
    names, ids, total = set(), set(), 0
    for chunk in chunks:
        if chunk['sha256'] in ids or chunk['sha256'] not in index['chunks']:
            raise BundleError('Duplicate or unindexed schema chunk')
        ids.add(chunk['sha256'])
        total += chunk['bytes']
        if total > 32 * 1024 * 1024:
            raise BundleError('Catalogue decoded size exceeded')
        for tool in decode_chunk(chunk):
            name = tool.get('function', {}).get('name')
            entry = entries.get(name, {})
            if not name or name in names or entry.get('chunkSha256') != chunk['sha256'] or entry.get('toolSha256') != canonical_hash(tool):
                raise BundleError('Catalogue operation mismatch')
            names.add(name)
            http = tool.get('_meta', {}).get('sqr/http', {})
            auth = http.get('authentication', {})
            if auth.get('format') != 'siliqun-authentication/1' or auth.get('endpointRequired') is not True or http.get('server') != f"https://{auth.get('slot')}.invalid":
                raise BundleError('Portable catalogue authentication required')
            if re.search(r'vault://|macOS Keychain|"(?:credential_ref|integration_auth|tokenFile)"|(?:Basic|Bearer)\s+[A-Za-z0-9_+/=.\-]{16,}|(?:ghp_|sk-)[A-Za-z0-9_\-]{20,}|eyJ[A-Za-z0-9_\-]{25,}', encoded(tool).decode()):
                raise BundleError('Deployment credential in catalogue')
    if len(names) != len(entries) or not isinstance(strategy.get('operationIds'), list) or any(name not in names for name in strategy['operationIds']):
        raise BundleError('Catalogue scope mismatch')

if __name__ == '__main__':
    import sys
    base = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    release = loads((base / 'release.json').read_bytes())
    data = (base / release['archive']).read_bytes()
    result = verify_archive(data, release['bundleSha256'], release['archiveSha256'])
    print('Verified archive, canonical manifest, every payload byte and portable authentication:', len(result['tools']), 'tools')
