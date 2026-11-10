"""
app.py - Flask 后端服务

提供数据 API 接口，供前端 ECharts 图表调用。
数据来源于 data_processor.py 处理的真实数据集。

数据来源：和鲸社区 - 城市环境空气质量日数据集
https://www.heywhale.com/home/dataset
"""

from flask import Flask, render_template, jsonify, request
from data_processor import (
    get_summary,
    get_province_aqi_ranking,
    get_quality_distribution,
    get_worst_cities,
    get_best_cities,
    get_pollutant_distribution,
    get_pollutants_average,
    get_region_comparison,
    get_region_pollutant_comparison,
    get_grade_level_cities,
)

app = Flask(__name__)


# ─── 页面路由 ───

@app.route("/")
def index():
    """渲染大屏主页"""
    return render_template("index.html")


# ─── 数据 API 接口 ───

@app.route("/api/summary")
def api_summary():
    """核心指标汇总"""
    return jsonify(get_summary())


@app.route("/api/province_ranking")
def api_province_ranking():
    """省份 AQI 排名"""
    return jsonify(get_province_aqi_ranking(top_n=15))


@app.route("/api/quality_distribution")
def api_quality_distribution():
    """空气质量等级分布"""
    return jsonify(get_quality_distribution())


@app.route("/api/worst_cities")
def api_worst_cities():
    """污染最重 Top 10 城市"""
    return jsonify(get_worst_cities(top_n=10))


@app.route("/api/best_cities")
def api_best_cities():
    """空气质量最优 Top 10 城市"""
    return jsonify(get_best_cities(top_n=10))


@app.route("/api/pollutant_distribution")
def api_pollutant_distribution():
    """首要污染物分布"""
    return jsonify(get_pollutant_distribution())


@app.route("/api/pollutants_average")
def api_pollutants_average():
    """六项污染物全国均值"""
    return jsonify(get_pollutants_average())


@app.route("/api/region_comparison")
def api_region_comparison():
    """七大区域对比"""
    return jsonify(get_region_comparison())


@app.route("/api/region_pollutant_comparison")
def api_region_pollutant_comparison():
    """区域×污染物组合聚合"""
    region = request.args.get("region")
    pollutants_param = request.args.get("pollutants", "")
    pollutants = [p.strip() for p in pollutants_param.split(",") if p.strip()]
    return jsonify(get_region_pollutant_comparison(region=region, pollutants=pollutants))


@app.route("/api/grade_level_cities")
def api_grade_level_cities():
    """等级下钻：按空气质量等级返回城市明细"""
    grade_level = request.args.get("grade_level")
    return jsonify(get_grade_level_cities(grade_level=grade_level))


# ─── 启动服务 ───

if __name__ == "__main__":
    print("=" * 60)
    print("  全国城市空气质量可视化大屏")
    print("  访问地址: http://127.0.0.1:5000")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    print()
    print("数据来源：和鲸社区 - 城市环境空气质量日数据集")
    print("数据日期：2025年11月26日（单日快照）")
    print("注意：本系统仅供课程学习和答辩展示使用。")
    print()
    app.run(debug=True, host="0.0.0.0", port=5000)
