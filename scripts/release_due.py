#!/usr/bin/env python3
"""予約した回のうち、公開時刻を過ぎたものを RSS に足して公開する。
- scheduled/*.json を見て、publish_at（JST）を過ぎたものを podcast.xml の先頭に追加
- 番組ページ（index.html）を RSS から作り直す
- --push を付けると、変更があれば commit して GitHub に上げる
"""
import json, os, glob, datetime, html, re, subprocess, sys, shutil
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://kazuki-onishi.github.io/kyohari'
JST = datetime.timezone(datetime.timedelta(hours=9))
AUTHOR = ('Kazuki-Onishi', '106076158+Kazuki-Onishi@users.noreply.github.com')

def item_xml(ep, pub):
    return (
        "    <item>\n"
        f"      <title>{html.escape(ep['title'])}</title>\n"
        f"      <description><![CDATA[{ep['description_html']}]]></description>\n"
        f"      <enclosure url=\"{BASE}/{ep['file']}\" length=\"{ep['length']}\" type=\"audio/mpeg\"/>\n"
        f"      <guid isPermaLink=\"false\">{ep['guid']}</guid>\n"
        f"      <pubDate>{format_datetime(pub)}</pubDate>\n"
        f"      <itunes:duration>{ep['duration']}</itunes:duration>\n"
        f"      <itunes:episode>{ep['episode']}</itunes:episode>\n"
        "      <itunes:episodeType>full</itunes:episodeType>\n"
        "      <itunes:explicit>false</itunes:explicit>\n"
        "    </item>\n\n")

def build_index(xml):
    items = re.findall(r'<item>.*?</item>', xml, flags=re.S)
    cards = []
    for it in items:
        t = re.search(r'<title>(.*?)</title>', it).group(1)
        d = re.search(r'<!\[CDATA\[(.*?)\]\]>', it, flags=re.S).group(1)
        u = re.search(r'enclosure url="(.*?)"', it).group(1).replace(BASE, '.')
        cards.append(f'<article class="ep"><h2>{t}</h2><audio controls preload="none" src="{u}"></audio><p>{d}</p></article>')
    desc = re.search(r'<channel>.*?<description>(.*?)</description>', xml, flags=re.S).group(1)
    tpl = open(os.path.join(ROOT, 'scripts', 'index_template.html'), encoding='utf-8').read()
    return tpl.replace('{{DESC}}', desc).replace('{{DESC_SHORT}}', html.escape(desc[:110])).replace('{{CARDS}}', '\n'.join(cards))

def main():
    push = '--push' in sys.argv
    now = datetime.datetime.now(JST)
    xml_path = os.path.join(ROOT, 'podcast.xml')
    xml = open(xml_path, encoding='utf-8').read()
    released = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'scheduled', '*.json'))):
        ep = json.load(open(p, encoding='utf-8'))
        at = datetime.datetime.fromisoformat(ep['publish_at'])
        if at.tzinfo is None: at = at.replace(tzinfo=JST)
        if at > now: continue
        if f">{ep['guid']}<" in xml:
            print('既にRSSにある:', ep['guid'])
        else:
            if not os.path.exists(os.path.join(ROOT, ep['file'])):
                print('音声ファイルが無いので保留:', ep['file']); continue
            i = xml.index('    <item>')
            xml = xml[:i] + item_xml(ep, at) + xml[i:]
            print('公開:', ep['title'], at.isoformat())
        shutil.move(p, os.path.join(ROOT, 'scheduled', 'released', os.path.basename(p)))
        released.append(ep['title'])
    if released:
        open(xml_path, 'w', encoding='utf-8').write(xml)
    idx = build_index(xml)
    if open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read() != idx:
        open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(idx)
    if push:
        st = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
        if st:
            msg = '予約していた回を公開: ' + ' / '.join(released) if released else '番組ページを更新'
            subprocess.run(['git', '-C', ROOT, 'add', '-A'], check=True)
            subprocess.run(['git', '-C', ROOT, '-c', f'user.name={AUTHOR[0]}', '-c', f'user.email={AUTHOR[1]}', 'commit', '-q', '-m', msg], check=True)
            subprocess.run(['git', '-C', ROOT, '-c', 'credential.helper=', '-c', 'credential.helper=!/opt/homebrew/bin/gh auth git-credential', 'push', '-q'], check=True)
            print('GitHubに反映:', msg)

if __name__ == '__main__':
    main()
