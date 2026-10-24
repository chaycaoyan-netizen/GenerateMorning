# 每日早安（成都 · 青羊区）

每天早上自动生成一条「文艺早安」，内容包含：

- 成都 · 青羊区的实时天气
- 历史上的今天（当天发生过的有趣事件）

生成之后复制一下，就能直接转发给微信好友。

## 快速开始

需要 Python 3.9+，无需安装任何第三方库。

```bash
python3 work/generate_morning.py
```

运行后会：

1. 从 Open-Meteo 抓取青羊区实时天气；
2. 从开源中文数据集「历史上的今天」抓取当天事件；
3. 生成一条文艺早安消息，打印到终端，并保存到 `outputs/早安_YYYY-MM-DD.txt`。

## 修改城市

编辑 `work/generate_morning.py` 顶部的 `LAT` / `LON`（经纬度）和 `CITY` 文案即可。

## 数据来源

- 天气：Open-Meteo（免费、无需密钥）
- 历史上的今天：LuoH-AN/TodayInHistory（开源，源自维基百科），通过 GitHub API / jsDelivr 获取，本地有缓存兜底

## 目录结构

```
.
├── README.md
├── work
│   ├── cache/              # 历史数据本地缓存（自动生成，已忽略）
│   └── generate_morning.py # 主脚本
└── outputs/                # 生成结果（自动生成，已忽略）
```
