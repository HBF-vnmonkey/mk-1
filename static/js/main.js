/* ============================================================
   main.js - 前端图表逻辑
   调用后端 API 获取数据，使用 ECharts 渲染图表
   ============================================================ */

// ─── 全局配色方案 ───
const COLORS = {
    primary: '#00d4ff',
    success: '#4ecdc4',
    warning: '#ffeaa7',
    danger: '#ff6b6b',
    purple: '#a29bfe',
    pink: '#fd79a8',
    orange: '#e17055',
    blue: '#0984e3',
    green: '#00b894',
    yellow: '#fdcb6e',
};

// 空气质量等级对应颜色
const QUALITY_COLORS = {
    '优': '#00e400',
    '良': '#ffff00',
    '轻度污染': '#ff7e00',
    '中度污染': '#ff0000',
    '重度污染': '#99004c',
    '严重污染': '#7e0023',
};

// 通用 ECharts 文字样式
const TEXT_STYLE = {
    color: '#8badc1',
    fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
};

// ─── 工具函数 ───

/**
 * 发起 GET 请求并返回 JSON
 */
async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`API 请求失败: ${url} → ${resp.status}`);
    return resp.json();
}

/**
 * 初始化 ECharts 实例，自适应窗口大小
 */
function initChart(domId) {
    const dom = document.getElementById(domId);
    if (!dom) {
        console.error(`图表容器 #${domId} 不存在`);
        return null;
    }
    return echarts.init(dom, null, { renderer: 'canvas' });
}

/**
 * 为柱状图生成渐变色
 */
function barGradient(colorStart, colorEnd) {
    return new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: colorStart },
        { offset: 1, color: colorEnd },
    ]);
}

/**
 * 根据 AQI 值返回对应的颜色
 * @param {number} aqi 空气质量指数
 * @returns {string} 颜色值
 */
function getAqiColor(aqi) {
    if (aqi <= 50) return COLORS.green;
    if (aqi <= 100) return COLORS.warning;
    if (aqi <= 150) return COLORS.orange;
    if (aqi <= 200) return COLORS.danger;
    return COLORS.purple;
}

// ─── 交互状态与映射常量 ───

// 当前筛选状态：省份筛选值、污染物筛选值、排名模式（worst=最差 / best=最优）
const filterState = {
    province: '',          // 为空表示全部省份
    pollutant: '',         // 为空表示全部污染物
    rankMode: 'worst',     // 城市排名模式
};

// 省份筛选选项 → 污染物对比指标映射（对应 /api/region_pollutant_comparison 的污染物字段）
const POLLUTANT_METRIC_MAP = {
    'PM2.5': 'pm25',
    'PM10': 'pm10',
    'SO₂': 'so2',
    'NO₂': 'no2',
    'CO': 'co',
    'O₃': 'o3',
};

// 污染物分布筛选选项 → 污染物分布函数的数据映射
// （污染物分布接口直接返回污染物名，无需额外映射，这里仅做选项值校验）
const POLLUTANT_DIST_OPTIONS = [
    '', 'PM2.5', 'PM10', 'SO₂', 'NO₂', 'CO', 'O₃'
];

// ─── 图表渲染函数 ───

/**
 * 1. 核心指标卡片
 */
async function renderSummary() {
    const data = await fetchJSON('/api/summary');

    document.getElementById('dataDate').textContent = data.data_date;
    document.getElementById('footerDate').textContent = data.data_date;
    document.getElementById('footerCities').textContent = data.total_cities;
    document.getElementById('footerPm25').textContent = data.avg_pm25;

    // 数字动画效果
    animateValue('kpiCities', 0, data.total_cities, 800, '', ' 个');
    animateValue('kpiAvgAqi', 0, data.avg_aqi, 1000, '', '');
    animateValue('kpiGoodRatio', 0, data.good_ratio, 1000, '', '%');
    animateValue('kpiPm25', 0, data.avg_pm25, 1000, '', '');
    // 污染城市数 = 总城市数 - 优良城市数（后端 summary 未返回 good_count，由优良占比反推）
    const pollutedCount = data.total_cities - Math.round(data.total_cities * data.good_ratio / 100);
    animateValue('kpiPollutedCities', 0, pollutedCount, 800, '', ' 个');

    // 赋值前做存在性判断，避免元素缺失导致崩溃
    const bestEl = document.getElementById('kpiBestCity');
    if (bestEl) bestEl.textContent = `${data.best_city} (${data.best_aqi})`;
    const worstEl = document.getElementById('kpiWorstCity');
    if (worstEl) worstEl.textContent = `${data.worst_city} (${data.worst_aqi})`;
}

