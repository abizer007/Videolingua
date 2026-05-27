"""
End-to-end pipeline API test.
Submits the demo video and polls for job completion.
"""
import requests
import time
import json

BASE = "http://localhost:8000"
VIDEO_PATH = r"d:\Vidiolingua\Vidiolingua_Test_Official.mp4"

print("=== VidioLingua E2E Pipeline Test ===")
print()

# 1. Submit job
print("[1] Submitting job...")
with open(VIDEO_PATH, "rb") as f:
    resp = requests.post(
        f"{BASE}/api/upload",
        files={"video": ("demo.mp4", f, "video/mp4")},
        data={
            "languages": '["fr"]',
            "sourceLanguage": "en",
            "voiceOptions": "{}",
        },
        timeout=30,
    )

if resp.status_code not in (200, 201, 202):
    print(f"FAIL: Submit returned {resp.status_code}: {resp.text}")
    exit(1)

job = resp.json()
job_id = job.get("jobId") or job.get("job_id") or job.get("id")
print(f"  Job ID: {job_id}")
print()

# 2. Poll for completion
print("[2] Polling job status...")
start = time.time()
MAX_WAIT = 600  # 10 minutes

while time.time() - start < MAX_WAIT:
    status_resp = requests.get(f"{BASE}/api/job-status/{job_id}", timeout=10)
    if status_resp.status_code != 200:
        print(f"  Status check failed: {status_resp.status_code}")
        break
    
    status = status_resp.json()
    stage = status.get("stage", "unknown")
    progress = status.get("progress", 0)
    elapsed = int(time.time() - start)
    print(f"  [{elapsed:>3}s] stage={stage:<15} progress={progress}%")
    
    if stage == "complete":
        print()
        print("[3] PIPELINE COMPLETE!")
        result_resp = requests.get(f"{BASE}/api/result/{job_id}", timeout=10)
        if result_resp.status_code != 200:
            print(f"  Result fetch failed: {result_resp.status_code}: {result_resp.text}")
            break
        result = result_resp.json()
        metrics = result.get("metrics", {})
        print(f"  Languages processed: {metrics.get('languagesProcessed', 0)}")
        print(f"  Total time:          {metrics.get('totalTime', 0)}s")
        print(f"  BGM preserved:       {metrics.get('bgmPreserved', False)}")
        print(f"  Speakers detected:   {metrics.get('speakersDetected', 0)}")
        print()
        videos = result.get("localizedVideos", [])
        for v in videos:
            print(f"  Dubbed [{v['language']}]: {v['url']}")
        break
    elif stage == "error":
        print()
        print(f"[ERROR] Pipeline failed: {status.get('error', 'unknown')}")
        break
    
    time.sleep(10)
else:
    print("TIMEOUT: Pipeline did not complete within 10 minutes.")

print()
print("=== Test Complete ===")
