import json
path = r'd:\Vidiolingua\asr\output\Vidiolingua_Test_Official_transcription.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)
print(f"Language: {data['language']} | Segments: {len(data['segments'])}")
print()
for i, s in enumerate(data['segments']):
    dur = s['end'] - s['start']
    words = [w['word'] for w in s.get('words', [])[:4]]
    print(f"  [{i}] {s['start']:.1f}s-{s['end']:.1f}s ({dur:.1f}s) | {s['text'].strip()}")
    if words:
        print(f"       words: {words}...")