/**
 * 数字递增动画
 */
function animateValue(elemId, start, end, duration, prefix, suffix) {
    const elem = document.getElementById(elemId);
    if (!elem) return;
    const range = end - start;
    const startTime = performance.now();
    const isFloat = !Number.isInteger(end);

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // ease-out
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + range * eased;
        elem.textContent = prefix + (isFloat ? current.toFixed(1) : Math.round(current)) + suffix;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

/**
 * 2. 省份 AQI 排名柱状图
 */
async function renderProvinceRanking() {
    const data = await fetchJSON('/api/province_ranking');
    const chart = initChart('chartProvinceRanking');
    if (!chart) return;

    // 从低到高排列（最高的在上面）
    const sorted = [...data].reverse();
    const provinces = sorted.map(d => d.province);
    const aqiValues = sorted.map(d => d.aqi);

    // 根据 AQI 值生成颜色
    const barColors = sorted.map(d => {
        if (d.aqi <= 50) return COLORS.green;
        if (d.aqi <= 100) return COLORS.warning;
        if (d.aqi <= 150) return COLORS.orange;
        if (d.aqi <= 200) return COLORS.danger;
        return COLORS.purple;
    });

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.primary,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = sorted[params[0].dataIndex];
                return `<strong>${d.province}</strong><br/>
                    AQI 均值：${d.aqi}<br/>
                    PM2.5 均值：${d.pm25} μg/m³<br/>
                    PM10 均值：${d.pm10} μg/m³<br/>
                    监测城市：${d.city_count} 个`;
            },
        },
        grid: {
            left: 80, right: 40, top: 10, bottom: 20,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        yAxis: {
            type: 'category',
            data: provinces,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        series: [{
            type: 'bar',
            data: aqiValues.map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(0, 212, 255, 0.2)' },
                        { offset: 1, color: barColors[i] },
                    ]),
                    borderRadius: [0, 4, 4, 0],
                },
            })),
            barWidth: '60%',
            label: {
                show: true,
                position: 'right',
                color: '#e0f0ff',
                fontSize: 11,
                formatter: '{c}',
            },
        }],
    });

    window.addEventListener('resize', () => chart.resize());
}

/**
 * 3. 空气质量等级分布饼图
 */
async function renderQualityDist() {
    const data = await fetchJSON('/api/quality_distribution');
    const chart = initChart('chartQualityDist');
    if (!chart) return;

    const pieData = data.map(d => ({
        name: d.level,
        value: d.count,
        itemStyle: { color: QUALITY_COLORS[d.level] || COLORS.primary },
    }));

    chart.setOption({
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.primary,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                return `<strong>${params.name}</strong><br/>
                    城市数：${params.value} 个<br/>
                    占比：${params.percent}%`;
            },
        },
        legend: {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: { color: '#e0f0ff', fontSize: 11 },
            itemWidth: 12,
            itemHeight: 12,
            itemGap: 10,
        },
        series: [{
            type: 'pie',
            radius: ['40%', '65%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderColor: '#112240',
                borderWidth: 2,
                borderRadius: 4,
            },
            label: { show: false },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 13,
                    fontWeight: 'bold',
                    color: '#e0f0ff',
                },
                itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'rgba(0, 212, 255, 0.5)',
                },
            },
            data: pieData,
        }],
    });

    window.addEventListener('resize', () => chart.resize());
}

