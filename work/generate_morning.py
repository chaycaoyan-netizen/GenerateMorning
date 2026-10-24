#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日早安生成器 —— 成都·青羊区天气 + 历史上的今天。林林林林林林林

运行后输出一条可直接转发到微信的早安消息，并保存到 outputs/ 目录。
天气数据来自 Open-Meteo（免费、无需密钥）；历史数据来自开源中文数据集
「历史上的今天」（源自维基百科），通过 GitHub API / jsDelivr 获取，本地有缓存兜底。
"""

import base64
import datetime as dt
import json
import os
import ssl
import sys
import urllib.request
from zoneinfo import ZoneInfo

CITY = "成都 · 青羊区"
LAT = 30.6740
LON = 104.0030
TZ = ZoneInfo("Asia/Shanghai")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE_DIR = os.path.join(HERE, "cache")
OUT_DIR = os.path.join(ROOT, "outputs")


def _ssl_context():
    """优先使用系统 CA 证书，找不到时降级为不校验（仅用于读取公开数据）。"""
    for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl._create_unverified_context()


SSL_CTX = _ssl_context()

# ---------------- 天气 ----------------

# WMO 天气代码 -> (天气名, 文艺描述, 温馨提示)
WMO = {
    0: ("晴", "天朗气清，阳光正好。", "适合出门走走，晒晒太阳。"),
    1: ("晴间多云", "云很薄，阳光偶尔漏下来。", "早晚微凉，出门带件薄外套。"),
    2: ("多云", "云朵在天空慢慢散步。", "体感舒适，适合慢慢走。"),
    3: ("阴", "天光柔和，云层低垂，像一封没写完的信。", "适合慢一点，给自己泡杯热茶。"),
    45: ("雾", "薄雾笼着街巷，像未醒的梦。", "能见度低，出门注意安全。"),
    48: ("雾", "雾蒙蒙的清晨，别有一番意境。", "注意保暖和出行安全。"),
    51: ("毛毛雨", "细雨如丝，空气里都是湿润的味道。", "记得带伞，听雨声也很好。"),
    53: ("小雨", "雨声细细，像谁在轻轻说话。", "出门带伞，鞋要防滑。"),
    55: ("小雨", "雨滴不紧不慢地落。", "带把伞，慢慢走。"),
    61: ("小雨", "细雨绵绵，润物无声。", "带伞，留意路面湿滑。"),
    63: ("中雨", "雨势渐起，天地被洗得干净。", "记得带伞，出行慢行。"),
    65: ("大雨", "雨声喧哗，世界安静下来。", "尽量待在室内，出门务必带伞。"),
    71: ("小雪", "若有细雪飘落，空气清冽。", "天冷，记得添衣。"),
    73: ("中雪", "雪落无声，世界素净。", "注意保暖和防滑。"),
    75: ("大雪", "天地皆白，静谧而辽阔。", "出行注意安全，多穿一点。"),
    80: ("阵雨", "阵雨忽来忽去，像路过的心情。", "带伞，总不会错。"),
    81: ("阵雨", "雨来得急，去得也快。", "带伞，留意天气变化。"),
    82: ("强阵雨", "雨点密集，来得轰轰烈烈。", "尽量避雨，出门带伞。"),
    95: ("雷阵雨", "雷声隐隐，空气潮湿。", "尽量待在室内，注意安全。"),
    96: ("雷阵雨", "雷雨交加，注意避雷。", "减少外出，安全第一。"),
    99: ("雷雨", "雷声隆隆，大雨如注。", "尽量待在室内。"),
}

EMOJI = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌦️", 81: "🌦️", 82: "🌧️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


def fetch_json(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Asia%2FShanghai&forecast_days=1"
    )
    raw = fetch_json(url)
    return json.loads(raw)


# ---------------- 历史上的今天 ----------------

# 敏感/沉重内容直接排除，早安只讲轻松、明亮的事。
BLOCK = [
    "战争", "战役", "入侵", "占领", "沦陷", "屠杀", "刺杀", "政变", "罢免",
    "绑架", "独裁", "毒枭", "禁书", "违禁", "分裂", "台独", "金门", "天安门",
    "六四", "法轮", "维吾尔", "藏独", "暴动", "起义", "战", "被捕", "处决",
]

COOL = {
    "航天": 5, "太空": 5, "卫星": 4, "火箭": 4, "探月": 5, "月球": 4, "宇宙": 4,
    "诗人": 4, "作家": 4, "作曲家": 4, "音乐": 3, "文学": 4, "画家": 4, "艺术家": 4,
    "小说": 3, "导演": 3, "科学家": 4, "发明": 4, "物理": 4, "化学": 4, "生物": 4,
    "数学": 4, "诺贝尔": 5, "中国": 2, "中华": 2, "四川": 3, "成都": 3,
    "北京": 2, "上海": 2, "联合国": 3, "创办人": 3, "企业家": 3, "世界": 1,
}


def history_score(entry):
    c = entry.get("content", "")
    t = entry.get("type", "")
    if not c or len(c) <= 5:
        return -99
    if any(k in c for k in BLOCK):
        return -99
    s = 0
    if len(c) > 55:
        s -= 3  # 太长，不适合早安短句
    if t == "birth":
        s += 1
        if "逝世" in c:
            s += 1  # 带生卒年的，通常是叫得出名字的人物
    for k, v in COOL.items():
        if k in c:
            s += v
    return s


def cache_path(md):
    return os.path.join(CACHE_DIR, f"{md}.json")


def fetch_history(m, d):
    """按「月-日」取历史条目，优先 GitHub API，其次 jsDelivr，最后本地缓存。"""
    m, d = str(m), str(d)
    variants = [f"{m}-{d:0>2}", f"{m}-{d}", f"{m:0>2}-{d:0>2}"]
    seen = []
    for md in variants:
        if md in seen:
            continue
        seen.append(md)
        sources = [
            (f"https://api.github.com/repos/LuoH-AN/TodayInHistory/contents/Wiki/WikiJson/{md}.json", "github"),
            (f"https://cdn.jsdelivr.net/gh/LuoH-AN/TodayInHistory@main/Wiki/WikiJson/{md}.json", "plain"),
        ]
        for url, kind in sources:
            try:
                headers = {"User-Agent": "morning-bot"}
                if kind == "github":
                    headers["Accept"] = "application/vnd.github+json"
                raw = fetch_json(url, headers=headers)
                if kind == "github":
                    raw = base64.b64decode(json.loads(raw)["content"])
                data = json.loads(raw)
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(cache_path(md), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                return data
            except Exception:
                continue
        # 本地缓存兜底
        p = cache_path(md)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise RuntimeError("无法获取「历史上的今天」数据")


def pick_entries(data, n=3):
    scored = [(history_score(e), e) for e in data]
    scored = [e for s, e in scored if s > 0]
    scored.sort(key=lambda e: history_score(e), reverse=True)
    chosen = scored[:n]
    chosen.sort(key=lambda e: e.get("year", ""))
    return chosen


# ---------------- 文案 ----------------

GREETINGS = [
    "早安。新的一天，从青羊区的一声问候开始。",
    "早上好。愿你今天的心情，和窗外的天气一样舒展。",
    "早安。日子缓缓，问候如约而至。",
    "早上好。愿你被这个清晨温柔以待。",
    "早安。把今天过成自己喜欢的样子。",
]

CLOSINGS = [
    "愿今天也有好事发生。",
    "祝你有柔软而明亮的一天。",
    "今天也要好好生活呀。",
    "愿你眼里有光，脚下有路。",
]

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def build_message(weather, entries, today):
    cur = weather["current"]
    daily = weather["daily"]
    code = daily["weather_code"][0]
    name, desc, tip = WMO.get(code, ("", "天气在悄悄变化。", "出门前看一眼天色。"))
    emoji = EMOJI.get(code, "")

    idx = today.timetuple().tm_yday
    greeting = GREETINGS[idx % len(GREETINGS)]
    closing = CLOSINGS[idx % len(CLOSINGS)]
    weekday = WEEKDAYS[today.weekday()]

    rise = daily["sunrise"][0][-5:]
    set_ = daily["sunset"][0][-5:]

    lines = [
        greeting,
        "",
        f"今天是 {today.month} 月 {today.day} 日，{weekday}。",
        f"{emoji} {desc}",
        "",
        f"现在 {cur['temperature_2m']:.0f}℃ · 体感 {cur['apparent_temperature']:.0f}℃",
        f"今日 {daily['temperature_2m_min'][0]:.0f} ~ {daily['temperature_2m_max'][0]:.0f}℃"
        f" · 日出 {rise} 日落 {set_}",
        tip,
        "",
        "—— 历史上的今天 ——",
    ]
    for e in entries:
        content = e["content"]
        if len(content) > 70:
            content = content[:70] + "…"
        lines.append(f"{e['year']} · {content}")
    lines += ["", closing]
    return "\n".join(lines)


def main():
    today = dt.datetime.now(TZ)
    weather = fetch_weather()
    data = fetch_history(today.month, today.day)
    entries = pick_entries(data)
    msg = build_message(weather, entries, today)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"早安_{today:%Y-%m-%d}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(msg + "\n")

    print(msg)
    print("\n---")
    print(f"已保存：{out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"生成失败：{exc}", file=sys.stderr)
        sys.exit(1)
