"""
data_processor.py - 数据处理模块

读取真实数据集 data/air_city_day.csv，使用 Pandas 进行清洗和统计分析，
为 Flask 后端提供数据接口。

数据来源：和鲸社区 - 城市环境空气质量日数据集
数据说明：2025年11月26日全国342个城市的空气质量监测数据（单日快照）
"""

import pandas as pd
import os

# 数据文件路径（相对于项目根目录）
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "air_city_day.csv")

# 全局数据缓存
_df_cache = None

# 污染物列名映射：兼容多种用户输入格式，统一映射到 DataFrame 实际列名
_POLLUTANT_COLS = {
    # PM2.5 / PM25
    "PM25": "PM25",
    "PM2.5": "PM25",
    # PM10
    "PM10": "PM10",
    # SO2 / SO₂
    "SO2": "SO2",
    "SO₂": "SO2",
    # NO2 / NO₂
    "NO2": "NO2",
    "NO₂": "NO2",
    # CO / CO×100 / CO*100
    "CO": "CO",
    "CO×100": "CO",
    "CO*100": "CO",
    # O3 / O₃ / O3_8h_24h / 臭氧
    "O3_8h_24h": "O3_8h_24h",
    "O3": "O3_8h_24h",
    "O₃": "O3_8h_24h",
    "O₃/臭氧": "O3_8h_24h",
}


def load_data():
    """
    加载并缓存数据集。

    处理步骤：
    1. 读取 CSV 文件
    2. 解析日期字段
    3. 填充 pollutions 空值为 "无"
    4. 返回清洗后的 DataFrame
    """
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')

    # 解析日期
    df["release_date"] = pd.to_datetime(df["release_date"], format="%d/%m/%Y")

    # 首要污染物空值填充为 "无"（空气质量为优时无首要污染物）
    df["pollutions"] = df["pollutions"].fillna("无")

    # 提取省份简称（去掉"省"/"市"/"自治区"等后缀，用于图表显示）
    def short_province(name):
        for suffix in ["壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "省", "市"]:
            if name.endswith(suffix):
                return name.replace(suffix, "")
        return name

    df["province_short"] = df["province"].apply(short_province)

    _df_cache = df
    return df


def get_data_date():
    """返回数据日期字符串"""
    df = load_data()
    return df["release_date"].dt.strftime("%Y年%m月%d日").iloc[0]


def get_summary():
    """
    核心指标汇总。

    返回:
        dict: 监测城市数、平均AQI、优良占比、最优城市、最差城市
    """
    df = load_data()

    total_cities = len(df)
    avg_aqi = round(df["AQI"].mean(), 1)

    # 优良城市数（AQI <= 100）
    good_count = len(df[df["AQI"] <= 100])
    good_ratio = round(good_count / total_cities * 100, 1)

    # 最优城市（AQI 最低）
    best_city = df.loc[df["AQI"].idxmin()]
    # 最差城市（AQI 最高）
    worst_city = df.loc[df["AQI"].idxmax()]

    # 平均 PM2.5
    avg_pm25 = round(df["PM25"].mean(), 1)

    return {
        "total_cities": int(total_cities),
        "avg_aqi": avg_aqi,
        "good_ratio": good_ratio,
        "avg_pm25": avg_pm25,
        "best_city": best_city["city_label"],
        "best_aqi": int(best_city["AQI"]),
        "worst_city": worst_city["city_label"],
        "worst_aqi": int(worst_city["AQI"]),
        "data_date": get_data_date(),
    }


def get_grade_level_cities(grade_level=None):
    """
    等级下钻：获取指定空气质量等级的城市明细数据。

    参数:
        grade_level: 可选，空气质量等级（如 "优"、"良" 等）。不传则返回全部等级的城市明细。

    返回:
        list[dict]: 城市明细列表，含 city_label、province、quality、aqi、pm25、pm10、so2、no2、pollution
        字段说明：city_label 城市名称、province 省份、quality 空气质量等级、aqi 空气质量指数、
        pm25/pm10 颗粒物浓度、so2/no2 二氧化硫/二氧化氮浓度、pollution 首要污染物
    """
    df = load_data()

    if grade_level:
        df = df[df["quality"] == grade_level]

    result = df[
        ["city_label", "province", "quality", "AQI", "PM25", "PM10", "SO2", "NO2", "pollutions"]
    ].copy()

    # 数值字段转换为整数（非空值），保持与接口返回口径一致
    for col in ["AQI", "PM25", "PM10", "SO2", "NO2"]:
        if col in result.columns:
            result[col] = result[col].apply(
                lambda x: int(x) if pd.notna(x) and x == x else x
            )

    return result.to_dict(orient="records")


def get_province_aqi_ranking(top_n=15):
    """
    省份 AQI 均值排名（从高到低）。

    返回:
        list[dict]: [{"province": "宁夏", "aqi": 218.6, "pm25": ...}, ...]
    """
    df = load_data()

    ranking = df.groupby("province_short").agg({
        "AQI": "mean",
        "PM25": "mean",
        "PM10": "mean",
        "city_label": "count",
    }).round(1)
    ranking.columns = ["aqi", "pm25", "pm10", "city_count"]
    ranking = ranking.sort_values("aqi", ascending=False).head(top_n)

    return [
        {"province": name, "aqi": float(row["aqi"]), "pm25": float(row["pm25"]),
         "pm10": float(row["pm10"]), "city_count": int(row["city_count"])}
        for name, row in ranking.iterrows()
    ]


def get_quality_distribution():
    """
    空气质量等级分布。

    返回:
        list[dict]: [{"level": "优", "count": 50, "ratio": 14.6}, ...]
    """
    df = load_data()
    total = len(df)

    # 按等级顺序排列
    level_order = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]
    dist = df["quality"].value_counts()

    result = []
    for level in level_order:
        count = int(dist.get(level, 0))
        if count > 0:
            result.append({
                "level": level,
                "count": count,
                "ratio": round(count / total * 100, 1),
            })
    return result