/**
 * 4. 首要污染物分布柱状图
 */
async function renderPollutantDist() {
    const data = await fetchJSON('/api/pollutant_distribution');
    const chart = initChart('chartPollutantDist');
    if (!chart) return;

    const names = data.map(d => d.pollutant);
    const values = data.map(d => d.count);
    const colors = [COLORS.primary, COLORS.success, COLORS.warning, COLORS.orange, COLORS.pink, COLORS.purple];

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.primary,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = data[params[0].dataIndex];
                return `<strong>${d.pollutant}</strong><br/>
                    城市数：${d.count} 个<br/>
                    占比：${d.ratio}%`;
            },
        },
        grid: {
            left: 70, right: 30, top: 10, bottom: 30,
        },
        xAxis: {
            type: 'category',
            data: names,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        series: [{
            type: 'bar',
            data: values.map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: colors[i % colors.length] },
                        { offset: 1, color: 'rgba(0, 212, 255, 0.1)' },
                    ]),
                    borderRadius: [4, 4, 0, 0],
                },
            })),
            barWidth: '50%',
            label: {
                show: true,
                position: 'top',
                color: '#e0f0ff',
                fontSize: 11,
                formatter: '{c}个',
            },
        }],
    });

    window.addEventListener('resize', () => chart.resize());
}

/**
 * 5. 污染最重 Top 10 城市
 */
async function renderWorstCities() {
    const data = await fetchJSON('/api/worst_cities');
    const chart = initChart('chartWorstCities');
    if (!chart) return;

    // 从低到高排列（最严重的在上面）
    const sorted = [...data].reverse();
    const cities = sorted.map(d => d.city);
    const aqiValues = sorted.map(d => d.aqi);

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.danger,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = sorted[params[0].dataIndex];
                return `<strong>${d.city}</strong>（${d.province}）<br/>
                    AQI：${d.aqi} ${d.quality}<br/>
                    PM2.5：${d.pm25} μg/m³<br/>
                    PM10：${d.pm10} μg/m³<br/>
                    首要污染物：${d.pollution}`;
            },
        },
        grid: {
            left: 80, right: 40, top: 10, bottom: 10,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        yAxis: {
            type: 'category',
            data: cities,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        series: [{
            type: 'bar',
            data: aqiValues.map(v => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(255, 107, 107, 0.15)' },
                        { offset: 1, color: v > 200 ? '#ff4757' : v > 150 ? '#ff6b6b' : '#e17055' },
                    ]),
                    borderRadius: [0, 4, 4, 0],
                },
            })),
            barWidth: '55%',
            label: {
                show: true,
                position: 'right',
                color: '#ff6b6b',
                fontSize: 11,
                fontWeight: 'bold',
                formatter: '{c}',
            },
        }],
    });

    window.addEventListener('resize', () => chart.resize());
}

/**
 * 6. 空气最优 Top 10 城市
 */
async function renderBestCities() {
    const data = await fetchJSON('/api/best_cities');
    const chart = initChart('chartBestCities');
    if (!chart) return;

    // 从高到低排列（最优的在上面）
    const sorted = [...data].reverse();
    const cities = sorted.map(d => d.city);
    const aqiValues = sorted.map(d => d.aqi);

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.success,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = sorted[params[0].dataIndex];
                return `<strong>${d.city}</strong>（${d.province}）<br/>
                    AQI：${d.aqi} ${d.quality}<br/>
                    PM2.5：${d.pm25} μg/m³<br/>
                    PM10：${d.pm10} μg/m³`;
            },
        },
        grid: {
            left: 80, right: 40, top: 10, bottom: 10,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        yAxis: {
            type: 'category',
            data: cities,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        series: [{
            type: 'bar',
            data: aqiValues.map(v => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(78, 205, 196, 0.15)' },
                        { offset: 1, color: '#4ecdc4' },
                    ]),
                    borderRadius: [0, 4, 4, 0],
                },
            })),
            barWidth: '55%',
            label: {
                show: true,
                position: 'right',
                color: '#4ecdc4',
                fontSize: 11,
                fontWeight: 'bold',
                formatter: '{c}',
            },
        }],
    });

    window.addEventListener('resize', () => chart.resize());
}

