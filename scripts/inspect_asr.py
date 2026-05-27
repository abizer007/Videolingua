import json

path = r'd:\Vidiolingua\asr\output\WIN_20250426_17_20_22_Pro_transcription.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)

print(f"Language : {data['language']} (conf={data['language_confidence']:.2f})")
print(f"Segments : {len(data['segments'])}")
print()
print("First 3 segments:")
for s in data['segments'][:3]:
    print(f"  [{s['start']:.1f}s - {s['end']:.1f}s] speaker={s.get('speaker')} | {s['text'].strip()}")
    if s.get('words'):
        words_preview = [w['word'] for w in s['words'][:6]]
        print(f"    word-timestamps: {words_preview}")
