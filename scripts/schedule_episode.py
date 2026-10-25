#!/usr/bin/env python3
"""新しい回を予約に入れる（Claude が毎回使う）。
使い方:
  python3 scripts/schedule_episode.py --master 完成版.wav --episode 3 \
      --title "#3 ..." --desc 概要欄.html --at "2026-11-03T07:00" [--push]
- 完成版（WAV）を 96kbps モノラルの mp3 にして episodes/epN.mp3 に置く
- scheduled/epN.json を作る（公開時刻 --at、JST）
- --at を省略すると「次の火曜 6:00」
"""
import argparse, datetime, json, os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = datetime.timezone(datetime.timedelta(hours=9))
ap = argparse.ArgumentParser()
ap.add_argument('--master', required=True); ap.add_argument('--episode', type=int, required=True)
ap.add_argument('--title', required=True); ap.add_argument('--desc', required=True)
ap.add_argument('--at'); ap.add_argument('--push', action='store_true')
a = ap.parse_args()
if a.at:
    at = datetime.datetime.fromisoformat(a.at).replace(tzinfo=JST)
else:
    n = datetime.datetime.now(JST); d = (1 - n.weekday()) % 7 or 7
    at = (n + datetime.timedelta(days=d)).replace(hour=6, minute=0, second=0, microsecond=0)
art = os.path.join(ROOT, 'scripts', 'art800.jpg')
out = os.path.join(ROOT, 'episodes', f'ep{a.episode}.mp3')
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',a.master,'-i',art,'-map','0:a','-map','1:v',
    '-ac','1','-ar','44100','-c:a','libmp3lame','-b:a','96k','-c:v','mjpeg','-disposition:v','attached_pic','-id3v2_version','3',
    '-metadata',f'title={a.title}','-metadata','artist=大西一輝','-metadata','album=京大院生、ハリウッドスターへの道',
    '-metadata',f'track={a.episode}','-metadata',f'date={at.year}',out], check=True)
dur = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',out],capture_output=True,text=True).stdout)
desc = open(a.desc, encoding='utf-8').read().strip()
ep = dict(episode=a.episode, title=a.title, description_html=desc, file=f'episodes/ep{a.episode}.mp3',
          length=os.path.getsize(out), duration=int(round(dur)), guid=f'onishi-radio-ep{a.episode}', publish_at=at.isoformat())
json.dump(ep, open(os.path.join(ROOT,'scheduled',f'ep{a.episode}.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print(json.dumps(ep, ensure_ascii=False, indent=2)[:600])
if a.push:
    au = ('Kazuki-Onishi','106076158+Kazuki-Onishi@users.noreply.github.com')
    subprocess.run(['git','-C',ROOT,'add','-A'],check=True)
    subprocess.run(['git','-C',ROOT,'-c',f'user.name={au[0]}','-c',f'user.email={au[1]}','commit','-q','-m',f'第{a.episode}回を予約（{at:%m/%d %H:%M}公開）'],check=True)
    subprocess.run(['git','-C',ROOT,'-c','credential.helper=','-c','credential.helper=!/opt/homebrew/bin/gh auth git-credential','push','-q'],check=True)
