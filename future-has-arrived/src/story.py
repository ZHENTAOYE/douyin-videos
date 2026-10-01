"""《未来已到达》v2 — text-only science short. Master storyboard.

All times are absolute seconds in the final cut.
Card styles:
  q      : centred statement (large)
  body   : lower-left statement, one or two lines
  stat   : big number (`num`) + small caption above/below (`pre`, `cap`)
  title  : the title card
  chapter: small chapter marker, top-left
Every fact used on screen is listed with its source in docs/fact-check.md.
"""

SCENES = [
    # id         start   end
    ('chip',       0.0,  14.6),
    ('title',     14.6,  19.0),
    ('moore',     19.0,  38.0),
    ('euv',       38.0,  62.0),
    ('earth',     62.0,  96.0),
    ('voyager',   96.0, 106.0),
    ('deepfield', 106.0, 116.5),
    ('moon',     116.5, 123.0),
    ('lhc',      123.0, 136.0),
    ('fusion',   136.0, 145.0),
    ('precision', 145.0, 155.0),
    ('dna',      155.0, 164.0),
    ('protein',  164.0, 171.0),
    ('ai',       171.0, 180.0),
    ('accel',    180.0, 204.0),
    ('finale',   204.0, 219.0),
]

CARDS = [
    # ---------------------------------------------------------------- hook
    dict(t0=1.0, t1=4.3, style='q', text='这是一座城市吗？'),
    dict(t0=4.7, t1=6.2, style='q', text='不是。'),
    dict(t0=6.6, t1=9.6, style='q', text='这是一块手机芯片的内部。'),
    dict(t0=9.9, t1=14.3, style='stat', pre='指甲盖大小的地方', num='上百亿', cap='个晶体管'),
    # ---------------------------------------------------------------- title
    dict(t0=14.6, t1=19.0, style='title', text='未来已到达', sub='人类的科技，究竟走到了哪一步？'),
    # ---------------------------------------------------------------- 01 speed
    dict(t0=19.4, t1=26.0, style='chapter', text='01', label='速度'),
    dict(t0=19.8, t1=24.0, style='body', text='1971 年，第一块商用微处理器\n只有 2,300 个晶体管'),
    dict(t0=27.6, t1=31.0, style='stat', x=600, pre='2024 年，一块 AI 芯片', num='2,080 亿', cap='个晶体管', src='数据：Intel / NVIDIA'),
    dict(t0=31.2, t1=34.0, style='stat', x=600, pre='53 年', num='× 9000 万', cap='增长约九千万倍'),
    dict(t0=34.4, t1=37.8, style='body', text='最细的结构\n只有几十个原子宽'),
    # ---------------------------------------------------------------- 02 make
    dict(t0=38.4, t1=46.0, style='chapter', text='02', label='制造'),
    dict(t0=38.8, t1=43.6, style='body', text='雕刻它们，需要一种在地表几乎不存在的光\n—— 波长 13.5 纳米的极紫外光'),
    dict(t0=44.0, t1=48.6, style='body', text='每秒 5 万次\n激光精准击中一颗下落的锡滴'),
    dict(t0=49.2, t1=53.6, style='stat', pre='锡滴瞬间化为等离子体', num='约 22 万 ℃', cap='约是太阳表面温度的 40 倍', src='数据：ASML'),
    dict(t0=54.4, t1=61.4, style='body', text='收集这束光的反射镜，若放大到德国那么大\n最高的起伏也只有 0.1 毫米', src='数据：ZEISS'),
    # ---------------------------------------------------------------- 03 connect
    dict(t0=62.6, t1=70.0, style='chapter', text='03', label='连接'),
    dict(t0=64.4, t1=69.0, style='body', text='跨越大洋的数据\n超过 99% 走的是海底光缆'),
    dict(t0=69.4, t1=73.6, style='stat', pre='全球海底光缆总长', num='140 万公里', cap='能绕地球 35 圈', src='数据：TeleGeography · 线路为示意'),
    dict(t0=75.0, t1=79.6, style='stat', pre='此刻，地球上空', num='10,000+', cap='颗卫星正在运行'),
    dict(t0=80.4, t1=85.6, style='body', text='导航卫星上的时钟\n每天比地面快 38 微秒'),
    dict(t0=86.0, t1=91.0, style='body', text='不修正爱因斯坦的相对论\n定位每天会偏离约 10 公里'),
    dict(t0=91.4, t1=95.6, style='q', text='你的每一次导航，都用到了相对论。'),
    # ---------------------------------------------------------------- 04 cosmos
    dict(t0=96.4, t1=104.0, style='chapter', text='04', label='宇宙'),
    dict(t0=96.8, t1=101.0, style='stat', x=1390, pre='1977 年出发的旅行者 1 号，此刻在', num='250 亿公里', cap='之外，仍在与地球通信'),
    dict(t0=101.3, t1=105.7, style='body', text='它的信号\n要飞将近一整天，才能回到地球'),
    dict(t0=106.6, t1=111.0, style='body', text='韦布望远镜，看到了\n宇宙诞生后约 3 亿年的星系'),
    dict(t0=111.4, t1=116.2, style='stat', x=560, pre='这束光在路上，走了', num='135 亿年', cap=''),
    dict(t0=117.2, t1=122.6, style='body', text='2024 年，嫦娥六号\n带回人类首份月球背面样品'),
    # ---------------------------------------------------------------- 05 extremes
    dict(t0=123.4, t1=131.0, style='chapter', text='05', label='极限'),
    dict(t0=123.8, t1=127.6, style='body', text='大型强子对撞机\n周长 27 公里'),
    dict(t0=128.0, t1=131.6, style='stat', pre='超导磁体温度', num='−271.3 ℃', cap='比宇宙深空还冷'),
    dict(t0=132.0, t1=135.8, style='stat', pre='质子被加速到光速的', num='99.9999991%', cap=''),
    dict(t0=136.4, t1=140.4, style='body', text='中国“人造太阳”EAST\n曾让 1.2 亿℃ 的等离子体运行 101 秒'),
    dict(t0=140.6, t1=144.8, style='stat', pre='2025 年，稳态高约束运行', num='1066 秒', cap='', src='数据：中国科学院等离子体物理研究所'),
    dict(t0=145.4, t1=150.0, style='body', text='最精确的原子钟\n从宇宙诞生走到今天，误差不到 1 秒'),
    dict(t0=150.3, t1=154.8, style='body', text='引力波探测器\n能察觉质子直径万分之一的长度变化'),
    # ---------------------------------------------------------------- 06 life & intelligence
    dict(t0=155.4, t1=163.0, style='chapter', text='06', label='生命与智能'),
    dict(t0=155.8, t1=160.0, style='body', text='第一个人类基因组\n花了 13 年，约 27 亿美元'),
    dict(t0=160.3, t1=163.8, style='stat', pre='今天，测一个人的基因组', num='几百美元', cap=''),
    dict(t0=164.4, t1=170.8, style='body', text='AlphaFold 预测了 2 亿多种蛋白质结构\n几乎覆盖所有已知蛋白质', src='2024 年诺贝尔化学奖'),
    dict(t0=171.4, t1=174.4, style='q', text='而机器，学会了人类的语言。'),
    # (the chat exchange in the 'ai' scene is drawn by the scene itself)
    # ---------------------------------------------------------------- 07 acceleration
    dict(t0=180.4, t1=186.0, style='chapter', text='07', label='加速'),
    dict(t0=180.8, t1=184.2, style='body', text='1903 年，人类第一次飞上天空\n只飞了 12 秒'),
    dict(t0=184.5, t1=187.8, style='body', text='66 年后\n人类站上了月球'),
    # (year montage 188 → 203 is drawn by the scene)
    # ---------------------------------------------------------------- finale
    dict(t0=205.0, t1=208.6, style='q', text='我们总以为，未来还很远。'),
    dict(t0=209.0, t1=212.4, style='q', text='其实，它已经到了。'),
    dict(t0=212.8, t1=219.0, style='title', text='未来已到达', sub='而你，正身处其中'),
]

