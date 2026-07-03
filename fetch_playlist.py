import urllib.request
import urllib.parse
import json
import os
import re
from datetime import datetime

PLAYLIST_URL = "https://www.bilibili.com/opus/1189914637774094353"
DATA_FILE = "data/playlist.json"
AVATAR_CACHE_FILE = "data/avatars.json"

PRESET_AVATARS = {}

def fetch_artist_avatar(artist_name):
    if artist_name in PRESET_AVATARS:
        return PRESET_AVATARS[artist_name]
    
    cache = load_avatar_cache()
    if artist_name in cache:
        return cache[artist_name]
    
    try:
        url = f"https://music.163.com/api/search/get/web?type=100&s={urllib.parse.quote(artist_name)}&limit=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://music.163.com/"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        if data.get("result") and data["result"].get("artists"):
            artists = data["result"]["artists"]
            if artists:
                avatar_url = artists[0].get("picUrl")
                if avatar_url:
                    cached_url = avatar_url.replace("300x300", "100x100")
                    cache[artist_name] = cached_url
                    save_avatar_cache(cache)
                    return cached_url
    except Exception as e:
        pass
    
    try:
        url = f"https://www.last.fm/music/{urllib.parse.quote(artist_name)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")
        
        match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if match:
            cache[artist_name] = match.group(1)
            save_avatar_cache(cache)
            return match.group(1)
        
        match = re.search(r'<img[^>]*class="artist-image[^>]*src="([^"]+)"', html)
        if match:
            cache[artist_name] = match.group(1)
            save_avatar_cache(cache)
            return match.group(1)
    except Exception as e:
        pass
    return None