// ─── 图表：污染物浓度对比 ───

/**
 * 污染物浓度对比（全国六项污染物均值柱状图）
 * 数据来源：/api/pollutants_average
 */
async function renderPollutantsAverage() {
    const data = await fetchJSON('/api/pollutants_average');
    const chart = initChart('chartPollutantsAverage');
    if (!chart) return;

    const names = data.names;
    const values = data.values;
    const barColors = ['#00d4ff', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#fd79a8'];

    const seriesData = values.map((v, i) => ({
        value: v,
        itemStyle: {
            color: barColors[i % barColors.length],
            borderRadius: [0, 4, 4, 0],
        },
    }));

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: '#00d4ff',
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const idx = params[0].dataIndex;
                return `<strong>${names[idx]}</strong><br/>
                    浓度均值：${values[idx]} ${params[0].axisValue}`;
            },
        },
        grid: {
            left: 80, right: 40, top: 20, bottom: 20,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        yAxis: {
            type: 'category',
            data: names,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        series: [{
            type: 'bar',
            data: seriesData,
            barWidth: '55%',
            label: {
                show: true,
                position: 'right',
                color: '#e0f0ff',
                fontSize: 11,
                fontWeight: 'bold',
                formatter: '{c}',
            },
        }],
    });

    window.addEventListener('resize', () => chart.resize());
}

// ─── 图表：区域×污染物对比 ───

/**
 * 区域×污染物对比（分组柱状图）
 * 数据来源：/api/region_pollutant_comparison
 */
async function renderRegionComparison() {
    const data = await fetchJSON('/api/region_pollutant_comparison');
    const chart = initChart('chartRegionComparison');
    if (!chart) return;

    // 污染物指标定义
    const metrics = [
        { key: 'aqi', name: 'AQI', unit: '', color: COLORS.danger },
        { key: 'pm25', name: 'PM2.5', unit: 'μg/m³', color: COLORS.blue },
        { key: 'pm10', name: 'PM10', unit: 'μg/m³', color: COLORS.purple },
        { key: 'so2', name: 'SO₂', unit: 'μg/m³', color: COLORS.orange },
        { key: 'no2', name: 'NO₂', unit: 'μg/m³', color: COLORS.pink },
        { key: 'co', name: 'CO', unit: 'mg/m³', color: COLORS.warning },
        { key: 'o3', name: 'O₃', unit: 'μg/m³', color: COLORS.green },
    ];

    const regions = data.map(d => d.region);

    // 每个污染物的柱状数据
    const seriesData = metrics.map(metric => ({
        name: metric.name,
        type: 'bar',
        data: data.map(row => ({
            value: row[metric.key],
            itemStyle: {
                color: metric.color,
                borderRadius: [2, 2, 0, 0],
            },
        })),
    }));

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: '#00d4ff',
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const regionName = params[0].name;
                let html = `<strong>${regionName}</strong><br/>`;
                params.forEach(p => {
                    const metric = metrics.find(m => m.name === p.seriesName);
                    if (p.data && metric) {
                        html += `${p.marker} ${metric.name}：${p.data.value} ${metric.unit}<br/>`;
                    }
                });
                return html;
            },
        },
        legend: {
            top: 10,
            left: 'center',
            textStyle: { color: '#e0f0ff', fontSize: 11 },
            itemWidth: 12,
            itemHeight: 12,
            itemGap: 10,
        },
        grid: {
            left: 55,
            right: 30,
            top: 40,
            bottom: 70,
        },
        xAxis: {
            type: 'category',
            data: regions,
            axisLabel: { color: '#8badc1', fontSize: 11, interval: 0, rotate: 20 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        series: seriesData,
    });

    window.addEventListener('resize', () => chart.resize());
}

