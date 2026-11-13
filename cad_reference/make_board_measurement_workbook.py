"""Blank, interactive measurement worksheet. No physical dimensions or CAD claims.

Uses ReportLab's standard CJK CID font for Chinese instructions. PDF form entries
use Helvetica and are intended for numeric/ASCII readings only; write Chinese
notes on a printed sheet or in BOARD_MEASUREMENT_WORKBOOK.md.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


UNITS = [
    ('APM32', 'APM32F103C8T6 / 向下焊', 'AST-MCU-APM32-001', 'USB 边朝下，器件面向上。',
     '重点：向下排针、USB 壳、跳帽、复位键和调试口。'),
    ('ESP32S3', 'ESP32-S3 N16R8 / 44 脚', 'AST-MCU-ESP32S3-001', 'USB 边朝下，天线在上。',
     '重点：含突出的天线和两个 USB 壳；57 mm 不是完整总长。'),
    ('RA02_U1', 'Ra-02 带蓝色底板 / 第 1 块', 'AST-RF-RA02-001 / U1', '模组字样朝上，IPEX 所在边朝下；拍照标定。',
     '重点：量底板而不是屏蔽盖；不为测量插拔 IPEX。'),
    ('RA02_U2', 'Ra-02 带蓝色底板 / 第 2 块', 'AST-RF-RA02-001 / U2', '模组字样朝上，IPEX 所在边朝下；拍照标定。',
     '第 2 块独立测量，不能复制第 1 块的尺寸。U1/U2 是临时采集标签。'),
    ('GY91', 'GY-91 / 紫板选项', 'AST-SENSOR-GY91-001', '接口排针一侧朝左，器件面向上。',
     '重点：安装孔和排针状态；标明轴向与气压传感器开口，不遮挡开口。'),
]


def create(output: Path) -> None:
    if output.exists():
        raise ValueError('Refusing to overwrite an existing workbook; choose a new output path.')
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=A4, invariant=1)
    c.setTitle('AI-rocket | 已购板卡最小测量工作表 | 尚未填写')
    c.setAuthor('AI-rocket project')
    w, h = A4
    navy = colors.HexColor('#17364B')
    blue = colors.HexColor('#E9F2F7')
    gray = colors.HexColor('#4F5C65')

    def text(x, y, s, size=10, color=navy):
        c.setFillColor(color)
        c.setFont('STSong-Light', size)
        c.drawString(x, y, s)

    def lines(y, strings, size=10, leading=18):
        for s in strings:
            text(42, y, s, size)
            y -= leading
        return y

    def header(title, page):
        c.setFillColor(navy)
        c.rect(0, h-100, w, 100, fill=1, stroke=0)
        text(42, h-40, 'AI-rocket / 板级 CAD 输入', 12, colors.white)
        text(42, h-72, title, 21, colors.white)
        text(42, 27, '未填写工作表，不是已测尺寸或装配图。所有线图均为示意，不按比例。', 9, gray)
        text(w-62, 27, f'{page} / 6', 9, gray)

    def section(y, title):
        c.setFillColor(blue)
        c.roundRect(36, y-8, w-72, 25, 4, fill=1, stroke=0)
        text(43, y, title, 12)

    def field(prefix, key, x, y, width, height=19):
        c.acroForm.textfield(name=f'{prefix}_{key}', tooltip=f'{prefix}: {key}',
            x=x, y=y, width=width, height=height, value='', fontName='Helvetica',
            fontSize=9, borderWidth=.6, borderColor=colors.HexColor('#A7B9C5'),
            fillColor=colors.white, textColor=colors.black, maxlen=180,
            forceBorder=True)

    header('先补最少数据，再建真实整板', 1)
    section(705, '当前确定与未确定')
    lines(675, [
        '采购证据已恢复，无需再次提供订单或重新证明持有。',
        '已锁定采购选项；还缺对应 PCB 版号、真实轮廓、排针和接口包络。',
        '同店公开检索尚未找到可绑定这些已购版本的整板工程图或 CAD。',
        '无需现在购买零件。优先测 APM32 和一块 Ra-02，哪块有数据就先做哪块。',
        '也可先用能对版的供应方机械图/CAD 建名义模型，随后核对实物。',
    ])
    section(561, '只做断电外部测量')
    lines(532, [
        '外接电源、USB、编程器全部断开；不为测量上电、焊接、拆封或掰针。',
        'IPEX 未连接就记未知，不为此反复插拔。中文长备注写纸面或 Markdown。',
        '正面、背面、侧面和丝印各拍一张，照片标 O / X / Y 与临时实物编号。',
        '照片用于辨认位置，不能用商品缩略图或透视像素比例推算装配尺寸。',
        '关键尺寸保留 3 次原始读数；同时记量具、分辨率与精度/不确定度。',
        '只有直尺就给粗测值并注明误差，孔针配合保持未知，不要求另购卡尺。',
    ])
    section(398, '统一基准与分阶段输入')
    lines(369, [
        'O：TOP 视图主要 PCB 左下角两直边延长交点；X 向右，Y 向上。',
        'PCB L 沿 Y，W 沿 X。T 是板材厚度；Z=0 为 PCB 下表面。',
        'H+ / H- 分别从板上 / 下表面量起，记录正的距离。',
        '完整 Z 范围 [-H-, T+H+]；总高 T+H++H-。固定突出计入完整 XY。',
        'A 外廓：先做带不确定度的粗排布占位，不据此生成紧配合支架。',
        'B 安装：孔坐标/孔径、排针中心、两面避让和可接触板边。',
        'C 接线：插头壳体、插拔方向、自然走线与检修路径；未知项保持空白。',
        '安装余量是设计选择，不是测量值。机械不碰撞不等于射频/散热合格。',
    ])
    section(180, '交接与来源')
    lines(152, [
        '后续五页是一件一表。Ra-02 的两块必须分别测；零与空白不能混用。',
        '完整方法、孔/针/线字段与既有工程记录的对应见：',
        'cad_reference/BOARD_MEASUREMENT_WORKBOOK.md',
        '原始照片和填写后表格先私下提交；仓库不放个人订单字段。',
        '这份表未解除 19 项 TVC CAD_START 缺项，未完成整机装配 CAD。',
    ], size=9.6, leading=17)
    c.showPage()

    for page, (key, title, asset, orient, focus) in enumerate(UNITS, 2):
        header(title, page)
        text(42, 719, asset, 10)
        text(42, 700, orient, 10)
        text(42, 681, focus, 9.5)
        text(42, 657, 'PCB 版号 / 实物照片编号（另附中文备注）：', 10)
        field(key, 'revision_photo_ids', 270, 651, 280)
        text(42, 630, '日期 / 量具 / 分辨率 / 精度或估计不确定度：', 10)
        field(key, 'date_tool_resolution_uncertainty', 270, 624, 280)
        section(599, 'A / 外廓最小输入（单位 mm；每框可写 3 次读数，以逗号分隔）')

        # Deliberately schematic; no product-like outline, sizes or hole positions.
        c.setStrokeColor(gray)
        c.setDash(3, 3)
        c.rect(70, 483, 160, 82)
        c.setDash()
        c.line(70, 483, 245, 483)
        c.line(70, 483, 70, 576)
        text(48, 470, 'O', 10)
        text(240, 470, '+X', 10)
        text(50, 574, '+Y', 10)
        text(96, 518, 'TOP：基准示意', 11)
        text(93, 501, '不代表实际板轮廓', 9, gray)
        c.rect(331, 514, 190, 9)
        c.setDash(2, 2)
        c.line(321, 552, 533, 552)
        c.line(321, 489, 533, 489)
        c.setDash()
        text(338, 536, 'H+ 从板上表面量', 10)
        text(338, 498, 'H- 从板下表面量', 10)
        text(339, 470, '侧视：Z=0 为板下表面', 10)
        labels = [('PCB_L', 'L (Y)'), ('PCB_W', 'W (X)'), ('PCB_T', 'PCB T'),
                  ('H_plus', 'H+'), ('H_minus', 'H-'), ('X_min', 'Xmin'),
                  ('X_max', 'Xmax'), ('Y_min', 'Ymin'), ('Y_max', 'Ymax')]
        for i, (name, label) in enumerate(labels):
            row, col = divmod(i, 3)
            x, y = 42 + col*174, 435-row*29
            text(x, y+5, label, 10)
            field(key, name, x+47, y, 116)
        text(42, 340, '刚性外廓包括天线、USB 壳和排针塑料；线缆柔性空间另记 C。', 9.4)
        text(42, 321, '轮廓缺口 / 达到极值的元件 / 排针已焊状态（附页）：', 9.4)
        field(key, 'outline_header_state_attachment', 330, 315, 220)
        section(287, 'B / 安装接口（同一原点；无孔 / 未看清须区分）')
        text(42, 258, '实际安装孔数：', 10)
        field(key, 'mount_hole_count', 125, 251, 60)
        text(202, 258, '孔表附页编号：', 10)
        field(key, 'mount_hole_table_ref', 285, 251, 265)
        text(42, 235, '每孔 Hn：(x,y,d)，两面螺钉头/垫片避让；孔多于一页则附页。', 9.4)
        text(42, 212, '排针表 / 可接触板边附页编号：', 10)
        field(key, 'headers_edge_zones_ref', 228, 205, 322)
        text(42, 188, '每排 Jn：针数、首针(x,y)、方向、针距、排间距、塑料和针顶/底高度。', 9.3)
        section(157, 'C / 插接与检修（仅记录现有状态，未装不强行补齐）')
        text(42, 127, '接口 / 走线 / 按键 / 特殊避让附页编号：', 10)
        field(key, 'connectors_service_keepouts_ref', 285, 120, 265)
        text(42, 101, '各接口：插头包络、插拔方向、自然走线、工具路径；无线/通气要求另查。', 9.2)
        text(42, 81, '数值框支持数字/英文；中文备注用纸面或正文。原始照片先私下交接。', 9.2)
        text(42, 61, '空白 = 未取得；无数据不补常见值。本页不建立实物配合或制造资格。', 9.2)
        c.showPage()
    c.save()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    create(p.parse_args().output)


if __name__ == '__main__':
    main()
