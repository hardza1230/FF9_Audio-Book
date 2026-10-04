import os, json, requests, subprocess

gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
github_token = os.environ.get('GITHUB_TOKEN', '').strip()
issue_num = os.environ.get('ISSUE_NUMBER')
comment = os.environ.get('COMMENT_BODY', '')
repo_name = os.environ.get('REPO_NAME')

user_prompt = comment.replace('/gemini', '', 1).strip()
system_instruction = "คุณคือ AI ผู้ช่วยสร้าง FF9 Audio-Book ตอบเป็น JSON: {\"reply\":\"ข้อความอธิบายภาษาไทย\",\"files\":[{\"path\":\"โฟลเดอร์/ชื่อไฟล์\",\"content\":\"เนื้อหา\"}]}"

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={gemini_key}"
payload = {
    "system_instruction": {"parts": [{"text": system_instruction}]},
    "contents": [{"parts": [{"text": user_prompt}]}],
    "generationConfig": {"response_mime_type": "application/json"}
}

res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
created_files = []
reply_text = ""

if res.status_code == 200:
    try:
        data = res.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        parsed = json.loads(raw_text)
        reply_text = parsed.get("reply", "")

        # ดึงข้อมูล Token Usage จาก API
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        candidates_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)

        for f in parsed.get("files", []):
            p = f.get("path")
            if p:
                d = os.path.dirname(p)
                if d: os.makedirs(d, exist_ok=True)
                with open(p, "w", encoding="utf-8") as out:
                    out.write(f.get("content", ""))
                created_files.append(p)

        if created_files:
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", "."], check=True)
            diff = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if diff.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"Auto-create files via Issue #{issue_num}"], check=True)
                subprocess.run(["git", "push"], check=True)
                reply_text += "\n\n---\n📁 **สร้างและ Push ไฟล์สำเร็จ:**\n" + "\n".join([f"- `{x}`" for x in created_files])

        # แนบรายงานสรุป Token ท้ายข้อความ
        reply_text += (
            f"\n\n---\n"
            f"📊 **สรุปการใช้ Token รอบนี้:**\n"
            f"- **Input Tokens (คำสั่ง + บริบท):** `{prompt_tokens}`\n"
            f"- **Output Tokens (เนื้อหาที่บอทตอบ/โค้ด):** `{candidates_tokens}`\n"
            f"- **Total Tokens รวม:** `{total_tokens}`"
        )

    except Exception as e:
        reply_text = f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}"
else:
    reply_text = f"API Error (HTTP {res.status_code}): {res.text}"

gh_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_num}/comments"
requests.post(gh_url, headers={"Authorization": f"token {github_token}"}, json={"body": f"### 🤖 Gemini Response:\n\n{reply_text}"})
