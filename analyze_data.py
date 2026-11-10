"""
analyze_data.py - 数据集分析脚本
用于分析 air_city_day.csv 的结构和质量
"""

import pandas as pd
import sys

def main():
    # 读取数据
    df = pd.read_csv(r"data\air_city_day.csv", parse_dates=["release_date", "update_time"])

    print("=" * 70)
    print("  数据集分析报告：城市环境空气质量日数据")
    print("=" * 70)

    # 1. 基本信息
    print(f"\n【1. 基本信息】")
    print(f"  总行数：{len(df)}")
    print(f"  总列数：{len(df.columns)}")
    print(f"  数据日期范围：{df['release_date'].min()} ~ {df['release_date'].max()}")

    # 2. 字段信息
    print(f"\n【2. 字段信息】")
    print(f"  {'字段名':<18} {'类型':<12} {'非空数':>6} {'缺失值':>6} {'唯一值':>6}")
    print(f"  {'-'*18} {'-'*12} {'-'*6} {'-'*6} {'-'*6}")
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        null_count = df[col].isna().sum()
        unique = df[col].nunique()
        print(f"  {col:<18} {dtype:<12} {non_null:>6} {null_count:>6} {unique:>6}")

    # 3. 城市和省份
    print(f"\n【3. 地理覆盖】")
    print(f"  省份数量：{df['province'].nunique()} 个")
    print(f"  城市数量：{df['city_label'].nunique()} 个")
    print(f"  省份列表：{', '.join(df['province'].unique()[:10])}...")

    # 4. 数值统计
    print(f"\n【4. 数值字段统计】")
    num_cols = ["PM25", "PM10", "SO2", "NO2", "CO", "O3_8h_24h", "AQI"]
    stats = df[num_cols].describe().round(2)
    print(stats.to_string())

    # 5. 空气质量等级分布
    print(f"\n【5. 空气质量等级分布】")
    quality_dist = df["quality"].value_counts()
    for level, count in quality_dist.items():
        pct = round(count / len(df) * 100, 1)
        print(f"  {level}: {count} 条 ({pct}%)")

    # 6. 首要污染物分布
    print(f"\n【6. 首要污染物分布】")
    poll_dist = df["pollutions"].value_counts(dropna=False)
    for pol, count in poll_dist.items():
        label = pol if pd.notna(pol) else "(空)"
        pct = round(count / len(df) * 100, 1)
        print(f"  {label}: {count} 条 ({pct}%)")

    # 7. 重复值检查
    dup_count = df.duplicated().sum()
    print(f"\n【7. 重复值】")
    print(f"  完全重复行数：{dup_count}")

    # 8. 异常值检查
    print(f"\n【8. 异常值检查】")
    print(f"  AQI < 0 的记录：{len(df[df['AQI'] < 0])} 条")
    print(f"  PM25 < 0 的记录：{len(df[df['PM25'] < 0])} 条")
    print(f"  PM10 < 0 的记录：{len(df[df['PM10'] < 0])} 条")
    print(f"  AQI > 500 的记录：{len(df[df['AQI'] > 500])} 条")
    print(f"  PM25 > 500 的记录：{len(df[df['PM25'] > 500])} 条")

    # 9. 日期分布
    print(f"\n【9. 日期分布】")
    date_counts = df.groupby(df["release_date"].dt.date).size()
    print(f"  有数据的天数：{len(date_counts)} 天")
    print(f"  每天记录数（均值）：{date_counts.mean():.1f}")
    print(f"  每天记录数（最小）：{date_counts.min()}")
    print(f"  每天记录数（最大）：{date_counts.max()}")

    # 10. AQI 分省排名
    print(f"\n【10. 省份 AQI 排名（均值从高到低）】")
    prov_aqi = df.groupby("province")["AQI"].mean().round(1).sort_values(ascending=False)
    for prov, aqi in prov_aqi.items():
        print(f"  {prov}: {aqi}")

    print("\n" + "=" * 70)
    print("  分析完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
