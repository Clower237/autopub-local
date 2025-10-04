import csv, requests, os

API = "http://127.0.0.1:8000"
TOKEN = ""  # colle ici "Bearer xxxxx" (depuis /auth/login)

def create_job(row):
    files = {"thumbnail": open(os.path.join("bulk_thumbs", row["thumbnail"]), "rb")}
    data = {
        "title": row["title"],
        "description": row["description"],
        "tags": row["tags"],
        "script_text": row["script_text"],
        "voice_category": row["voice_category"],
        "speed": row.get("speed","1.3"),
        "publish_iso": row.get("publish_iso",""),
        "voice": "",
    }
    r = requests.post(f"{API}/jobs", headers={"Authorization": TOKEN}, files=files, data=data, timeout=120)
    print(row["title"], "->", r.status_code)

if __name__ == "__main__":
    with open("jobs.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            create_job(row)
