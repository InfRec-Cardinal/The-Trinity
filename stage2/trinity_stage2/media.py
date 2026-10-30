import base64
import hashlib
import json
import re
from pathlib import Path


def image_block(value):
    if isinstance(value, str) and value.startswith('data:image/'):
        match = re.fullmatch(r'data:(image/[a-z]+);base64,([A-Za-z0-9+/=\s]+)', value)
        if not match:
            raise ValueError('Invalid image data URI')
        return image_block({'type': 'image', 'mimeType': match[1], 'data': match[2]})
    if not isinstance(value, dict):
        return None
    if value.get('type') in ('image_url', 'input_image'):
        url = value.get('image_url')
        url = url.get('url') if isinstance(url, dict) else url
        if not isinstance(url, str):
            raise ValueError('Image URL required')
        return image_block(url) if url.startswith('data:') else image_block({'type': 'image', 'source': {'type': 'url', 'url': url}})
    if value.get('type') != 'image':
        return None
    source = value.get('source') or {}
    if source.get('type') == 'url':
        if not re.match(r'^https?://', source.get('url', '')):
            raise ValueError('Invalid image URL')
        return {'type': 'image', 'source': {'type': 'url', 'url': source['url']}}
    data = source.get('data', value.get('data'))
    if value.get('path'):
        data = base64.b64encode(Path(value['path']).read_bytes()).decode()
    media = source.get('media_type', value.get('mimeType', value.get('media_type')))
    if media not in ('image/png', 'image/jpeg', 'image/gif', 'image/webp') or not isinstance(data, str):
        raise ValueError('Unsupported image source')
    data = re.sub(r'\s', '', data)
    raw = base64.b64decode(data + '=' * (-len(data) % 4), validate=True)
    if not raw or len(raw) > 5 * 1024 * 1024:
        raise ValueError('Invalid image size')
    detected = ('image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else
                'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else
                'image/gif' if raw[:6] in (b'GIF87a', b'GIF89a') else
                'image/webp' if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' else None)
    if detected != media:
        raise ValueError('Image signature does not match media type')
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': media, 'data': base64.b64encode(raw).decode()}}


def normalize_media(value):
    block = image_block(value)
    if block:
        return block
    if isinstance(value, list):
        return [normalize_media(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_media(item) for key, item in value.items()}
    return value


def split_media(value):
    images = {}

    def visit(item, location):
        block = image_block(item)
        if block:
            image_id = hashlib.sha256(json.dumps(block['source'], sort_keys=True).encode()).hexdigest()
            if image_id not in images:
                images[image_id] = {'block': block, 'locations': []}
            images[image_id]['locations'].append(location)
            return {'imageId': image_id, 'mediaType': block['source'].get('media_type', 'remote_image')}
        if isinstance(item, list):
            return [visit(child, f'{location}/{index}') for index, child in enumerate(item)]
        if isinstance(item, dict):
            return {key: visit(child, location + '/' + key.replace('~', '~0').replace('/', '~1')) for key, child in item.items()}
        return item

    data = visit(value, '')
    attachments = []
    for image_id, item in images.items():
        attachments += [{'type': 'text', 'text': json.dumps({'imageId': image_id, 'locations': item['locations']})}, item['block']]
    return data, attachments


def observation_text(value):
    data, _ = split_media(value)
    return data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)


def step_evidence(work_dir, task, episode, step):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,159}', task):
        raise ValueError('Invalid task identifier')
    file = Path(work_dir) / 'records-canonical' / (task + '.json')
    if not file.exists():
        raise ValueError('Canonical observations are unavailable; reimport the source trajectories')
    rows = json.loads(file.read_text())
    row = next((row for row in rows if row['episodeId'] == episode), None)
    if row is None or not 0 <= step <= len(row['steps']):
        raise ValueError('Unknown episode or step')
    if step == 0:
        value = {'initialObservation': row['initialObservation']}
    else:
        current = row['steps'][step - 1]
        value = {'beforeObservation': row['initialObservation'] if step == 1 else row['steps'][step - 2]['observation'], **current}
    data, attachments = split_media(value)
    return {'output': {'task': task, 'episode': episode, 'step': step, 'evidence': data}, 'attach': attachments}


def model_content(value):
    parsed = value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            pass
    data, attachments = split_media(parsed)
    if not attachments:
        return value if isinstance(value, str) else json.dumps(data, ensure_ascii=False)
    if len(attachments) // 2 > 100:
        raise ValueError('Request exceeds the image limit')
    return [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}, *attachments]
