import json

path = r'd:\Vidiolingua\translation\output\WIN_20250426_17_20_22_Pro_transcription_es.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)

print('=== Spanish Translation Sample ===')
print('Engine:', data.get('translation_engine'))
print()
for s in data['segments'][:3]:
    start = s['start']
    end = s['end']
    text = s['text']
    print(f'  [{start:.1f}s - {end:.1f}s] {text}')