def get_worst_cities(top_n=10):
    """
    AQI 最高的前 N 个城市（污染最严重）。

    返回:
        list[dict]: [{"city": "某市", "aqi": 358, "quality": "严重污染", "province": "某省"}, ...]
    """
    df = load_data()
    top = df.nlargest(top_n, "AQI")

    return [
        {
            "city": row["city_label"],
            "province": row["province_short"],
            "aqi": int(row["AQI"]),
            "pm25": int(row["PM25"]),
            "pm10": int(row["PM10"]),
            "quality": row["quality"],
            "pollution": row["pollutions"],
        }
        for _, row in top.iterrows()
    ]


def get_best_cities(top_n=10):
    """
    AQI 最低的前 N 个城市（空气质量最好）。

    返回:
        list[dict]: [{"city": "某市", "aqi": 29, "quality": "优", "province": "某省"}, ...]
    """
    df = load_data()
    top = df.nsmallest(top_n, "AQI")

    return [
        {
            "city": row["city_label"],
            "province": row["province_short"],
            "aqi": int(row["AQI"]),
            "pm25": int(row["PM25"]),
            "pm10": int(row["PM10"]),
            "quality": row["quality"],
            "pollution": row["pollutions"],
        }
        for _, row in top.iterrows()
    ]


def get_pollutant_distribution():
    """
    首要污染物分布统计。

    返回:
        list[dict]: [{"pollutant": "PM10", "count": 214, "ratio": 62.6}, ...]
    """
    df = load_data()
    total = len(df)
    dist = df["pollutions"].value_counts()

    result = []
    for pol, count in dist.items():
        if pol != "无":  # 跳过无首要污染物的记录
            result.append({
                "pollutant": pol,
                "count": int(count),
                "ratio": round(count / total * 100, 1),
            })
    return result


def get_pollutants_average():
    """
    六项污染物全国均值对比。

    返回:
        dict: {"names": [...], "values": [...]}
    """
    df = load_data()

    # CO 的单位是 mg/m³，数值较小（0.2~2.1），乘 100 以便在图表中与其他指标对比显示
    pollutants = {
        "PM2.5": df["PM25"].mean(),
        "PM10": df["PM10"].mean(),
        "SO₂": df["SO2"].mean(),
        "NO₂": df["NO2"].mean(),
        "CO×100": df["CO"].mean() * 100,
        "O₃": df["O3_8h_24h"].mean(),
    }

    return {
        "names": list(pollutants.keys()),
        "values": [round(v, 1) for v in pollutants.values()],
    }