// ─── 交互逻辑：筛选与图表更新 ───

/**
 * 省份筛选 → 更新省份 AQI 排名图表
 */
async function updateProvinceRankingChart() {
    const chart = initChart('chartProvinceRanking');
    if (!chart) return;

    const data = await fetchJSON('/api/province_ranking');
    const province = filterState.province;

    // 过滤数据
    let filtered = data;
    if (province) {
        filtered = data.filter(d => d.province === province);
    }

    // 从高到低排列
    const sorted = [...filtered].reverse();
    const provinces = sorted.map(d => d.province);
    const aqiValues = sorted.map(d => d.aqi);
    const barColors = sorted.map(d => getAqiColor(d.aqi));

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.primary,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = sorted[params[0].dataIndex];
                return `<strong>${d.province}</strong><br/>
                    AQI 均值：${d.aqi}<br/>
                    PM2.5 均值：${d.pm25} μg/m³<br/>
                    PM10 均值：${d.pm10} μg/m³<br/>
                    监测城市：${d.city_count} 个`;
            },
        },
        grid: {
            left: 80, right: 40, top: 10, bottom: 20,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        yAxis: {
            type: 'category',
            data: provinces,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        series: [{
            type: 'bar',
            data: aqiValues.map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(0, 212, 255, 0.2)' },
                        { offset: 1, color: barColors[i] },
                    ]),
                    borderRadius: [0, 4, 4, 0],
                },
            })),
            barWidth: '60%',
            label: {
                show: true,
                position: 'right',
                color: '#e0f0ff',
                fontSize: 11,
                formatter: '{c}',
            },
        }],
    });
}

/**
 * 污染物筛选 → 更新首要污染物分布图表
 */
async function updatePollutantDistChart() {
    const chart = initChart('chartPollutantDist');
    if (!chart) return;

    const data = await fetchJSON('/api/pollutant_distribution');
    const pollutant = filterState.pollutant;

    // 过滤数据
    let filtered = data;
    if (pollutant) {
        filtered = data.filter(d => d.pollutant === pollutant);
    }

    // 无匹配数据时返回空图表
    if (filtered.length === 0) {
        chart.setOption({
            title: { show: false },
            tooltip: { show: false },
            legend: { show: false },
            xAxis: { show: false },
            yAxis: { show: false },
            series: [],
        });
        return;
    }

    const names = filtered.map(d => d.pollutant);
    const values = filtered.map(d => d.count);
    const colors = [COLORS.primary, COLORS.success, COLORS.warning, COLORS.orange, COLORS.pink, COLORS.purple];

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: COLORS.primary,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = filtered[params[0].dataIndex];
                return `<strong>${d.pollutant}</strong><br/>
                    城市数：${d.count} 个<br/>
                    占比：${d.ratio}%`;
            },
        },
        grid: {
            left: 70, right: 30, top: 10, bottom: 30,
        },
        xAxis: {
            type: 'category',
            data: names,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        series: [{
            type: 'bar',
            data: values.map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: colors[i % colors.length] },
                        { offset: 1, color: 'rgba(0, 212, 255, 0.1)' },
                    ]),
                    borderRadius: [4, 4, 0, 0],
                },
            })),
            barWidth: '50%',
            label: {
                show: true,
                position: 'top',
                color: '#e0f0ff',
                fontSize: 11,
                formatter: '{c}个',
            },
        }],
    });
}

/**
 * 区域×污染物对比 → 筛选并更新图表
 */
