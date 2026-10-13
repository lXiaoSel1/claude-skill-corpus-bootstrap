# corpus-bootstrap

[English](README.md) | 简体中文

**让你的论文读起来像本领域的文献。**

一个 [Claude Code](https://claude.com/claude-code) skill。它从你为某个研究领域收集的论文里，学会这个领域是怎么写文章的，再据此生成两个写作助手：

- **`<field>-lit`**：审查你写的一段文字，报告它读起来像不像本领域的文献。它会对照你的语料检查术语，套用文风规则，并检查句与句之间的衔接。改完的文字还给你，论点、引用和数字一律不动。
- **`<field>-draft`**：一次起草一段。每一段都沿用语料里至少两篇论文用过的结构（叫作一个 “Version”）。每个论断在写成句子之前，必须先在台账里登记一行，贴上出处原文。它还能给写好的章节做反向提纲（`--outline`），也能把引言或摘要里的论断追溯到支撑它的表格（`--trace`）。

所有数字都不从别的领域照搬：术语频次、段落长度、衔接常模、章节分类、引述他人结论时用的动词阶梯，全部在你自己的语料上重新测量。

## 为什么做这个项目

我们大多数人学一个领域的写法，靠的是慢功夫：读几百篇论文，慢慢知道大家用哪些术语、一段话通常怎么开头、转述别人的结论该用哪个动词。语法检查工具和通用的 AI 助手给不了这些。它们写出的句子通顺，但泛泛而谈；会用本领域没人用的说法，读起来有 AI 腔；还可能把一篇论文转述的别人的结论，说成这篇论文自己的发现。

这个项目想帮大家把论文写得更好，办法是把你所在领域的论文当作标准。论文由你收集，skill 测量这些论文是怎么写的，再拿它们来检查你的文字。每条建议都附上证据：你的语料里有几篇论文这样写，原句是哪一句。你能看到每处修改的理由，改不改由你决定。

## 适合谁

- **研究生和青年学者**：直接从论文本身学会本领域的写法，看到的是计数和例句，而不是笼统的经验之谈。
- **英文非母语的作者**：语法可能没问题，但用词和句式还是会露出痕迹。每条建议都列出用这种说法的论文，你学到的是地道的表达，而不只是接受一处改动。
- **跨领域的研究者**：用新领域的论文建好参照，这个领域的术语和段落惯例就一目了然，不必花几年慢慢体会。
- **用 AI 辅助写作的人**：AI 写的文字往往通顺但空泛，还可能出现原文里没有的术语或归因。`-lit` 会标出本领域不用的说法；`-draft` 写出的每个论断都在台账里有出处原句，找不到出处的会标出来提醒你核对。

## 它能帮你做什么

**`<field>-lit`：每条意见都附证据的审稿人**

- 逐个对照语料检查术语，报告有几篇论文用过，并引出其中一句原文。
- 把含糊的名词换成本领域用的准确术语。
- 只有当你的语料也很少这样写时，才把一个说法判为 “AI 腔”；在你的语料里有 3 篇以上论文用过的说法，就算本领域的正常写法。
- 给每一句和上一句之间的衔接打分。
- 每处修改都写明理由，拿不准的问题列在 “留给作者” 里。
- 不改你的论点、引用和数字。

**`<field>-draft`：没有出处就不动笔的起草人**

- 先选一个段落结构，要求你的语料里至少有两篇论文用它做同样的事。
- 动笔前先建论断台账：每个论断一行，写明引述动词，并贴上论文原句；找不到出处的标 `!!`。
- 引述他人结论的动词不能比原文支持的更强，用的是在你的语料上测出的 “动词阶梯”，例如报告结果用 “find that”，原文支持较弱时退到 “note that”。
- 能给写好的章节做反向提纲，也能把引言或摘要里的论断追溯到支撑它的表格。

## 真实例子：一份文献综述

下面的片段来自一份关于工伤保险与医疗账单的文献综述草稿，对照的是这个领域 66 篇论文组成的语料（其中 51 篇用于文风判断）。片段只摘几行，语料里的论文编号换成了作者和年份。

计数的读法：`w:62` 表示总共出现 62 次；`range:10/66` 表示 66 篇论文里有 10 篇用过。

### 例 1：对照语料检查术语（`-lit`）

草稿里的三个说法：

> …medical costs paid through workers' compensation are higher than those paid through **general health insurance**…
>
> …fractures, lacerations, and other **clear-cut traumas** showed no such effect.
>
> …after the 2006 increase in the **weekly benefit ceiling**, affected workers' benefit duration increased by 11.1%…

`-lit` 改了什么、为什么改（摘录）：

```
CHANGED (3)

  1. "general health insurance" → "health insurance"
     R7/§3 — vague modifier; "health insurance" is the corpus standard (range:29/66);
     "general health insurance" appears in only 1 paper

  2. "clear-cut traumas" → "traumatic injuries"
     §3 — "clear-cut traumas" w:0 range:0/66; "traumatic injuries" w:62 range:10/66;
     Fomenko & Gruber (the paper being described) uses "traumatic injuries" 22 times

  3. "weekly benefit ceiling" → "maximum weekly benefit"
     §3 — "weekly benefit ceiling" w:0 range:0/66; "maximum weekly benefit" w:18 range:2/66;
     Cabral & Dillender (the paper being described) uses "maximum weekly benefit" 9 times
```

三处替换里有两处，换上的正是被引论文自己用的词。熟悉那篇论文的读者，看到的就是他们预期的说法。

### 例 2：先建台账，再写句子（`-draft`）

写介绍 Graves et al. (2012) 的那一段时，`-draft` 选了 **Version 3（逐项介绍研究，单篇）**，动笔前先填好台账。其中三行：

| cite-key | verb | claim | source | flag |
|---|---|---|---|---|
| Graves2012 | find that | Followed 1,830 workers identified from July 2002 to April 2004 | "From July 2002 to April 2004, 4354 workers were identified" (p.5); "the final study sample consisted of 1830 workers." (p.5) | |
| Graves2012 | find that | Male workers were 43% more likely to receive an early MRI within 42 days of injury than female workers | "Multivariable regression showed that male workers were 43% more likely to receive an early MRI than female workers (IRR: 1.43, 95% CI: 1.12--1.82)" (p.6) | |
| Graves2012 | find that | In Model 2, male IRR dropped to 1.24 (95% CI 0.98--1.58), no longer significant | Table 2 in the published journal version (not available in the PDF used for the note) | !! |

它起草的其中一句：

```latex
Male workers were 43\% more likely than female workers to receive an MRI within 42 days of injury (IRR 1.43, 95\% CI 1.12--1.82); after excluding self-report variables that could have been affected by interview timing, the authors stated that the overall pattern of associations was similar to the main model, but the male-to-female ratio dropped to 1.24 (95\% CI 0.98--1.58) and was no longer statistically significant.
```

关键是标了 `!!` 的那一行。`-draft` 没找到 1.24 这个数字的出处原句，于是把它标出来等人核对，而不是当作已经确认。作者去查了，这个数字在论文第 16 页的表 2 里。

### 例 3：两个 skill，两种证据

有一段用 **“Regarding costs,”** 开头。`-lit` 判它合格，因为 51 篇论文里有 25 篇用过 “Regarding”。但 `-draft` 记录了语料里每一段是怎么开头的，结果不一样：语料的 2,702 个段落开头里，只有 2 个用 “Regarding”；那 25 篇论文都是在句中用它。于是这一段改成了用主语开头。

同一份综述里另外几处改写，每处都有语料计数作依据：

| 草稿的写法 | 语料里 | 改后的写法 |
|---|---|---|
| a longer time to return to work | 0/66 | delayed return to work（4/51） |
| mostly indicate | 0/51 | mostly suggest（"suggest"：33/51） |
| Industry composition can also alter aggregate results. | 0/51 | Aggregate results also depend on industry composition.（"depend on"：8/51） |
| Studies controlling for … find similar results. | 0/51 | Results from studies that control for injury type in regression models are consistent with these findings.（"results from"：20/51；"consistent with"：31/51） |

## 它会漏掉什么

这份综述也暴露了工具的不足，用之前值得了解：

- **`-lit` 查的是措辞，不是事实。** 上面那一段的另一份草稿没有建台账，把 1.24 写成了 “odds ratio”，而 Graves et al. 报告的是 incidence rate ratio。`-lit` 对那一节一处都没改，因为措辞本身没问题。这个错误是逐句对照原文核对时才查出来的。
- **第一轮审查可能偏松。** 第一轮里 13 节审查全部 “通过”，但全文仍有 12 处 “the authors argue”（51 篇论文里没有一篇这样写），句长中位数是 44 词，语料是 25 词。之后按更严的规则逐节重审：先扫描全文，拆开长句，再把每个术语和框架句重新查一遍。
- **“论文专用词，保留” 需要人来复核。** `-lit` 认为 “acute low back sprains” 是 Graves et al. 自己的说法，所以保留了；其实原文写的是 “back sprain/strain”，定稿改成了跟原文一致。
- **有些改动会删掉意思。** `-lit` 曾把 “fairly consistent” 改成 “consistent”，还删掉了 “the resulting”。这两个词都带着意思，两处改动后来都撤回了。

所以，数字和结论请对照原文核对；每个论断从哪里来，可以看 `-draft` 的台账；每处修改都要读过再接受。

## 设计原则

- **内容归你。** 工具不改你的论点、引用和数字。
- **语料是唯一依据。** 不凭经验立规矩，每个判断都引用你自己语料里的计数和原句。
- **没有证据就不写。** 起草出的每个论断都有出处原句，或者有一个看得见的标记。
- **论文由你提供。** 这个 skill 不抓取、不爬网页，也不调用任何 API。
- **主动权在你。** 每过一关都会停下来，章节分类要等你批准。

## 工作方式

搭建分五关进行。每一关结束都有验收：一个 `check_drift` 脚本，加上一项需要你亲自看的检查。每过一关，skill 都会停下来等你确认。

| 关 | 产出 | 成本 | 验收 |
|---|---|---|---|
| **0 语料** | 把 PDF 转成文本；来源清单（源文件哈希、转换器及版本，并标出扫描件、短文档和编码损坏）；四种口径的语料清单 | 脚本，几分钟 | 你审阅清单；lit 的 `check_drift` 第 0 关通过 |
| **1 文风层** | 文风测量、衔接常模、过渡语库。**从这一关起 `<field>-lit` 可以用了** | 只跑脚本 | lit 的 `check_drift` 第 1 关通过；你读一次实际审查结果 |
| **2 章节图** | 每篇论文的标题；从你的论文里归纳出的章节分类（**需要你批准**）；标注好的章节图；按章切片 | 1 轮归纳 + 约 4–8 轮标注 | 与人工核对的样本一致率 ≥ 90%；你读分类表和 3 个切片 |
| **3 阅读记录与 Version** | 逐段阅读记录；每章至少有 2 篇论文佐证的段落结构。**从这一关起 `<field>-draft` 可以用了** | 约 27 ×（论文数 / 60）轮阅读，加每章 1 轮，逐章进行 | draft 的 `check_drift` 第 3 关通过；你读一整章；起草出第一段 |
| **4 例句库** | 按 8 种修辞动作标注的例句库、动词阶梯、结构准则 | 每 10 篇约 1 轮 | 两个 `check_drift` 全部通过 |

阅读这几轮由 Claude Code 的子代理执行，提示词在 `templates/prompts/` 里。章节分类从你的论文里归纳，不预设。分类一旦错了，后面全部白做，所以第 2 关会停下来等你批准。

## 依赖

- Claude Code（阅读的几轮要用子代理）
- Python 3.8 或更高
- **PyMuPDF**（`pip install pymupdf`）。请当作必装：没有它（也没有 pypdf）时，页数会记成 0，扫描件也就检测不出来。
- Poppler 的 **`pdftotext`**，放在 PATH 上，或在 `field-config.yaml` 里写明路径
- 可选：PyYAML、pypdf

文档里用的是 Windows 的 `py -3`，macOS 和 Linux 请换成 `python3`。

## 安装

```bash
git clone https://github.com/lXiaoSel1/claude-skill-corpus-bootstrap ~/.claude/skills/corpus-bootstrap
```

文件夹必须叫 `corpus-bootstrap`。生成的两个 skill 默认放在它旁边，即同一个 `skills/` 目录下，也可以用 `--dest` 指定位置。放在项目自己的 `.claude/skills/` 里也可以。

## 快速开始

以下命令都在 skill 文件夹里运行，示例领域是 `ecology`。

```bash
cd ~/.claude/skills/corpus-bootstrap

# 1. 为这个领域生成两个 skill
py -3 scripts/stamp.py ecology --citation-style author-year --keywords "population ecology, habitat loss"

# 2. 转换 PDF：放进 ../ecology-lit/drop/，或者直接读你文献库里的原位置
py -3 scripts/ingest.py ../ecology-lit --src "/path/to/your/pdfs" --recursive

# 3. 生成语料清单，然后审阅
py -3 ../ecology-lit/scripts/build_corpus_meta.py

# 4. 查看已经建好哪几关，以及下一关的成本
py -3 scripts/tier_status.py ecology
```

然后在 Claude Code 里请它进行下一关，例如 `/corpus-bootstrap tier 1`。随时可以中断后接着做，`tier_status.py` 会读取进度台账。

`--citation-style` 可选 `author-year`、`numeric` 或 `mixed`。`--keywords` 会写进两个新 skill 的触发说明。

**论文由你自己下载。** 这个 skill 不抓取、不爬网页，也不调用任何 API。请不要把 PDF 和语料文本放进公开仓库。

## 第 4 关用到的写作指南

第 4 关的结构准则引用了几本已出版的写作指南，包括 McCloskey、Cochrane、Thomson、Gopen & Swan 等。这些文本有版权，**仓库里没有附带**。`references/canon-sources/_manifest.md` 列出了每一篇的出处；你能拿到哪篇，就把它存成 UTF-8 文本放进那个文件夹，文件名用 `<key>.txt`，第 4 关的检查会自动找到。

## 自检

```bash
py -3 tests/run_selftest.py
```

共 65 项检查，分两部分：

1. 对模板脚本的单元测试。
2. 在临时文件夹里的集成测试：先生成一个一次性的领域，再造一份故意埋了缺陷的测试语料（弯引号、跨行断开的短语、上标引用、纯图片的扫描件、只有一段的简报），然后跑第 0、1 关，每个缺陷都必须被抓出来。

自检需要 PyMuPDF 和 `pdftotext`，除临时文件夹外不写任何文件。

## 已知限制

- **第 4 关不完整。** 第 0–3 关不需要额外文件就能完整运行；第 4 关还需要一份 `structure-canon.md`（本仓库没有提供模板），以及你自己获取的写作指南。
- **只支持英文语料。** 分句、词表和各项测量都以英文为前提。
- **以 Windows 为主。** 文档和提示信息默认用 `py -3`，脚本本身跨平台。
- **稿件路径请写绝对路径。** `field-config.yaml` 里的 `manuscript_tex` 和 `manuscript_tables` 请用绝对路径，因为有两个脚本解析相对路径的方式不同。
- **可选模式需要仓库里没有的 agent。** `<field>-lit --audit` 会调用 `humanize-auditor`，`<field>-draft` 可以分出一个 `claim-verifier`。两者默认都关闭。
- **文件里的 “parent”。** 这套做法最早是为实证金融论文写作手工搭的一对 skill。那一对不在本仓库里，工厂运行也不依赖它们。文件里说的 “parent” 指的就是它们，它们的数字只作为示意出现。

## 仓库结构

```
SKILL.md                    Claude Code 加载的 skill
scripts/                    stamp、ingest、capture、tier_status
templates/lit/              <field>-lit 的骨架
templates/draft/            <field>-draft 的骨架
templates/field-config.yaml 两个 skill 共用的领域配置
templates/prompts/          各轮阅读的提示词及格式示例
references/                 搭建来历、一份存档的（未实现的）文献抓取调研、写作指南清单
tests/run_selftest.py       自检
```

## 许可证

MIT，见 [LICENSE](LICENSE)。版本 1.1.0（2026-10-07）。
