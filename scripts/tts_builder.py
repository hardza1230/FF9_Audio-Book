#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FF9 Audio-Book: TTS Builder Script
Converts text (default: Thai) into audio files using Google Text-to-Speech (gTTS).
Output directory: assets/audio
"""

import os
import argparse
from pathlib import Path
from typing import Optional, List, Dict

try:
    from gtts import gTTS
except ImportError:
    raise ImportError("กรุณาติดตั้ง gTTS ก่อนใช้งาน: pip install gTTS")

# กำหนดโฟลเดอร์ปลายทางเริ่มต้น
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "audio"


def ensure_output_dir(output_dir: Path) -> None:
    """สร้างโฟลเดอร์สำหรับเก็บไฟล์เสียงหากยังไม่มีอยู่"""
    output_dir.mkdir(parents=True, exist_ok=True)


def generate_speech(
    text: str,
    output_filename: str,
    lang: str = "th",
    slow: bool = False,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    แปลงข้อความเป็นไฟล์เสียงและบันทึกลงโฟลเดอร์ปลายทาง

    :param text: ข้อความที่ต้องการแปลงเป็นเสียง
    :param output_filename: ชื่อไฟล์เสียง (เช่น intro.mp3)
    :param lang: รหัสภาษา (ค่าเริ่มต้น 'th')
    :param slow: ความเร็วเสียงช้าลงหรือไม่ (ค่าเริ่มต้น False)
    :param output_dir: โฟลเดอร์ปลายทาง (ค่าเริ่มต้น assets/audio)
    :return: Path ของไฟล์เสียงที่สร้างสำเร็จ
    """
    if not text.strip():
        raise ValueError("ข้อความไม่สามารถเป็นค่าว่างได้")

    target_dir = output_dir or DEFAULT_OUTPUT_DIR
    ensure_output_dir(target_dir)

    if not output_filename.endswith(".mp3"):
        output_filename = f"{output_filename}.mp3"

    target_path = target_dir / output_filename

    print(f"[*] กำลังแปลงเสียง: '{text[:30]}...' -> {target_path.name}")
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(target_path))
    print(f"[✓] บันทึกไฟล์สำเร็จ: {target_path}")

    return target_path


def batch_generate(
    dialogues: List[Dict[str, str]],
    lang: str = "th",
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    แปลงรายการบทพูดเป็นไฟล์เสียงแบบชุด

    :param dialogues: รายการ dictionary เช่น [{'filename': 'scene1_01.mp3', 'text': 'สวัสดี'}]
    """
    results = []
    for item in dialogues:
        path = generate_speech(
            text=item["text"],
            output_filename=item["filename"],
            lang=lang,
            output_dir=output_dir,
        )
        results.append(path)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="FF9 Audio-Book: Google TTS Audio Generator"
    )
    parser.add_argument(
        "-t", "--text", type=str, help="ข้อความภาษาไทยที่ต้องการแปลงเป็นเสียง"
    )
    parser.add_argument(
        "-f",
        "--input-file",
        type=str,
        help="ไฟล์ .txt ที่ต้องการอ่านข้อความเพื่อนำมาแปลงเสียง",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.mp3",
        help="ชื่อไฟล์เสียงปลายทาง (ค่าเริ่มต้น: output.mp3)",
    )
    parser.add_argument(
        "-l", "--lang", type=str, default="th", help="รหัสภาษา (ค่าเริ่มต้น: th)"
    )
    parser.add_argument(
        "--slow", action="store_true", help="พูดด้วยความเร็วที่ช้าลง"
    )

    args = parser.parse_args()

    text_to_speak = ""
    if args.input_file:
        file_path = Path(args.input_file)
        if not file_path.exists():
            print(f"[!] ไม่พบไฟล์: {file_path}")
            return
        with open(file_path, "r", encoding="utf-8") as f:
            text_to_speak = f.read().strip()
    elif args.text:
        text_to_speak = args.text.strip()
    else:
        # ตัวอย่างข้อความเริ่มต้นหากไม่ได้ระบุพารามิเตอร์
        text_to_speak = "ยินดีต้อนรับสู่โลกของ ไฟนอลแฟนตาซี 9 ออดิโอบุ๊ก"
        print("[*] ไม่ได้ระบุข้อความ ใช้ข้อความตัวอย่างเริ่มต้น...")

    try:
        generate_speech(
            text=text_to_speak,
            output_filename=args.output,
            lang=args.lang,
            slow=args.slow,
        )
    except Exception as e:
        print(f"[!] เกิดข้อผิดพลาดในการแปลงเสียง: {e}")


if __name__ == "__main__":
    main()