async function updateRegionComparisonChart() {
    const chart = initChart('chartRegionComparison');
    if (!chart) return;

    const data = await fetchJSON('/api/region_pollutant_comparison');

    // 过滤区域
    let filteredData = data;
    if (filterState.province) {
        filteredData = data.filter(d => d.region === filterState.province);
    }

    // 过滤污染物指标
    let metrics = [
        { key: 'aqi', name: 'AQI', unit: '', color: COLORS.danger },
        { key: 'pm25', name: 'PM2.5', unit: 'μg/m³', color: COLORS.blue },
        { key: 'pm10', name: 'PM10', unit: 'μg/m³', color: COLORS.purple },
        { key: 'so2', name: 'SO₂', unit: 'μg/m³', color: COLORS.orange },
        { key: 'no2', name: 'NO₂', unit: 'μg/m³', color: COLORS.pink },
        { key: 'co', name: 'CO', unit: 'mg/m³', color: COLORS.warning },
        { key: 'o3', name: 'O₃', unit: 'μg/m³', color: COLORS.green },
    ];

    if (filterState.pollutant) {
        const metricKey = POLLUTANT_METRIC_MAP[filterState.pollutant];
        if (metricKey) {
            metrics = metrics.filter(m => m.key === metricKey);
        } else {
            // 污染物值不匹配，清空指标
            metrics = [];
        }
    }

    const regions = filteredData.map(d => d.region);

    // 每个污染物的柱状数据
    const seriesData = metrics.map(metric => ({
        name: metric.name,
        type: 'bar',
        data: filteredData.map(row => ({
            value: row[metric.key],
            itemStyle: {
                color: metric.color,
                borderRadius: [2, 2, 0, 0],
            },
        })),
    }));

    // 无数据时返回空图表
    if (regions.length === 0 || metrics.length === 0) {
        chart.setOption({
            title: { show: false },
            tooltip: { show: false },
            legend: { show: false },
            xAxis: { show: false },
            yAxis: { show: false },
            series: [],
        });
        return;
    }

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: '#00d4ff',
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const regionName = params[0].name;
                let html = `<strong>${regionName}</strong><br/>`;
                params.forEach(p => {
                    const metric = metrics.find(m => m.name === p.seriesName);
                    if (p.data && metric) {
                        html += `${p.marker} ${metric.name}：${p.data.value} ${metric.unit}<br/>`;
                    }
                });
                return html;
            },
        },
        legend: {
            top: 10,
            left: 'center',
            textStyle: { color: '#e0f0ff', fontSize: 11 },
            itemWidth: 12,
            itemHeight: 12,
            itemGap: 10,
        },
        grid: {
            left: 55,
            right: 30,
            top: 40,
            bottom: 70,
        },
        xAxis: {
            type: 'category',
            data: regions,
            axisLabel: { color: '#8badc1', fontSize: 11, interval: 0, rotate: 20 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        series: seriesData,
    });
}

/**
 * 城市排名切换：最差城市 ↔ 最优城市
 */
