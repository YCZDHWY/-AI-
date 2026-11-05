"""Build the project description DOCX (Chinese, CJK-safe styles)."""
import os
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "大创项目说明", "智能植物养护系统项目说明.docx")
BODY_FONT = "宋体"
HEAD_FONT = "黑体"


def set_run(run, name, size=None, bold=False, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)
    if size is not None:
        run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color or RGBColor(0, 0, 0)


def add_para(doc, text, style=None, size=10.5, bold=False, font=BODY_FONT,
             align=None, before=0, after=6, line=1.5, indent=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if indent is not None:
        pf.first_line_indent = Pt(indent)
    run = p.add_run(text)
    set_run(run, font, size, bold)
    return p


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_borders(table, color="D9D9D9", size=6):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def cell_text(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.25
    run = p.add_run(text)
    set_run(run, BODY_FONT, 10, bold)


def set_fixed_layout(table, widths_cm):
    """Use a fixed table grid so the intended column widths actually apply."""
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for col, cm in zip(grid.findall(qn("w:gridCol")), widths_cm):
            col.set(qn("w:w"), str(int(Cm(cm).twips)))


def prevent_row_split(table):
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        tr_pr.append(cant)


def add_table(doc, header, rows, widths_cm, header_fill="DCE6F1"):
    table = doc.add_table(rows=1, cols=len(header))
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    table.autofit = False
    set_borders(table)
    for i, name in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.width = Cm(widths_cm[i])
        cell_text(cell, name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        shade_cell(cell, header_fill)
    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].width = Cm(widths_cm[i])
            align = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            cell_text(cells[i], val, align=align)
            if r_idx % 2 == 1:
                shade_cell(cells[i], "F5F8FC")
    set_fixed_layout(table, widths_cm)
    prevent_row_split(table)
    return table


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = Cm(2.8)
    sec.right_margin = Cm(2.8)
    sec.top_margin = Cm(2.6)
    sec.bottom_margin = Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    normal.font.size = Pt(10.5)

    # Title block
    add_para(doc, "智能植物养护系统项目说明", size=18, bold=True, font=HEAD_FONT,
             align=WD_ALIGN_PARAGRAPH.CENTER, after=4, line=1.4)
    add_para(doc, "大学生创新创业训练计划项目 · 项目方向与实施方案（送指导老师审阅）",
             size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=16, line=1.4)

    def h1(text):
        add_para(doc, text, size=13, bold=True, font=HEAD_FONT, before=12, after=6, line=1.4)

    def h2(text):
        add_para(doc, text, size=11, bold=True, font=HEAD_FONT, before=8, after=4, line=1.4)

    def body(text):
        add_para(doc, text, size=10.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                 after=6, line=1.5, indent=21)

    h1("一、项目背景与要解决的问题")
    body("养植物是很多人日常生活的一部分，但真正能把植物养好并不容易。浇水靠感觉，土是干是湿看不出；"
         "光照够不够、温度湿度合不合适，普通人没有判断依据；一旦出差、回家或忙起来忘记照顾，植物就容易"
         "出问题。更常见的情况是浇水浇过头把根泡坏，或者长期缺水等到发现时叶子已经发黄。植物出现黄叶、"
         "叶斑等异常时，普通人也很难判断是缺水、光照不足还是病虫害，往往等发现时已经错过处理时机。")
    body("市面上已经有一些智能浇水装置，但它们大多停留在“按固定时间定量浇水”的层面：不感知真实环境，"
         "不认识植物，也不理解植物当前的状态，本质上只是一个定时开关。本项目想做的是一个真正“懂植物”"
         "的养护助手：用传感器感知真实环境，用图像识别植物的外观状态，再用 AI 把两者结合起来给出个性化的"
         "养护建议，让“凭感觉养”变成“看数据养”。")

    h1("二、项目目标")
    body("围绕“感知环境—理解状态—给出建议—远程可控”这一条主线，搭建一套软硬件结合的智能植物养护系统。"
         "项目完成后应达到：硬件端能稳定采集土壤湿度、空气温湿度、光照强度和水位数据，并驱动水泵按需浇水；"
         "软件端提供微信小程序，实现数据实时查看、远程手动/自动浇水、养护提醒和历史数据曲线；"
         "AI 端能结合传感器数据与植物种类给出通俗的养护建议，并通过拍照识别叶片异常。"
         "在宿舍或家中真实环境中连续运行稳定，能通过实际使用验证效果。")

    h1("三、技术方案")
    body("系统采用“端—网—云—用”四层架构：硬件端负责感知与执行，网络层负责数据传输，云端负责存储与"
         "智能决策，应用层负责用户交互。数据流为：传感器采集环境数据，经主控通过 Wi-Fi 上传到云端；"
         "云端结合规则与 AI 生成养护建议；小程序展示数据并接收用户指令，反向控制硬件执行浇水。")
    h2("1. 硬件端：感知与执行（硬件方向两位同学）")
    body("以 ESP32 为主控，搭配土壤湿度传感器、DHT11 空气温湿度传感器、BH1750 光照传感器和水位传感器，"
         "采集植物生长环境数据；执行端采用继电器控制小型水泵，实现按需自动浇水或远程手动浇水。"
         "数据通过 Wi-Fi 以 MQTT 协议上报云端，同时接收云端下发的控制指令。主控固件优先采用 MicroPython "
         "开发，复用团队已有的 Python 基础并降低上手门槛，重点放在通信稳定性与传感器标定上。")
    h2("2. 网络与云端：数据通道（软件方向一位同学）")
    body("搭建轻量级后端服务，负责接收硬件上报的数据、写入数据库、按阈值规则判断是否需要提醒或自动浇水，"
         "并作为 AI 能力的调用入口。后端同时承担小程序的接口服务，把实时数据、历史曲线和养护建议下发给前端。")
    h2("3. 应用与 AI：用户交互与智能决策（软件方向一位同学）")
    body("基于微信小程序提供用户界面，包含实时数据看板、远程控制、养护提醒推送、历史数据曲线和植物档案。"
         "AI 部分分两层：一是规则层，用阈值判断土壤过干、光照不足等基础状况；二是模型层，调用多模态大模型，"
         "把环境数据与植物种类作为上下文生成通俗的养护建议，并对用户上传的植物照片进行叶片异常识别。")

    h1("四、与现有产品的差异")
    body("下表把本项目与市面上常见的定时浇水装置进行对比，重点体现“从定时执行到智能决策”的升级。")
    add_table(
        doc,
        ["对比维度", "市面常见定时浇水装置", "本项目"],
        [
            ["环境感知", "无，或仅单一湿度", "湿度、温湿度、光照、水位多维采集"],
            ["决策方式", "固定时间定量浇水", "结合实时环境与植物状态，AI 辅助决策"],
            ["状态识别", "无", "拍照识别黄叶、叶斑等异常"],
            ["养护建议", "无", "结合植物种类的个性化建议与提醒"],
            ["远程交互", "无或功能有限", "小程序远程查看、控制与历史曲线"],
            ["可扩展性", "功能固定", "预留无障碍等扩展模块"],
        ],
        [3.0, 6.0, 6.0],
    )

    h1("五、创新点")
    body("第一，从“按时间浇水”升级为“按植物状态养护”。系统不再依赖固定定时，而是把环境感知和植物状态"
         "作为决策依据，这是与现有产品最本质的区别。")
    body("第二，软硬件深度结合形成完整闭环。从传感器采集到云端决策再到小程序交互，整条链路可完整演示，"
         "便于展示和验证真实效果。")
    body("第三，模块化设计预留无障碍扩展。项目第二阶段计划把识别与语音播报能力单独封装为无障碍模式，"
         "让视障人士和老人也能“听懂”植物状态，使一次开发同时覆盖智慧生活与助老助残两类场景。")

    h1("六、团队分工")
    body("团队四人，以软件方向为主、硬件由项目负责人牵头并兼任，同时指定一位软件方向同学作为硬件备份，"
         "避免硬件开发形成单点依赖。软硬并行推进，接口协议在开发初期先行约定，降低后期联调成本。")
    add_table(
        doc,
        ["角色", "方向", "主要职责"],
        [
            ["负责人", "软件 + 硬件", "主控固件开发（MicroPython）、传感器选型与接线、数据上云；并负责 AI 模型调用与接口"],
            ["成员 B", "软件", "后端服务、数据库、阈值规则与提醒逻辑"],
            ["成员 C", "软件", "微信小程序前端、数据可视化、历史曲线"],
            ["成员 D", "软件（硬件备份）", "小程序辅助功能；跟随负责人学习硬件，能在主负责人忙碌时接手基础硬件任务"],
            ["全体", "共同", "申报书撰写、中期与结题材料、成果答辩"],
        ],
        [2.0, 2.0, 11.0],
    )

    h1("七、实施计划")
    add_table(
        doc,
        ["阶段", "时间", "主要工作", "阶段成果"],
        [
            ["第一阶段", "第 1 个月", "选题调研、需求确认、硬件选型与预算、完成立项申报",
             "立项材料、硬件清单"],
            ["第二阶段", "第 2–3 个月", "硬件负责人跑通传感采集与执行最小闭环；软件组完成小程序框架与模型接口",
             "端到端最小可运行原型"],
            ["第三阶段", "第 4 个月", "软硬件联调，打通数据链路，完善自动浇水与远程控制",
             "系统完整运行"],
            ["第四阶段", "第 5 个月", "AI 建议与异常识别功能打磨，真实环境连续试用并收集反馈",
             "试用反馈与优化记录"],
            ["第五阶段", "第 6 个月", "整理材料、申请软件著作权、准备中期与结题、参赛",
             "软著申请、结题材料、参赛作品"],
        ],
        [2.0, 2.4, 7.8, 3.0],
    )

    h1("八、预期成果")
    body("1. 硬件原型一套，能在真实环境连续稳定运行，完成数据采集与按需浇水。")
    body("2. 微信小程序一款，实现数据看板、远程控制、提醒推送与历史曲线，具备真实可用性。")
    body("3. 申请软件著作权一项，整理项目演示视频与技术文档，形成可对外展示的完整成果。")
    body("4. 完成校级大创立项，并以本项目为基础冲击省级立项及“挑战杯”“互联网+”等赛事。")
    body("5. 规划第二阶段无障碍扩展模块：将识别与语音播报能力封装为独立功能，服务视障人士与老年用户，"
         "作为后续持续开发方向。")

    h1("九、可能的风险与应对")
    body("硬件单点依赖方面，硬件由负责人兼任、团队无专职硬件同学，因此指定一位软件方向同学作为硬件备份并"
         "提前熟悉接线与固件流程，同时优先使用 MicroPython 与成熟传感器模块，先跑通最小系统再逐步扩展，"
         "把入门难度和开发风险控制在可控范围内。软硬件联调方面，接口协议与数据格式在开发初期先行约定，"
         "避免后期反复返工。AI 调用方面，对外部大模型接口设置超时与降级策略，接口异常时回落到本地阈值规则，"
         "保证核心功能不受影响。负责人需在时间上为硬件留出固定投入，避免因软件任务繁忙导致硬件停滞。")

    h1("十、请指导老师给予指导")
    body("恳请老师在项目方向、技术方案与技术边界上给予指导：一是选题的现实意义与创新点是否站得住；"
         "二是当前方案的技术深度是否适合大创，硬件学习投入是否可控；三是团队配置与分工是否合理。"
         "我们会根据老师的意见进一步调整和完善实施方案。")

    h1("附：联系指导老师的沟通要点")
    body("老师您好，我是【学院/专业/班级】的【姓名】。我们想做的大创方向是“软硬件结合的智能植物养护系统”。"
         "市面上的自动浇水装置大多只是按固定时间定量浇水，并不了解植物的真实状态。我们想做的是用传感器感知"
         "温湿度、光照和土壤湿度，用图像识别叶片是否异常，再用 AI 把这些信息结合起来，给出个性化的养护建议，"
         "并配套一个小程序实现远程查看和控制。团队四人，以软件方向为主，硬件部分由我牵头并兼任，用 "
         "MicroPython 开发主控、复用团队已有的 Python 基础，同时安排一位同学作为硬件备份，避免单点依赖。"
         "硬件选型已初步确定。想请教您："
         "这个方向作为大创选题是否合适，以及您是否方便指导我们？附上一份详细的项目说明，期待您的回复。")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
