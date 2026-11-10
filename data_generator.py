"""
data_generator.py - 城市环境与空气质量模拟数据生成器

本模块使用 Pandas 生成模拟数据，供大屏展示使用。
重要声明：本数据为教学模拟数据，基于中国城市空气质量的普遍规律生成，
不代表任何真实城市的实际空气质量数据。仅供课程学习和答辩展示使用。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# 设置随机种子以保证可重复性
np.random.seed(42)
random.seed(42)

# 城市基础信息
CITIES = {
    "北京": {"region": "华北", "base_aqi": 95, "base_temp": 13},
    "上海": {"region": "华东", "base_aqi": 70, "base_temp": 16},
    "广州": {"region": "华南", "base_aqi": 60, "base_temp": 22},
    "深圳": {"region": "华南", "base_aqi": 50, "base_temp": 23},
    "成都": {"region": "西南", "base_aqi": 80, "base_temp": 16},
    "杭州": {"region": "华东", "base_aqi": 65, "base_temp": 17},
    "武汉": {"region": "华中", "base_aqi": 75, "base_temp": 17},
    "南京": {"region": "华东", "base_aqi": 68, "base_temp": 16},
    "重庆": {"region": "西南", "base_aqi": 72, "base_temp": 18},
    "西安": {"region": "西北", "base_aqi": 88, "base_temp": 14},
    "天津": {"region": "华北", "base_aqi": 85, "base_temp": 13},
    "苏州": {"region": "华东", "base_aqi": 62, "base_temp": 16},
    "郑州": {"region": "华中", "base_aqi": 90, "base_temp": 15},
    "长沙": {"region": "华中", "base_aqi": 70, "base_temp": 18},
    "青岛": {"region": "华东", "base_aqi": 55, "base_temp": 13},
    "大连": {"region": "东北", "base_aqi": 52, "base_temp": 11},
    "厦门": {"region": "华南", "base_aqi": 45, "base_temp": 21},
    "昆明": {"region": "西南", "base_aqi": 40, "base_temp": 16},
    "沈阳": {"region": "东北", "base_aqi": 78, "base_temp": 9},
    "哈尔滨": {"region": "东北", "base_aqi": 82, "base_temp": 5},
}

# 月份对应的季节温度修正（冬季低、夏季高）
MONTH_TEMP_OFFSET = {
    1: -12, 2: -9, 3: -2, 4: 6, 5: 12, 6: 17,
    7: 20, 8: 19, 9: 13, 10: 5, 11: -3, 12: -10
}

# 月份对应的 AQI 修正（冬季供暖期 AQI 偏高）
MONTH_AQI_OFFSET = {
    1: 35, 2: 25, 3: 5, 4: -10, 5: -15, 6: -10,
    7: -5, 8: -5, 9: 0, 10: 5, 11: 20, 12: 30
}


def generate_daily_data(city, year=2024, days=365):
    """
    为单个城市生成一年的逐日空气质量数据。

    参数:
        city: 城市名称
        year: 年份，默认 2024
        days: 天数，默认 365

    返回:
        DataFrame，包含日期、AQI、PM2.5、PM10、温度、湿度、风速、空气质量等级
    """
    info = CITIES[city]
    start_date = datetime(year, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(days)]

    records = []
    for date in dates:
        month = date.month
        day_of_year = date.timetuple().tm_yday

        # 基础 AQI + 月份修正 + 随机波动
        aqi_base = info["base_aqi"] + MONTH_AQI_OFFSET[month]
        aqi = max(10, int(aqi_base + np.random.normal(0, 15)))
        aqi = min(aqi, 500)  # AQI 上限

        # PM2.5 与 AQI 正相关，加入随机噪声
        pm25 = max(5, int(aqi * 0.65 + np.random.normal(0, 8)))

        # PM10 通常比 PM2.5 高
        pm10 = max(pm25 + 5, int(pm25 * 1.4 + np.random.normal(0, 10)))

        # 温度：基础温度 + 月份修正 + 随机波动
        temp = round(info["base_temp"] + MONTH_TEMP_OFFSET[month] + np.random.normal(0, 3), 1)

        # 湿度：南方城市基础更高，夏季更高
        base_humidity = 60 if info["region"] in ["华南", "华东"] else 45
        humidity = int(base_humidity + MONTH_TEMP_OFFSET[month] * 0.8 + np.random.normal(0, 8))
        humidity = max(15, min(98, humidity))

        # 风速：随机生成，冬季稍大
        wind_speed = round(max(0.5, 3.0 + np.random.normal(0, 1.5) + (2 if month in [12, 1, 2] else 0)), 1)

        # 根据 AQI 判断空气质量等级
        level = get_aqi_level(aqi)

        records.append({
            "日期": date.strftime("%Y-%m-%d"),
            "月份": month,
            "城市": city,
            "区域": info["region"],
            "AQI": aqi,
            "PM2.5": pm25,
            "PM10": pm10,
            "温度": temp,
            "湿度": humidity,
            "风速": wind_speed,
            "空气质量等级": level,
        })

    return pd.DataFrame(records)


def get_aqi_level(aqi):
    """根据 AQI 值返回空气质量等级"""
    if aqi <= 50:
        return "优"
    elif aqi <= 100:
        return "良"
    elif aqi <= 150:
        return "轻度污染"
    elif aqi <= 200:
        return "中度污染"
    elif aqi <= 300:
        return "重度污染"
    else:
        return "严重污染"


def generate_all_data():
    """
    生成所有城市的模拟数据并合并。

    返回:
        合并后的 DataFrame
    """
    frames = []
    for city in CITIES:
        df = generate_daily_data(city)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ─── 以下是供 Flask 调用的数据查询函数 ───

# 预生成数据缓存
_data_cache = None


def _get_data():
    """懒加载数据缓存"""
    global _data_cache
    if _data_cache is None:
        _data_cache = generate_all_data()
    return _data_cache


def get_summary(month=None):
    """
    获取汇总统计数据。

    参数:
        month: 可选，指定月份（1-12）。不传则取全年数据。

    返回:
        dict，包含城市数量、平均AQI、平均PM2.5、优良天数占比、平均温度
    """
    df = _get_data()
    if month:
        df = df[df["月份"] == month]

    total_cities = df["城市"].nunique()
    avg_aqi = round(df["AQI"].mean(), 1)
    avg_pm25 = round(df["PM2.5"].mean(), 1)
    good_days = len(df[df["AQI"] <= 100])
    total_days = len(df)
    good_ratio = round(good_days / total_days * 100, 1) if total_days > 0 else 0
    avg_temp = round(df["温度"].mean(), 1)

    return {
        "城市数量": total_cities,
        "平均AQI": avg_aqi,
        "平均PM2.5": avg_pm25,
        "优良天数占比": good_ratio,
        "平均温度": avg_temp,
    }


def get_city_aqi_ranking(month=None):
    """
    获取城市 AQI 排行榜（从高到低）。

    返回:
        list[dict]，每个元素包含 城市 和 AQI
    """
    df = _get_data()
    if month:
        df = df[df["月份"] == month]

    ranking = df.groupby("城市")["AQI"].mean().round(1).sort_values(ascending=False)
    return [{"城市": city, "AQI": float(aqi)} for city, aqi in ranking.items()]


def get_monthly_trend(city=None):
    """
    获取每月 AQI 和 PM2.5 趋势数据。

    参数:
        city: 可选，指定城市。不传则取全国平均。

    返回:
        dict，包含月份列表、AQI 列表、PM2.5 列表
    """
    df = _get_data()
    if city:
        df = df[df["城市"] == city]

    monthly = df.groupby("月份").agg({"AQI": "mean", "PM2.5": "mean"}).round(1)
    return {
        "月份": [f"{int(m)}月" for m in monthly.index],
        "AQI": monthly["AQI"].tolist(),
        "PM2.5": monthly["PM2.5"].tolist(),
    }


def get_monthly_temp_trend():
    """
    获取全国月均温度趋势。

    返回:
        dict，包含月份列表和平均温度列表
    """
    df = _get_data()
    monthly = df.groupby("月份")["温度"].mean().round(1)
    return {
        "月份": [f"{int(m)}月" for m in monthly.index],
        "温度": monthly.tolist(),
    }


def get_air_quality_distribution(month=None):
    """
    获取各空气质量等级的天数分布。

    返回:
        list[dict]，每个元素包含 等级 和 天数
    """
    df = _get_data()
    if month:
        df = df[df["月份"] == month]

    dist = df["空气质量等级"].value_counts()
    # 按等级顺序排列
    level_order = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]
    result = []
    for level in level_order:
        count = int(dist.get(level, 0))
        if count > 0:
            result.append({"等级": level, "天数": count})
    return result


def get_city_comparison():
    """
    获取各城市的 AQI、PM2.5、温度对比数据（用于雷达图或多维对比）。

    返回:
        list[dict]，每个元素包含城市名和各项指标
    """
    df = _get_data()
    summary = df.groupby("城市").agg({
        "AQI": "mean",
        "PM2.5": "mean",
        "温度": "mean",
        "湿度": "mean",
        "风速": "mean",
    }).round(1)

    result = []
    for city, row in summary.iterrows():
        result.append({
            "城市": city,
            "AQI": float(row["AQI"]),
            "PM2.5": float(row["PM2.5"]),
            "温度": float(row["温度"]),
            "湿度": float(row["湿度"]),
            "风速": float(row["风速"]),
        })
    return result


def get_top5_best_worst(month=None):
    """
    获取空气质量最好和最差的前5个城市。

    返回:
        dict，包含 best（AQI最低的5个城市）和 worst（AQI最高的5个城市）
    """
    df = _get_data()
    if month:
        df = df[df["月份"] == month]

    ranking = df.groupby("城市")["AQI"].mean().round(1).sort_values()
    best = [{"城市": city, "AQI": float(aqi)} for city, aqi in ranking.head(5).items()]
    worst = [{"城市": city, "AQI": float(aqi)} for city, aqi in ranking.tail(5).iloc[::-1].items()]

    return {"best": best, "worst": worst}


# 测试入口：直接运行时打印数据样例
if __name__ == "__main__":
    data = generate_all_data()
    print("=" * 60)
    print("数据总览")
    print("=" * 60)
    print(f"数据总量：{len(data)} 条记录")
    print(f"城市数量：{data['城市'].nunique()} 个")
    print(f"时间范围：{data['日期'].min()} ~ {data['日期'].max()}")
    print()
    print("数据样例（前 10 行）:")
    print(data.head(10).to_string(index=False))
    print()
    print("汇总统计:")
    print(get_summary())
    print()
    print("城市 AQI 排行榜（前 10）:")
    for item in get_city_aqi_ranking()[:10]:
        print(f"  {item['城市']}: {item['AQI']}")