async function toggleRankMode(mode) {
    // 切换模式并更新图表
    filterState.rankMode = mode;

    // 切换按钮高亮状态
    const toggleBtn = document.getElementById('rankToggle');
    const toggleOtherBtn = document.getElementById('rankToggleOther');
    if (toggleBtn && toggleOtherBtn) {
        if (mode === 'worst') {
            toggleBtn.classList.add('btn-active');
            toggleOtherBtn.classList.remove('btn-active');
        } else {
            toggleBtn.classList.remove('btn-active');
            toggleOtherBtn.classList.add('btn-active');
        }
    }

    // 获取城市排名数据
    const cities = await fetchJSON(
        filterState.rankMode === 'worst'
            ? '/api/worst_cities'
            : '/api/best_cities'
    );

    // 最差：从低到高排列（最严重的在最上面）
    // 最优：从高到低排列（最优的在最上面）
    const sorted = filterState.rankMode === 'worst'
        ? [...cities].reverse()
        : [...cities].reverse(); // 最优也是按 AQI 从低到高排序，最上面是最优

    const chart = initChart('chartWorstBestCities');
    if (!chart) return;

    const citiesName = sorted.map(d => d.city);
    const aqiValues = sorted.map(d => d.aqi);

    // 根据 AQI 值生成颜色
    const barColors = sorted.map(d => getAqiColor(d.aqi));

    chart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(13, 33, 55, 0.95)',
            borderColor: filterState.rankMode === 'worst'
                ? COLORS.danger
                : COLORS.success,
            textStyle: { color: '#e0f0ff', fontSize: 12 },
            formatter: function (params) {
                const d = sorted[params[0].dataIndex];
                return `<strong>${d.city}</strong>（${d.province}）<br/>
                    AQI：${d.aqi} ${d.quality}<br/>
                    PM2.5：${d.pm25} μg/m³<br/>
                    PM10：${d.pm10} μg/m³<br/>
                    首要污染物：${d.pollution}`;
            },
        },
        grid: {
            left: 80, right: 40, top: 10, bottom: 10,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#8badc1', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
            axisLine: { show: false },
        },
        yAxis: {
            type: 'category',
            data: citiesName,
            axisLabel: { color: '#e0f0ff', fontSize: 11 },
            axisLine: { lineStyle: { color: '#1e3a5f' } },
            axisTick: { show: false },
        },
        series: [{
            type: 'bar',
            data: aqiValues.map(v => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: 'rgba(255, 107, 107, 0.15)' },
                        { offset: 1, color: v > 200 ? '#ff4757' : v > 150 ? '#ff6b6b' : '#e17055' },
                    ]),
                    borderRadius: [0, 4, 4, 0],
                },
            })),
            barWidth: '55%',
            label: {
                show: true,
                position: 'right',
                color: '#e0f0ff',
                fontSize: 11,
                fontWeight: 'bold',
                formatter: '{c}',
            },
        }],
    });
}

/**
 * 初始化交互筛选栏事件监听
 */
function initFilters() {
    const provinceSelect = document.getElementById('provinceFilter');
    const pollutantSelect = document.getElementById('pollutantFilter');
    const rankToggle = document.getElementById('rankToggle');
    const rankToggleOther = document.getElementById('rankToggleOther');

    // 省份筛选变化 → 更新省份排名和区域对比图表
    if (provinceSelect) {
        provinceSelect.addEventListener('change', () => {
            filterState.province = provinceSelect.value;
            updateProvinceRankingChart();
            updateRegionComparisonChart();
        });
    }

    // 污染物筛选变化 → 更新污染物分布和区域对比图表
    if (pollutantSelect) {
        pollutantSelect.addEventListener('change', () => {
            filterState.pollutant = pollutantSelect.value;
            updatePollutantDistChart();
            updateRegionComparisonChart();
        });
    }

    // 城市排名切换（最差 ↔ 最优）
    if (rankToggle) {
        rankToggle.addEventListener('click', () => {
            toggleRankMode('worst');
        });
    }

    if (rankToggleOther) {
        rankToggleOther.addEventListener('click', () => {
            toggleRankMode('best');
        });
    }
}

// ─── 启动入口 ───

async function init() {
    try {
        console.log('正在加载大屏数据...');
        console.log('初始化交互筛选栏...');

        // 初始化交互筛选栏事件监听
        initFilters();

        // 并行加载所有数据
        await Promise.all([
            renderSummary(),
            renderProvinceRanking(),
            renderQualityDist(),
            renderPollutantDist(),
            renderWorstCities(),
            renderBestCities(),
            renderPollutantsAverage(),
            renderRegionComparison(),
        ]);

        console.log('大屏加载完成 ✅');
    } catch (err) {
        console.error('大屏加载失败:', err);
        // 在页面上显示错误
        document.body.insertAdjacentHTML('beforeend',
            `<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
             background:#1a1a2e;color:#ff6b6b;padding:30px;border-radius:10px;
             border:1px solid #ff6b6b;z-index:9999;text-align:center;">
                <h3>数据加载失败</h3>
                <p>${err.message}</p>
                <p style="color:#8badc1;font-size:12px;">请确保 Flask 服务正在运行</p>
            </div>`
        );
    }
}

// 页面加载完成后启动
window.addEventListener('DOMContentLoaded', init);
