import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

tree = ET.parse(BASE_DIR / 'source.xml')
root = tree.getroot()
ns = {'s': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}

def find_slide(sid):
    for slide in root.iter('{%s}slide' % ns['s'] if ns else 'slide'):
        if slide.get('id') == sid:
            return slide
    return None

for sid in ['psF', 'psV']:
    slide = find_slide(sid)
    if slide is None:
        print(f'{sid}: NOT FOUND')
        continue
    xml_str = ET.tostring(slide, encoding='unicode')
    with open(BASE_DIR / f'page-{sid}.xml', 'w', encoding='utf-8') as f:
        f.write(xml_str)
    print(f'{sid}: {len(xml_str)} chars')