def get_region_comparison():
    """
    按地理区域对比各项污染物均值。

    将全国分为华北、东北、华东、华中、华南、西南、西北七大区域。

    返回:
        list[dict]: [{"region": "华北", "aqi": ..., "pm25": ..., "pm10": ...}, ...]
    """
    df = load_data()

    # 省份到区域的映射
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

    df = df.copy()
    df["region"] = df["province_short"].map(region_map).fillna("其他")

    region_stats = df.groupby("region").agg({
        "AQI": "mean",
        "PM25": "mean",
        "PM10": "mean",
        "city_label": "count",
    }).round(1)
    region_stats.columns = ["aqi", "pm25", "pm10", "city_count"]

    # 按 AQI 从高到低排序
    region_order = ["华北", "东北", "华东", "华中", "华南", "西南", "西北"]
    region_stats = region_stats.reindex([r for r in region_order if r in region_stats.index])

    return [
        {
            "region": name,
            "aqi": float(row["aqi"]),
            "pm25": float(row["pm25"]),
            "pm10": float(row["pm10"]),
            "city_count": int(row["city_count"]),
        }
        for name, row in region_stats.iterrows()
    ]


def get_region_pollutant_comparison(region=None, pollutants=None):
    """
    区域×污染物组合聚合。

    根据 region 和 pollutants 参数，将数据按地理区域分组，
    计算各区域空气质量相关指标的均值。

    返回:
        list[dict]: 每个区域一行，字段包括
        region, aqi, pm25, pm10, so2, no2, co, o3, city_count
        排序：按七大区域固定顺序（华北→东北→华东→华中→华南→西南→西北）

    说明:
        - CO 单位统一为 mg/m³ × 100，与全国均值口径一致，便于横向对比
        - aqi 为空气质量指数，与污染物浓度量纲不同，不适同叠加
    """
    df = load_data()

    # 设置区域列（与 get_region_comparison 逻辑一致）
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
    df = df.copy()
    df["region"] = df["province_short"].map(region_map).fillna("其他")

    # 区域过滤
    if region:
        df = df[df["region"] == region]

    # 污染物过滤
    if pollutants:
        for pol_name in pollutants:
            col = _POLLUTANT_COLS.get(pol_name)
            if col is None:
                raise ValueError(
                    f"未知污染物列名: {pol_name}，可用列名: {list(_POLLUTANT_COLS.keys())}"
                )
            df = df[df[col].notna()]

    # 聚合计算各区域指标
    agg_cols = {
        "AQI": "mean",
        "PM25": "mean",
        "PM10": "mean",
        "SO2": "mean",
        "NO2": "mean",
        "CO": "mean",
        "O3_8h_24h": "mean",
        "city_label": "count",
    }
    result = df.groupby("region").agg(agg_cols).round(1)

    # 重命名列
    result = result.rename(columns={
        "AQI": "aqi",
        "PM25": "pm25",
        "PM10": "pm10",
        "SO2": "so2",
        "NO2": "no2",
        "CO": "co",
        "O3_8h_24h": "o3",
        "city_label": "city_count",
    })

    # CO 单位统一为 mg/m³ × 100，保证与其他污染物量纲可比
    if "co" in result.columns:
        result["co"] = result["co"] * 100

    # 按七大区域固定顺序排序
    region_order = ["华北", "东北", "华东", "华中", "华南", "西南", "西北"]
    result = result.reindex([r for r in region_order if r in result.index.unique()])

    return [
        {
            "region": name,
            "aqi": float(row["aqi"]),
            "pm25": float(row["pm25"]),
            "pm10": float(row["pm10"]),
            "so2": float(row["so2"]),
            "no2": float(row["no2"]),
            "co": float(row["co"]),
            "o3": float(row["o3"]),
            "city_count": int(row["city_count"]),
        }
        for name, row in result.iterrows()
    ]


# 测试入口
if __name__ == "__main__":
    print("数据日期:", get_data_date())
    print("\n核心指标:", get_summary())
    print("\n省份排名（前5）:", get_province_aqi_ranking(5))
    print("\n质量等级分布:", get_quality_distribution())
    print("\n最差城市（前5）:", get_worst_cities(5))
    print("\n最优城市（前5）:", get_best_cities(5))
    print("\n首要污染物:", get_pollutant_distribution())
    print("\n污染物均值:", get_pollutants_average())
    print("\n区域对比:", get_region_comparison())