def load_avatar_cache():
    if os.path.exists(AVATAR_CACHE_FILE):
        try:
            with open(AVATAR_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_avatar_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(AVATAR_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def fetch_playlist():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.bilibili.com/"
    }
    
    try:
        req = urllib.request.Request(PLAYLIST_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8")
        
        title = extract_title(html)
        content = extract_content(html)
        
        if content:
            songs = parse_content(content)
            avatars = fetch_all_avatars(songs)
            
            playlist = {
                "title": title or "直播间点歌单",
                "author": "toutou",
                "updated_at": datetime.now().isoformat(),
                "total_songs": sum(len(group["songs"]) for group in songs),
                "groups": songs,
                "avatars": avatars
            }
            
            os.makedirs("data", exist_ok=True)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(playlist, f, ensure_ascii=False, indent=2)
            
            print(f"Successfully fetched playlist at {datetime.now()}")
            print(f"Title: {playlist['title']}")
            print(f"Total groups: {len(songs)}, Total songs: {playlist['total_songs']}")
            print(f"Avatars fetched: {len(avatars)}")
            return playlist
        else:
            print("Failed to extract content from page")
            return None
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return None

def extract_title(html):
    match = re.search(r'<title>(.*?)</title>', html)
    if match:
        return match.group(1).strip()
    return None

def extract_content(html):
    text = re.sub(r'<[^>]+>', '\n', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\s+', '\n', text)
    
    lines = text.split('\n')
    filtered_lines = []
    
    in_playlist = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("【女歌手系列】"):
            in_playlist = True
        if in_playlist:
            if line.startswith("本文为我原创"):
                break
            filtered_lines.append(line)
    
    if filtered_lines:
        return '\n'.join(filtered_lines)
    
    json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
    match = re.search(json_pattern, html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            opus_data = data.get('opus', {}).get('detail', {})
            content = opus_data.get('content', '')
            if content:
                return content
        except:
            pass
    
    return None

def parse_content(content):
    groups = []
    current_group = None
    lines = content.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("【") and line.endswith("】"):
            if current_group:
                groups.append(current_group)
            current_group = {
                "name": line[1:-1],
                "songs": []
            }
        elif current_group and "-" in line:
            parts = line.split("-", 1)
            if len(parts) == 2:
                artist = parts[0].strip()
                song = parts[1].strip()
                if artist and song and len(song) > 1:
                    current_group["songs"].append({
                        "artist": artist,
                        "title": song
                    })
    
    if current_group:
        groups.append(current_group)
    
    return groups

def fetch_all_avatars(groups):
    artists = set()
    
    for group in groups:
        for song in group["songs"]:
            artists.add(song["artist"])
    
    avatars = {}
    for artist in artists:
        avatar = fetch_artist_avatar(artist)
        if avatar:
            avatars[artist] = avatar
    
    return avatars

if __name__ == "__main__":
    playlist = fetch_playlist()
    
    if not playlist or playlist["total_songs"] < 10:
        print("Using fallback data...")
        fallback_groups = [
                {
                    "name": "女歌手系列",
                    "songs": [
                        {"artist": "LiSA", "title": "ジェットロケット"},
                        {"artist": "LiSA", "title": "無色透明"},
                        {"artist": "LiSA", "title": "Believe in myself"},
                        {"artist": "LiSA", "title": "Believe in ourselves"},
                        {"artist": "LiSA", "title": "BEAUTIFUL WORLD"},
                        {"artist": "LiSA", "title": "いつかの手紙"},
                        {"artist": "LiSA", "title": "oath sign"},
                        {"artist": "LiSA", "title": "シルシ (刀剑神域)"},
                        {"artist": "LiSA", "title": "Catch the Moment"},
                        {"artist": "LiSA", "title": "unlasting"},
                        {"artist": "LiSA", "title": "红莲华（鬼灭）"},
                        {"artist": "LiSA", "title": "炎"},
                        {"artist": "LiSA", "title": "Little Braver(Angel Beats)"},
                        {"artist": "LiSA", "title": "Brave Song"},
                        {"artist": "LiSA", "title": "一番の宝物"},
                        {"artist": "LiSA", "title": "Crow Song"},
                        {"artist": "EGOIST", "title": "好きと言われた日"},
                        {"artist": "EGOIST", "title": "キズナミュージック"},
                        {"artist": "EGOIST", "title": "Ghost of a smile"},
                        {"artist": "EGOIST", "title": "Euterpeエウテルペ（罪恶王冠）"},
                        {"artist": "EGOIST", "title": "Depatures～あなたにおくるおくるアイの歌～（罪恶王冠）"},
                        {"artist": "EGOIST", "title": "The Everlasting Guilty Crown（罪恶王冠）"},
                        {"artist": "EGOIST", "title": "想いを巡らす100の事象"},
                        {"artist": "EGOIST", "title": "Planetes"},
                        {"artist": "EGOIST", "title": "All Alone With You（心理测量者）"},
                        {"artist": "Aimee Blackschleger", "title": "Release My Sou（罪恶王冠）"},
                        {"artist": "YUI", "title": "Good-bye days"},
                        {"artist": "YUI", "title": "I remember you"},
                        {"artist": "YUI", "title": "again(钢炼)"},
                        {"artist": "YUI", "title": "Rolling Star(死神)"},
                        {"artist": "YUI", "title": "CHE.R.RY (重生计划）"},
                        {"artist": "YUI", "title": "灯火(FLOWER FLOWER)"},
                        {"artist": "YUI", "title": "スタートライン"},
                        {"artist": "Aimer", "title": "カタオモイ"},
                        {"artist": "Aimer", "title": "コイワズライ"},
                        {"artist": "Aimer", "title": "糸(中島みゆき)"},
                        {"artist": "Aimer", "title": "Ref:rain（恋如雨止）"},
                        {"artist": "Aimer", "title": "六等星の夜（未来都市NO.6）"},
                        {"artist": "Aimer", "title": "茜さす(夏目友人帐)"},
                        {"artist": "爱缪", "title": "君はロックを聴かない"},
                        {"artist": "爱缪", "title": "貴方解剖純愛歌"},
                        {"artist": "爱缪", "title": "マリーゴールド"},
                        {"artist": "爱缪", "title": "猫(DISH)"},
                        {"artist": "椎名林檎", "title": "17"},
                        {"artist": "椎名林檎", "title": "ギブス"},
                        {"artist": "美波", "title": "水中リフレクション"},
                        {"artist": "美波", "title": "カワキヲアメク"},
                        {"artist": "さユり", "title": "花の塔"},
                        {"artist": "さユり", "title": "ミカヅキ"},
                        {"artist": "コレサワ", "title": "たばこ"},
                        {"artist": "yama", "title": "春を告げる"},
                        {"artist": "ano", "title": "AIDA"},
                        {"artist": "tuki.", "title": "晚餐歌"},
                        {"artist": "TRUE", "title": "Sincerely"},
                        {"artist": "りりあ。", "title": "失恋ソング沢山聴いて～泣いてばかりの私はもう。"},
                        {"artist": "hitomi", "title": "Love 2000"},
                        {"artist": "花澤香菜", "title": "恋愛サーキュレーション"},
                        {"artist": "小木曽雪菜", "title": "届かない恋"},
                        {"artist": "平野綾", "title": "WHITE ALBUM"},
                        {"artist": "ヒグチアイ", "title": "まっさらな大地"},
                        {"artist": "瑞葵", "title": "Avid"},
                        {"artist": "浜崎あゆみ", "title": "Dearest"},
                        {"artist": "ZARD", "title": "運命のルーレット廻して"},
                        {"artist": "Rie fu", "title": "Life Is Like A Boat"},
                        {"artist": "milet", "title": "Anytime Anywhere"},
                        {"artist": "大槻マキ", "title": "memories"},
                        {"artist": "eill", "title": "フィナーレ。"}
                    ]
                },
                {
                    "name": "男歌手系列",
                    "songs": [
                        {"artist": "優里", "title": "ベテルギウス"},
                        {"artist": "優里", "title": "ドライフラワー"},
                        {"artist": "米津玄师", "title": "打上花火"},
                        {"artist": "なとり", "title": "プロポーズ"},
                        {"artist": "藤井風", "title": "満ちてゆく"},
                        {"artist": "秦基博", "title": "Rain"},
                        {"artist": "秦基博", "title": "ひまわりの約束"},
                        {"artist": "Ayase", "title": "夜撫でるメノウ"},
                        {"artist": "喜多修平", "title": "一斉の声（夏目友人帐）"},
                        {"artist": "桑田佳祐", "title": "明日晴れるかな"}
                    ]
                },
                {
                    "name": "乐队/组合系列",
                    "songs": [
                        {"artist": "ヨルシカ", "title": "だから僕は音楽を辞めた"},
                        {"artist": "ヨルシカ", "title": "パレード"},
                        {"artist": "ヨルシカ", "title": "言って。"},
                        {"artist": "ヨルシカ", "title": "都落ち"},
                        {"artist": "ヨルシカ", "title": "老人と海"},
                        {"artist": "ヨルシカ", "title": "ただ君に晴れ"},
                        {"artist": "ヨルシカ", "title": "風を食む"},
                        {"artist": "ヨルシカ", "title": "ノーチラス"},
                        {"artist": "ヨルシカ", "title": "夜行"},
                        {"artist": "ヨルシカ", "title": "盗作"},
                        {"artist": "ヨルシカ", "title": "雨とカプチーノ"},
                        {"artist": "ヨルシカ", "title": "いさな"},
                        {"artist": "ヨルシカ", "title": "憂、燦々"},
                        {"artist": "ヨルシカ", "title": "雪国"},
                        {"artist": "ヨルシカ", "title": "嘘月(想哭的我带上了猫的面具)"},
                        {"artist": "ヨルシカ", "title": "花に亡霊"},
                        {"artist": "ヨルシカ", "title": "アルジャーノン（黄昏时分、牵着手）"},
                        {"artist": "ヨルシカ", "title": "太陽（正体）"},
                        {"artist": "ヨルシカ", "title": "忘れてください"},
                        {"artist": "ヨルシカ", "title": "斜陽（我心里危险的东西）"},
                        {"artist": "ヨルシカ", "title": "茜"},
                        {"artist": "supercell", "title": "My Dearest(罪恶王冠)"},
                        {"artist": "supercell", "title": "Perfect Day"},
                        {"artist": "supercell", "title": "カレ"},
                        {"artist": "supercell", "title": "罪人"},
                        {"artist": "supercell", "title": "終わりへ向かう始まりの歌、"},
                        {"artist": "supercell", "title": "夜が明けるよ"},
                        {"artist": "supercell", "title": "银色飞行船"},
                        {"artist": "supercell", "title": "君の知ない物語(化物语)"},
                        {"artist": "supercell", "title": "星が瞬くこんな夜に"},
                        {"artist": "supercell", "title": "リルモア"},
                        {"artist": "ずっと真夜中でいいのに。", "title": "秒針を噛む"},
                        {"artist": "ずっと真夜中でいいのに。", "title": "正しくなれない"},
                        {"artist": "ずっと真夜中でいいのに。", "title": "不法侵入"},
                        {"artist": "ずっと真夜中でいいのに。", "title": "Dear Mr「F」"},
                        {"artist": "YOASOBI", "title": "群青"},
                        {"artist": "YOASOBI", "title": "夜に駆ける"},
                        {"artist": "あたらよ", "title": "十月無口な君を忘れる"},
                        {"artist": "あたらよ", "title": "明け方の夏"},
                        {"artist": "あたらよ", "title": "嘘つき"},
                        {"artist": "あたらよ", "title": "夏霞"},
                        {"artist": "あたらよ", "title": "また夏を追う"},
                        {"artist": "あたらよ", "title": "僕は…(心危)"},
                        {"artist": "あたらよ", "title": "晴るる"},
                        {"artist": "あたらよ", "title": "夏が来るたび"},
                        {"artist": "あたらよ", "title": "朝凪"},
                        {"artist": "SCANDAL", "title": "声"},
                        {"artist": "THE MUSMUS", "title": "ミュゲー"},
                        {"artist": "THE MUSMUS", "title": "F*** Darlin'"},
                        {"artist": "ZONE", "title": "secret base ~君がくれたもの~"},
                        {"artist": "chilldspot", "title": "Kiss me before I rise"},
                        {"artist": "Hump Back", "title": "拝啓、少年よ"},
                        {"artist": "チャットモンチー", "title": "恋愛スピリッツ"},
                        {"artist": "HoneyWorks", "title": "決戦スピリッツ"},
                        {"artist": "いきものがかり", "title": "ブルーバード"},
                        {"artist": "LONGMAN", "title": "spiral"},
                        {"artist": "RAM WIRE", "title": "僕らの手には何もないけど、"},
                        {"artist": "SPYAIR", "title": "My Friend"},
                        {"artist": "SPYAIR", "title": "オレンジ"},
                        {"artist": "RADWIMPS", "title": "me me she"},
                        {"artist": "RADWIMPS", "title": "25コ目の染色体"},
                        {"artist": "RADWIMPS", "title": "有心論"},
                        {"artist": "RADWIMPS", "title": "夢灯籠"},
                        {"artist": "RADWIMPS", "title": "Tummy"},
                        {"artist": "OOR", "title": "Wherever you are"},
                        {"artist": "OOR", "title": "Heartache"},
                        {"artist": "GReeeeN", "title": "愛唄"},
                        {"artist": "Mrs. GREEN APPLE", "title": "Lulu"},
                        {"artist": "Mrs. GREEN APPLE", "title": "ダンスホール"},
                        {"artist": "Mrs. GREEN APPLE", "title": "春愁"},
                        {"artist": "Vaundy", "title": "怪獣の花唄"},
                        {"artist": "Official髭男dism", "title": "Pretender"},
                        {"artist": "The ROOTLESS", "title": "One day"},
                        {"artist": "WANDS", "title": "世界が終るまでは..."},
                        {"artist": "MONGOL800", "title": "小さな恋のうた"},
                        {"artist": "THE BLUE HEARTS", "title": "Linda Linda"}
                    ]
                },
                {
                    "name": "少女系列",
                    "songs": [
                        {"artist": "放課後ティータイム", "title": "天使にふれたよ!"},
                        {"artist": "結束バンド", "title": "青春コンプレックス"},
                        {"artist": "結束バンド", "title": "ギターと孤独と蒼い惑星"},
                        {"artist": "結束バンド", "title": "転がる岩、君に朝が降る"},
                        {"artist": "結束バンド", "title": "星座になれたら"},
                        {"artist": "結束バンド", "title": "青い春と西の空"},
                        {"artist": "結束バンド", "title": "フラッシュバッカー"},
                        {"artist": "トゲナシトゲアリ", "title": "空の箱"},
                        {"artist": "トゲナシトゲアリ", "title": "雑踏、僕らの街"},
                        {"artist": "トゲナシトゲアリ", "title": "誰にもなれない私だから"},
                        {"artist": "トゲナシトゲアリ", "title": "声なき魚"},
                        {"artist": "トゲナシトゲアリ", "title": "蝶に結いた赤い糸"},
                        {"artist": "Ave Mujica", "title": "Imprisoned XII"},
                        {"artist": "Ave Mujica", "title": "天球(そら)のMúsica"},
                        {"artist": "Poppin'Party", "title": "キズナミュージック♪"},
                        {"artist": "Roselia", "title": "Neo-Aspect"},
                        {"artist": "My Go!!!!!", "title": "迷星叫"},
                        {"artist": "My Go!!!!!", "title": "春日影"},
                        {"artist": "My Go!!!!!", "title": "過惰幻"},
                        {"artist": "μ's", "title": "Snow Halation"},
                        {"artist": "μ's", "title": "CHASE!"},
                        {"artist": "μ's", "title": "なわとび"},
                        {"artist": "μ's", "title": "愛してるばんざーい!"},
                        {"artist": "赛马娘", "title": "Everlasting BEATS"}
                    ]
                },
                {
                    "name": "P主系列",
                    "songs": [
                        {"artist": "古川本舗", "title": "Alice"},
                        {"artist": "古川本舗", "title": "Good Morning EMMA Sympson"},
                        {"artist": "DECO*27", "title": "at"},
                        {"artist": "DECO*27", "title": "愛言葉1"},
                        {"artist": "Orangestar", "title": "アスノヨゾラ哨戒班"},
                        {"artist": "Orangestar", "title": "雨き声残響"},
                        {"artist": "n-buna", "title": "夜明けと蛍"},
                        {"artist": "bassy", "title": "mistake"},
                        {"artist": "keeno", "title": "glow"},
                        {"artist": "れるりり", "title": "神のまにまに"},
                        {"artist": "ナノウ", "title": "Hello/How are you"},
                        {"artist": "DATEKEN", "title": "君が生まれた日"},
                        {"artist": "EasyPop", "title": "ハッピーシンセサイザ"},
                        {"artist": "ナユタン星人", "title": "惑星ループ"},
                        {"artist": "40mp", "title": "恋愛裁判"},
                        {"artist": "黒うさP", "title": "千本桜"},
                        {"artist": "ねこぼーろ", "title": "弾けないギターを片手に。"},
                        {"artist": "Dixie Flatline", "title": "Just Be Friends"},
                        {"artist": "一之瀬ユウ", "title": "心做し"},
                        {"artist": "Aqu3ra", "title": "星降る海"}
                    ]
                }
            ]
        
        avatars = fetch_all_avatars(fallback_groups)
        
        playlist = {
            "title": "直播间点歌单（toutouです）",
            "author": "八突",
            "updated_at": datetime.now().isoformat(),
            "total_songs": 200,
            "groups": fallback_groups,
            "avatars": avatars
        }
        
        os.makedirs("data", exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(playlist, f, ensure_ascii=False, indent=2)
        print(f"Fallback data saved with {len(avatars)} avatars")