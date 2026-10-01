"""Publish the built site to R2 so the crickrida.com server can mirror it.

Files are stored by content hash under site/objects/, so a file that has
not changed is never uploaded again. site/manifest.json maps every path to
its hash and is written last: the server's sync job only ever sees a
complete release. Objects that neither the new nor the previous release
uses are removed afterwards.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / '_site'
BUCKET = 'cricket-wicket-data'
PREFIX = 'site/'
TYPES = {'.webmanifest': 'application/manifest+json', '.parquet': 'application/vnd.apache.parquet', '.xml': 'application/xml',
         '.json': 'application/json', '.js': 'text/javascript', '.woff2': 'font/woff2', '.svg': 'image/svg+xml'}


def client():
    return boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'], aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'], region_name='auto',
                        config=Config(signature_version='s3v4', max_pool_connections=32, retries={'max_attempts': 6, 'mode': 'adaptive'}))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def key(sha):
    return f'{PREFIX}objects/{sha[:2]}/{sha}'


def content_type(path):
    return TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or 'application/octet-stream'


def main():
    if not (SITE / 'index.html').exists():
        sys.exit('Build the site first: _site/index.html is missing')
    files = sorted(p for p in SITE.rglob('*') if p.is_file() and not p.name.startswith('.'))
    with ThreadPoolExecutor(8) as pool:
        hashes = dict(zip((p.relative_to(SITE).as_posix() for p in files), pool.map(digest, files)))
    s3 = client()
    try:
        previous = json.loads(s3.get_object(Bucket=BUCKET, Key=PREFIX + 'manifest.json')['Body'].read())
    except s3.exceptions.NoSuchKey:
        previous = {'files': {}}
    stored = set()
    for page in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET, Prefix=PREFIX + 'objects/'):
        stored.update(o['Key'] for o in page.get('Contents', []))
    upload = {}
    for rel, sha in hashes.items():
        if key(sha) not in stored:
            upload.setdefault(sha, rel)

    def put(item):
        sha, rel = item
        path = SITE / rel
        s3.upload_file(str(path), BUCKET, key(sha), ExtraArgs={'ContentType': content_type(path), 'CacheControl': 'public, max-age=31536000, immutable'})
        return path.stat().st_size

    with ThreadPoolExecutor(24) as pool:
        sent = sum(pool.map(put, upload.items()))
    now = datetime.now(timezone.utc)
    manifest = {'version': os.environ.get('GITHUB_SHA', '')[:12] + '-' + now.strftime('%Y%m%d%H%M%S'), 'generated_at': now.isoformat(timespec='seconds'),
                'files': hashes, 'bytes': sum((SITE / rel).stat().st_size for rel in hashes)}
    s3.put_object(Bucket=BUCKET, Key=PREFIX + 'manifest.json', Body=json.dumps(manifest, separators=(',', ':')).encode(),
                  ContentType='application/json', CacheControl='no-cache')
    keep = {key(sha) for sha in hashes.values()} | {key(sha) for sha in (previous.get('files') or {}).values()}
    stale = sorted(stored - keep)
    for i in range(0, len(stale), 1000):
        s3.delete_objects(Bucket=BUCKET, Delete={'Objects': [{'Key': k} for k in stale[i:i + 1000]], 'Quiet': True})
    print(json.dumps({'files': len(hashes), 'uploaded': len(upload), 'uploaded_bytes': sent, 'removed': len(stale), 'version': manifest['version']}))


if __name__ == '__main__':
    main()