# Milestones for the acceleration montage (all verified, see docs/fact-check.md)
MILESTONES = [
    (1903, '人类首次动力飞行'),
    (1957, '第一颗人造卫星'),
    (1961, '人类首次进入太空'),
    (1969, '人类登上月球'),
    (1970, '东方红一号上天'),
    (1971, '第一块商用微处理器'),
    (1973, '第一通手机电话'),
    (1983, '互联网协议 TCP/IP 启用'),
    (1991, '万维网向公众开放'),
    (1994, '中国接入国际互联网'),
    (1996, '克隆羊多莉诞生'),
    (2003, '人类基因组计划完成'),
    (2003, '神舟五号载人飞天'),
    (2007, '智能手机时代开启'),
    (2008, '京津城际高铁开通'),
    (2012, '深度学习突破'),
    (2015, '首次探测到引力波'),
    (2016, 'AI 战胜围棋世界冠军'),
    (2019, '首张黑洞照片'),
    (2019, '嫦娥四号着陆月球背面'),
    (2020, '北斗全球组网完成'),
    (2021, '祝融号登陆火星'),
    (2022, '激光核聚变首次实现能量增益'),
    (2022, '对话式 AI 走进大众'),
    (2023, '首个基因编辑疗法获批'),
    (2024, '嫦娥六号月背采样返回'),
    (2025, 'EAST 1066 秒稳态运行'),
    (2025, '人形机器人跑完半程马拉松'),
    (2026, '此刻'),
]

# Sound-design hit points (seconds): name -> list of times. The score is written to these.
HITS = {
    'sub_drop': [4.7, 14.6, 27.6, 49.2, 75.0, 111.4, 128.0, 140.6, 205.0],
    'riser_end': [6.6, 14.6, 49.2, 62.0, 123.0, 188.0],
    'big_hit': [14.6, 212.8],
}


def scene_at(t):
    for sid, a, b in SCENES:
        if a <= t < b:
            return sid, a, b
    return SCENES[-1]


TOTAL = SCENES[-1][2]
