import os, re, json, requests, subprocess
from youtube_transcript_api import YouTubeTranscriptApi

gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
github_token = os.environ.get('GITHUB_TOKEN', '').strip()
issue_num = os.environ.get('ISSUE_NUMBER')
comment = os.environ.get('COMMENT_BODY', '')
repo_name = os.environ.get('REPO_NAME')

user_prompt = comment.replace('/gemini', '', 1).strip()

# ฟังก์ชันดึง Video ID จากลิงก์ YouTube
def get_yt_video_id(text):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1)
    return None

video_id = get_yt_video_id(user_prompt)
transcript_context = ""

# หากพบคลิป YouTube ให้ดึงบทพูดพร้อมเวลา
if video_id:
    try:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['th', 'en', 'ja'])
            raw_transcript = transcript.fetch()
        except Exception:
            raw_transcript = YouTubeTranscriptApi.get_transcript(video_id)

        lines = []
        for item in raw_transcript:
            m, s = divmod(int(item['start']), 60)
            lines.append(f"[{m:02d}:{s:02d}] {item['text']}")
        transcript_context = "\n".join(lines)
    except Exception as yt_err:
        transcript_context = f"[ไม่สามารถดึง Transcript จากคลิปได้: {yt_err}]"

# ประกอบ Prompt
final_prompt = user_prompt
if transcript_context:
    final_prompt += (
        f"\n\n--- ข้อมูลบทพูดและลำดับเวลาจากคลิป YouTube ---\n"
        f"{transcript_context}\n"
        f"--------------------------------------------------\n"
        f"คำสั่งบังคับ: โปรดเรียงลำดับบทพูดตามไทม์ไลน์เวลาข้างต้น ห้ามสลับเหตุการณ์ "
        f"และจัดกลุ่มผู้พูด (เช่น Zidane, Steiner, Garnet, Narrator) ให้ถูกต้อง"
    )

system_instruction = (
    "คุณคือ AI ผู้ช่วยพัฒนาโปรเจกต์ 'FF9 Audio-Book' บน GitHub\n"
    "ตอบกลับในรูปแบบ JSON เท่านั้น:\n"
    "{\n"
    '  "reply": "ข้อความอธิบายภาษาไทย",\n'
    '  "files": [\n'
    '    {"path": "โฟลเดอร์/ชื่อไฟล์.นามสกุล", "content": "เนื้อหาของไฟล์"}\n'
    "  ]\n"
    "}"
)

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={gemini_key}"
payload = {
    "system_instruction": {"parts": [{"text": system_instruction}]},
    "contents": [{"parts": [{"text": final_prompt}]}],
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

        reply_text += (
            f"\n\n---\n"
            f"📊 **สรุปการใช้ Token:**\n"
            f"- Input: `{prompt_tokens}` | Output: `{candidates_tokens}` | Total: `{total_tokens}`"
        )

    except Exception as e:
        reply_text = f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}"
else:
    reply_text = f"API Error (HTTP {res.status_code}): {res.text}"

gh_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_num}/comments"
requests.post(gh_url, headers={"Authorization": f"token {github_token}"}, json={"body": f"### 🤖 Gemini Response:\n\n{reply_text}"})
