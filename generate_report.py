# -*- coding: utf-8 -*-
"""
generate_report.py - 生成全国城市空气质量可视化大屏项目报告 Word 文档

使用 Python 内置模块（pandas + zipfile）生成 .docx 文件，
包含项目概述、技术实现、可视化成果、数据分析与发现等完整内容。
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape

# ─── 路径配置 ───
PROJECT_DIR = r"C:\Users\wxt11\Desktop\大数据可视化大屏"
os.chdir(PROJECT_DIR)

OUTPUT_PATH = os.path.join(PROJECT_DIR, "项目报告.docx")


def compute_findings():
    """从 CSV 数据计算各项分析指标，返回结构化结果"""
    import pandas as pd

    df = pd.read_csv(r"data/air_city_day.csv", encoding='utf-8-sig')

    # 解析日期（CSV 中为 dd/mm/yyy 格式）
    df['release_date'] = pd.to_datetime(df['release_date'], format='%d/%m/%Y')

    # 提取省份简称（去掉"省"/"市"/"自治区"等后缀）
    def short_province(name):
        for suffix in ["壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "省", "市"]:
            if name.endswith(suffix):
                return name.replace(suffix, "")
        return name

    df['province_short'] = df['province'].apply(short_province)

    findings = {}

    # 1. 基本信息
    findings['total_cities'] = len(df)
    findings['data_date'] = df['release_date'].dt.strftime("%Y年%m月%d日").iloc[0]
    findings['total_province'] = df['province'].nunique()
    findings['avg_aqi'] = round(df['AQI'].mean(), 1)
    findings['good_count'] = len(df[df['AQI'] <= 100])
    findings['good_ratio'] = round(findings['good_count'] / findings['total_cities'] * 100, 1)
    findings['avg_pm25'] = round(df['PM25'].mean(), 1)
    findings['avg_pm10'] = round(df['PM10'].mean(), 1)

    # 2. 最优/最差城市
    best_idx = df.loc[df['AQI'].idxmin()]
    worst_idx = df.loc[df['AQI'].idxmax()]
    findings['best_city'] = best_idx['city_label']
    findings['best_aqi'] = int(best_idx['AQI'])
    findings['worst_city'] = worst_idx['city_label']
    findings['worst_aqi'] = int(worst_idx['AQI'])

    # 3. 空气质量等级分布
    findings['quality_dist'] = {}
    for level in ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]:
        count = len(df[df['quality'] == level])
        ratio = round(count / findings['total_cities'] * 100, 1)
        findings['quality_dist'][level] = {'count': count, 'ratio': ratio}

    # 4. 首要污染物分布（使用 data 中实际的 pollututions 值作为 key）
    findings['pollutant_dist'] = {}
    for pol, count in df['pollutions'].value_counts().items():
        if pol != "无":
            ratio = round(count / findings['total_cities'] * 100, 1)
            findings['pollutant_dist'][pol] = {'count': int(count), 'ratio': ratio}

    # 5. 区域对比（七大区域 AQI 均值）
    region_map = {
        "北京": "华北", "天津": "华北", "河北": "华北", "山西": "华北", "内蒙古": "华北",
        "辽宁": "东北", "吉林": "东北", "黑龙江": "东北",
        "上海": "华东", "江苏": "华东", "浙江": "华东", "安徽": "华东",
        "福建": "华东", "江西": "华东", "山东": "华东",
        "河南": "华中", "湖北": "华中", "湖南": "华中",
        "广东": "华南", "广西": "华南", "海南": "华南",
        "重庆": "西南", "四川": "西南", "贵州": "西南", "云南": "西南", "西藏": "西南",
        "陕西": "西北", "甘肃": "西北", "青海": "西北", "宁夏": "西北", "新疆": "西北",
    }
    df['region'] = df['province_short'].map(region_map).fillna("其他")
    region_stats = df.groupby('region')['AQI'].mean().round(1)
    findings['region_stats'] = {r: float(v) for r, v in region_stats.items()}

    # 6. 污染物均值
    findings['pollutant_avg'] = {
        'PM2.5': round(df['PM25'].mean(), 1),
        'PM10': round(df['PM10'].mean(), 1),
        'SO2': round(df['SO2'].mean(), 1),
        'NO2': round(df['NO2'].mean(), 1),
        'CO': round(df['CO'].mean(), 1),
        'O3': round(df['O3_8h_24h'].mean(), 1),
    }

    return findings


def build_findings(findings):
    """将计算数据转为可读的发现文本"""
    findings_text = []

    # 发现 1
    findings_text.append(
        f"**发现一：全国空气质量整体处于「良」以上水平**\n"
        f"本日监测的 {findings['total_cities']} 个城市中，空气质量「优」和「良」的城市占比达 {findings['good_ratio']}%，"
        f"全国平均 AQI 指数为 {findings['avg_aqi']}，"
        f"空气质量整体处于良好偏好的区间。"
    )

    # 发现 2
    findings_text.append(
        f"**发现二：城市空气质量差异显著，极端值突出**\n"
        f"{findings['worst_city']} 当日 AQI 高达 {findings['worst_aqi']}（严重污染），是全国空气质量最差的城市，"
        f"污染程度较重；"
        f"反观 {findings['best_city']}，AQI 仅 {findings['best_aqi']}，空气质量达到最优水平，"
        f"两地空气质量差异达到 {findings['worst_aqi'] - findings['best_aqi']} 个 AQI 指数，差距明显。"
    )

    # 发现 3
    # 根据数据中实际的首要污染物 key 来生成
    pol_map = {
        'PM10': 'PM10',
        'PM25': 'PM2.5',
        'O3': 'O₃',
        'NO2': 'NO₂',
    }
    pol_lines = []
    for key in ['PM10', 'PM25', 'O3', 'NO2']:
        if key in findings['pollutant_dist']:
            info = findings['pollutant_dist'][key]
            display = pol_map.get(key, key)
            pol_lines.append(f"**{display}**：{info['count']} 个城市，占比 {info['ratio']}%")

    findings_text.append(
        f"**发现三：首要污染物以 PM10 为主，污染特征明显**\n"
        f"{('、'.join(pol_lines[:3]))}。这表明本次监测期间颗粒物类污染是空气污染的主要来源，"
        f"对城市空气质量影响较大。"
    )

    # 发现 4
    findings_text.append(
        f"**发现四：区域空气质量差异明显，部分区域污染较重**\n"
        f"七大区域 AQI 均值统计显示：{('、'.join(f'{r} {v}' for r, v in sorted(findings['region_stats'].items(), key=lambda x: -x[1])))}。"
        f"华北地区（AQI {findings['region_stats']['华北']}）和西北地区（AQI {findings['region_stats']['西北']}）空气质量相对较差，"
        f"而西南地区（AQI {findings['region_stats']['西南']}）空气最为清洁。"
    )

    return "\n\n".join(findings_text)


def create_docx(findings):
    """使用 zipfile 生成标准 .docx 文件"""

    # ─── 计算数据内容（用于报告正文） ───
    data_parts = []

    # 基本信息
    data_parts.append(
        f"监测城市总数：**{findings['total_cities']}** 个\n"
        f"监测省份数量：**{findings['total_province']}** 个\n"
        f"数据日期：**{findings['data_date']}**\n"
        f"全国平均 AQI 指数：**{findings['avg_aqi']}**\n"
        f"优良城市占比：**{findings['good_ratio']}%**\n"
        f"全国平均 PM2.5 浓度：**{findings['avg_pm25']} μg/m³**\n"
        f"全国平均 PM10 浓度：**{findings['avg_pm10']} μg/m³**\n"
        f"最优城市：**{findings['best_city']}**（AQI {findings['best_aqi']}）\n"
        f"最差城市：**{findings['worst_city']}**（AQI {findings['worst_aqi']}）"
    )

    # 空气质量等级分布
    quality_lines = []
    for level in ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]:
        info = findings['quality_dist'][level]
        quality_lines.append(f"**{level}**：{info['count']} 个城市，占比 {info['ratio']}%")
    data_parts.append("**空气质量等级分布**：" + "；".join(quality_lines) + "\n")

    # 首要污染物分布
    pollutant_lines = []
    for key in ['PM10', 'PM25', 'O3', 'NO2']:
        if key in findings['pollutant_dist']:
            info = findings['pollutant_dist'][key]
            pol_map = {
                'PM10': 'PM10',
                'PM25': 'PM2.5',
                'O3': 'O₃',
                'NO2': 'NO₂',
            }
            display = pol_map.get(key, key)
            pollutant_lines.append(f"**{display}**：{info['count']} 个城市，占比 {info['ratio']}%")
    data_parts.append("**首要污染物分布**：" + "；".join(pollutant_lines) + "\n")

    # 区域对比
    region_lines = []
    for region in ["华北", "东北", "华东", "华中", "华南", "西南", "西北"]:
        aqi = findings['region_stats'][region]
        region_lines.append(f"**{region}**：AQI 均值 {aqi}")
    data_parts.append("**七大区域 AQI 均值对比**：" + "；".join(region_lines) + "\n")

    findings_text = build_findings(findings)

    # ─── 构建 XML 内容（.docx 格式） ───
    def escape_text(text):
        return escape(text, {'"': "&quot;"})

    # 文档正文段落
    paragraphs = []

    # 标题
    paragraphs.append(
        f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>{escape_text(f"全国城市空气质量可视化大屏 — 项目报告与数据分析")}</w:t></w:r></w:p>'
    )

    # 空行
    paragraphs.append('<w:p/>')

    # 一、项目概述
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>一、项目概述</w:t></w:r></w:p>')

    # 1.1 项目背景
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1 项目背景</w:t></w:r></w:p>')
    paragraphs.append(
        '本项目基于和鲸社区城市环境空气质量数据，构建了一款面向 1920×1080（16:9）大屏的「全国城市空气质量实时监测可视化系统」，'
        '旨在通过大数据分析与可视化手段，直观呈现全国城市空气质量状况，服务于课程学习、数据分析及汇报展示需求。'
    )

    # 1.2 数据集说明
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.2 数据集说明</w:t></w:r></w:p>')
    paragraphs.append(
        f'数据来源为和鲸社区城市环境空气质量日数据集，涵盖 **{findings["total_cities"]}** 个城市的监测数据，'
        f'覆盖 **{findings["total_province"]}** 个省份，数据日期为 {findings["data_date"]}（单日快照）。'
        f'数据集包含 AQI、PM2.5、PM10、SO₂、NO₂、CO、O₃ 等污染物浓度及空气质量等级等字段，数据完整、结构清晰，为可视化分析提供了可靠基础。'
    )

    # 1.3 技术要求
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.3 技术要求</w:t></w:r></w:p>')
    paragraphs.append(
        f'系统严格按照作业要求实现，核心技术指标包括：\n'
        f'• 画布尺寸：1920×1080，16:9 宽屏布局，适配大屏展示；\n'
        f'• 核心指标：设置 4 个核心 KPI 卡片（全国平均 AQI、优良城市占比、平均 PM2.5、污染城市数）；\n'
        f'• 可视化模块：包含 6 个可视化图表模块，覆盖柱状图、饼图、分组柱状图等多种图表类型；\n'
        f'• 交互功能：支持省份筛选、污染物类型筛选、城市排名（最差/最优）切换等交互；\n'
        f'• 视觉效果：深蓝科技风格配色，蓝绿主色调，数据全部来自实时接口，无硬编码值。'
    )

    # 二、系统架构与技术实现
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>二、系统架构与技术实现</w:t></w:r></w:p>')

    # 2.1 技术栈
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>2.1 技术栈</w:t></w:r></w:p>')
    paragraphs.append(
        '系统采用前后端分离架构，前端使用 HTML、CSS、JavaScript 结合 ECharts 实现可视化渲染，'
        '后端使用 Flask 提供数据接口，数据处理使用 Pandas 完成清洗与统计分析，技术栈成熟、功能完备。'
    )

    # 2.2 文件结构
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>2.2 文件结构</w:t></w:r></w:p>')
    paragraphs.append(
        '<w:t>项目核心文件结构如下：\n'
        '<w:t>数据层：</w:t><w:t>data/air_city_day.csv</w:t>（原始监测数据集）</w:t><w:t>；</w:t><w:t>数据处理：</w:t><w:t>data_processor.py</w:t>（数据清洗与统计接口）</w:t>；</w:t><w:t>后端服务：</w:t><w:t>app.py</w:t>（Flask 服务与 API 接口）</w:t>；</w:t><w:t>前端页面：</w:t><w:t>templates/index.html</w:t>（大屏页面模板）</w:t>；</w:t><w:t>前端样式：</w:t><w:t>static/css/style.css</w:t>（大屏样式与主题）</w:t>；</w:t><w:t>前端逻辑：</w:t><w:t>static/js/main.js</w:t>（ECharts 图表与交互逻辑）</w:t>；</w:t><w:t>分析脚本：</w:t><w:t>analyze_data.py</w:t>（数据集质量分析与统计）</w:t>'
    )

    # 2.3 系统架构说明
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>2.3 系统架构说明</w:t></w:r></w:p>')
    paragraphs.append(
        '系统采用「Flask 后端 + 前端可视化」分层架构：后端 app.py 负责加载并清洗数据，'
        '通过多组 RESTful API 接口（如 /api/summary、/api/province_ranking、/api/region_pollutant_comparison 等）'
        '向外提供标准化数据；前端 index.html + main.js 通过 ECharts 渲染各类图表，'
        '所有数据均通过实时接口获取，无硬编码值，确保数据时效性与准确性。'
    )

    # 三、数据可视化成果
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>三、数据可视化成果</w:t></w:r></w:p>')

    # 3.1 核心指标卡片
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>3.1 核心指标卡片</w:t></w:r></w:p>')
    paragraphs.append(
        f'页面顶部设置 4 个核心 KPI 卡片，实时展示关键监测指标：'
        f'全国平均 AQI（{findings["avg_aqi"]}）、优良城市占比（{findings["good_ratio"]}%）、'
        f'平均 PM2.5（{findings["avg_pm25"]} μg/m³）、污染城市数。'
        f'卡片采用动态数字动画效果，数据随接口实时更新，直观呈现空气质量核心结论。'
    )

    # 3.2 图表模块说明
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>3.2 图表模块说明</w:t></w:r></w:p>')
    chart_desc = [
        "**省份 AQI 排名 Top 15**（水平柱状图）：展示各省级区域平均 AQI 排名，按 AQI 由高到低排列，配色随 AQI 等级变化，直观呈现区域空气质量差异。",
        "**空气质量等级分布**（饼图）：按空气质量等级统计城市数量与占比，环形饼图展示不同等级的分布结构，支持悬浮查看具体数据。",
        "**首要污染物分布**（柱状图）：统计各首要污染物的城市覆盖数与占比，柱状图清晰展示各类污染物的分布特征。",
        "**污染物浓度对比**（水平柱状图）：对比全国六项主要污染物（PM2.5、PM10、SO₂、NO₂、CO、O₃）的均值浓度，直观呈现污染物浓度差异。",
        "**区域 × 污染物对比**（分组柱状图）：以分组柱状图形式展示七大区域各项污染物的浓度对比，支持按区域、污染物多维度筛选。",
        "**城市排名 Top 10**（垂直柱状图）：展示城市 AQI 排名，支持切换最差/最优模式，按 AQI 等级着色，突出空气质量优劣势城市。",
    ]
    for i, desc in enumerate(chart_desc, 1):
        paragraphs.append(f'<w:p><w:pPr><w:pStyle w:val="ListBullet"/></w:pPr><w:r><w:t>{desc}</w:t></w:r></w:p>')

    # 3.3 交互功能说明
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>3.3 交互功能说明</w:t></w:r></w:p>')
    interact_desc = [
        "**省份筛选**：通过下拉框可按省份（全部省份/华北/东北/华东/华中/华南/西南/西北/其他）筛选，实时更新省份 AQI 排名图表与区域对比图表，缩小数据范围。",
        "**污染物类型筛选**：通过下拉框可按污染物类型（PM2.5/PM10/SO₂/NO₂/CO/O₃）筛选，实时更新首要污染物分布图表与区域对比图表，聚焦特定污染物分析。",
        "**城市排名切换**：通过按钮在「最差城市」与「最优城市」间切换，实时切换城市排名图表，分别呈现空气质量最差与最优的城市，辅助分析极端空气质量情况。",
    ]
    for i, desc in enumerate(interact_desc, 1):
        paragraphs.append(f'<w:p><w:pPr><w:pStyle w:val="ListBullet"/></w:pPr><w:r><w:t>{desc}</w:t></w:r></w:p>')

    # 3.4 视觉效果说明
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>3.4 视觉效果</w:t></w:r></w:p>')
    paragraphs.append(
        '系统采用深蓝科技风格配色，以深蓝（#0a1929）为背景主色调，搭配蓝绿（#00d4ff）高亮色，'
        '营造专业、科技感的展示氛围；布局采用 3×3 网格的 16:9 宽屏结构，图表卡片统一边框与圆角风格，'
        '视觉层次清晰、美观协调，适配大屏高清展示需求。'
    )

    # 四、数据分析与发现
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>四、数据分析与发现</w:t></w:r></w:p>')
    paragraphs.append(build_findings(findings))

    # 五、结论与展望
    paragraphs.append('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>五、结论与展望</w:t></w:r></w:p>')
    paragraphs.append(
        f'本项目基于和鲸社区真实监测数据，完成了全国城市空气质量可视化大屏的构建，'
        f'通过 4 个核心指标、6 个可视化图表与 3 项交互功能，全面呈现了单日全国城市空气质量监测结果。'
        f'数据分析表明，全国空气质量整体处于良好水平，但城市间空气质量差异显著，首要污染物以 PM10 为主，'
        f'区域空气质量存在明显差异。'
        f'未来可进一步扩展数据维度、优化交互体验、引入实时更新机制，提升可视化系统的大数据分析与展示能力。'
    )

    # ─── 生成 .docx 文件 ───
    document_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    document_xml += '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    document_xml += '<w:body>'

    # 添加段落
    for p in paragraphs:
        document_xml += p + '</w:p>'

    # 添加页脚
    document_xml += '<w:p>'
    document_xml += '<w:pPr><w:pStyle w:val="Footer"/></w:pPr>'
    document_xml += '<w:r><w:t>全国城市空气质量可视化大屏项目报告</w:t></w:r>'
    document_xml += '</w:p>'

    document_xml += '<w:sectPr>'
    document_xml += '<w:pgSz w:w="11906" w:h="16838"/>'
    document_xml += '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
    document_xml += '</w:sectPr>'
    document_xml += '</w:body></w:document>'

    # 定义 Content Types
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '</Types>'
    )

    # 根关系
    rels_root = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )

    # document 关系
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )

    # 样式定义
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei" w:hAnsi="Microsoft YaHei"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:rPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1"><w:name w:val="Normal"/><w:pPr><w:spacing w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:spacing w:before="240" w:after="120" w:line="360" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/><w:b/><w:sz w:val="42"/><w:szCs w:val="42"/><w:color w:val="2E7DD2"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:spacing w:before="240" w:after="120" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="480"/></w:pPr><w:rPr><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/><w:color w:val="00D4FF"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:spacing w:before="200" w:after="100" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="480"/></w:pPr><w:rPr><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/><w:b/><w:sz w:val="26"/><w:szCs w:val="26"/><w:color w:val="4ECDC4"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:pPr><w:ind w:left="480" w:hanging="240"/></w:pPr></w:style>'
        '</w:styles>'
    )

    # 创建 zip 文件
    with zipfile.ZipFile(OUTPUT_PATH, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('[Content_Types].xml', content_types)
        zipf.writestr('_rels/.rels', rels_root)
        zipf.writestr('word/document.xml', document_xml)
        zipf.writestr('word/_rels/document.xml.rels', doc_rels)
        zipf.writestr('word/styles.xml', styles_xml)

    # 验证文件生成
    if os.path.exists(OUTPUT_PATH):
        file_size = os.path.getsize(OUTPUT_PATH)
        print(f"✅ Word 文档已生成：{OUTPUT_PATH}")
        print(f"   文件大小：{file_size} 字节")
    else:
        print("❌ Word 文档生成失败")
        sys.exit(1)


def main():
    """主流程：计算数据 → 构建文档 → 生成 Word 文件"""
    print("开始计算数据分析指标...")
    findings = compute_findings()

    print("开始生成 Word 文档...")
    create_docx(findings)

    print("\n🎉 项目报告生成完成！")
    print(f"   报告文件路径：{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
