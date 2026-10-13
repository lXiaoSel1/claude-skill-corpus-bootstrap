# corpus-bootstrap

[English](README.md) | 简体中文

一个 [Claude Code](https://claude.com/claude-code) skill。它用你为某个研究领域收集的论文，给这个领域生成两个写作 skill：

- **`<field>-lit`**：审查你写的一段文字，报告它读起来像不像本领域的文献。它会对照你的语料检查术语，套用文风规则，并检查句与句之间的衔接。改完的文字还给你，论点、引用和数字一律不动。
- **`<field>-draft`**：一次起草一段。每一段都沿用语料里至少两篇论文用过的结构（叫作一个 “Version”）。每个论断在写成句子之前，必须先在台账里登记一行，贴上出处原文。它还能给写好的章节做反向提纲（`--outline`），也能把引言或摘要里的论断追溯到支撑它的表格（`--trace`）。

所有数字都不从别的领域照搬：术语频次、段落长度、衔接常模、章节分类、引述他人结论时用的动词阶梯，全部在你自己的语料上重新测量。

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
