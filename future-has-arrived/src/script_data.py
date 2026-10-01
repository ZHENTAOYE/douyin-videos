"""《未来已到达》 — narration script and timing structure.

Every line has:
  id    : stable id used by the renderer / mixer
  say   : text fed to TTS (numbers spelled out so the reading is unambiguous)
  sub   : text shown on screen
  pause : seconds of silence after the line ends
Each scene has a lead-in (seconds before its first line) and a tail
(seconds after its last line, before the next scene starts).
"""

SCENES = [
    dict(id='prophecy', lead=1.7, tail=0.0, lines=[
        dict(id='L01', say='很久以后，每个人的口袋里，都会有一块发光的玻璃。', sub='很久以后，每个人的口袋里，都会有一块发光的玻璃。', pause=1.0),
        dict(id='L02', say='隔着半个地球，你能看见另一个人的脸。', sub='隔着半个地球，你能看见另一个人的脸。', pause=0.9),
        dict(id='L04', say='迷了路，它会为你指路。', sub='迷了路，它会为你指路。', pause=1.1),
        dict(id='L05', say='你对它说话——', sub='你对它说话——', pause=0.7),
        dict(id='L06', say='它会回答你。', sub='它会回答你。', pause=2.6),   # hold, then the lamp goes out
    ]),
    dict(id='reveal', lead=0.0, tail=1.4, lines=[
        dict(id='L07', say='这不是预言。', sub='这不是预言。', pause=1.1),
        dict(id='L08', say='这是你，今天早上。', sub='这是你，今天早上。', pause=0.0),
    ]),
    dict(id='title1', lead=5.0, tail=0.0, lines=[]),
    dict(id='night', lead=2.8, tail=1.2, lines=[
        dict(id='L09', say='人类在地球上，已经生活了大约三十万年。', sub='人类在地球上，已经生活了大约三十万年。', pause=1.0),
        dict(id='L10', say='这三十万年里，几乎每一个夜晚，都是这样的。', sub='这三十万年里，几乎每一个夜晚，都是这样的。', pause=2.2),
        dict(id='L11', say='最快的速度，是一匹马。', sub='最快的速度，是一匹马。', pause=0.8),
        dict(id='L12', say='最远的声音，是一声呼喊。', sub='最远的声音，是一声呼喊。', pause=0.8),
        dict(id='L13', say='一封信，要在路上走好几个月。', sub='一封信，要在路上走好几个月。', pause=1.1),
        dict(id='L14', say='一个人出生时的世界，和他离开时，几乎一模一样。', sub='一个人出生时的世界，和他离开时，几乎一模一样。', pause=0.0),
    ]),
    dict(id='dots', lead=1.0, tail=2.2, lines=[
        dict(id='L15', say='如果把每一代人，画成一个点——', sub='如果把每一代人，画成一个点——', pause=0.7),
        dict(id='L16', say='三十万年，是一万两千个点。', sub='三十万年，是一万两千个点。', pause=2.8),
        dict(id='L17', say='只有最后五个点，见过电灯。', sub='只有最后五个点，见过电灯。', pause=1.6),
        dict(id='L18', say='而最后一个点——', sub='而最后一个点——', pause=0.9),
        dict(id='L19', say='是我们。', sub='是我们。', pause=0.0),
    ]),
    dict(id='accel', lead=1.2, tail=11.5, lines=[
        dict(id='L20', say='一九零三年，人类第一次飞上天空。那一次，只飞了十二秒。', sub='1903年，人类第一次飞上天空。那一次，只飞了12秒。', pause=1.0),
        dict(id='L21', say='六十六年后，人类站上了月球。', sub='66年后，人类站上了月球。', pause=1.6),
        dict(id='L22', say='把人送上月球的那台计算机，内存只有大约四千字节。', sub='把人送上月球的那台计算机，内存只有大约 4KB。', pause=0.9),
        dict(id='L23', say='今天，一部普通手机的内存，是它的一百万倍。', sub='今天，一部普通手机的内存，是它的一百万倍。', pause=1.6),
        dict(id='L24', say='然后，一切开始加速。', sub='然后，一切开始加速。', pause=0.0),
    ]),
    dict(id='earth', lead=1.6, tail=3.4, lines=[
        dict(id='L25', say='一百五十年前，如果能从太空俯瞰地球的夜晚，', sub='一百五十年前，如果能从太空俯瞰地球的夜晚，', pause=0.35),
        dict(id='L26', say='你会看到，一片漆黑。', sub='你会看到，一片漆黑。', pause=13.0),   # the planet lights up
        dict(id='L27', say='而今天——', sub='而今天——', pause=3.2),
        dict(id='L28', say='这每一点光，都是人类亲手点亮的。', sub='这每一点光，都是人类亲手点亮的。', pause=0.0),
    ]),
    dict(id='quiet', lead=1.0, tail=2.0, lines=[
        dict(id='L29', say='小时候，我们总在等未来。', sub='小时候，我们总在等未来。', pause=0.8),
        dict(id='L30', say='等会说话的机器，等一个装得下整个世界的口袋。', sub='等会说话的机器，等一个装得下整个世界的口袋。', pause=0.9),
        dict(id='L31', say='我们以为，它会在某一天，敲锣打鼓地到来。', sub='我们以为，它会在某一天，敲锣打鼓地到来。', pause=0.9),
        dict(id='L32', say='但它没有。', sub='但它没有。', pause=1.3),
        dict(id='L33', say='它是一件一件，悄悄来的。', sub='它是一件一件，悄悄来的。', pause=1.0),
        dict(id='L34', say='每一件出现的时候，都是奇迹。', sub='每一件出现的时候，都是奇迹。', pause=0.6),
        dict(id='L35', say='然后不到一个星期，就成了平常。', sub='然后不到一个星期，就成了平常。', pause=1.5),
        dict(id='L36', say='你在时速三百五十公里的列车上，睡着了。', sub='你在时速 350 公里的列车上，睡着了。', pause=1.8),
        dict(id='L38', say='奶奶在一千公里外，隔着屏幕，看你吃饭。', sub='奶奶在一千公里外，隔着屏幕，看你吃饭。', pause=2.0),
        dict(id='L39', say='你问一台机器问题，它像人一样，回答了你。', sub='你问一台机器问题，它像人一样，回答了你。', pause=2.2),
        dict(id='L40', say='而我们，早已不再惊讶。', sub='而我们，早已不再惊讶。', pause=0.0),
    ]),
    dict(id='look', lead=1.4, tail=2.6, lines=[
        dict(id='L41', say='如果你还在等未来——', sub='如果你还在等未来——', pause=0.9),
        dict(id='L42', say='不用抬头。', sub='不用抬头。', pause=1.1),
        dict(id='L43', say='低头看看，你手里的东西。', sub='低头看看，你手里的东西。', pause=3.0),
        dict(id='L44', say='神话里的千里眼、顺风耳，', sub='神话里的千里眼、顺风耳，', pause=0.5),
        dict(id='L45', say='此刻，就握在你的手里。', sub='此刻，就握在你的手里。', pause=0.0),
    ]),
    dict(id='coda', lead=0.8, tail=2.0, lines=[
        dict(id='L46', say='很久以后，会有人回头看我们，', sub='很久以后，会有人回头看我们，', pause=0.4),
        dict(id='L47', say='就像我们，回头看那一盏油灯。', sub='就像我们，回头看那一盏油灯。', pause=1.6),
        dict(id='L48', say='在他们眼里，我们才是古人。', sub='在他们眼里，我们才是古人。', pause=1.6),
        dict(id='L49', say='而在祖先的梦里——', sub='而在祖先的梦里——', pause=0.9),
        dict(id='L50', say='我们，就是未来。', sub='我们，就是未来。', pause=0.0),
    ]),
    dict(id='title2', lead=7.0, tail=0.0, lines=[]),
]

ALL_LINES = [ln for sc in SCENES for ln in sc['lines']]
