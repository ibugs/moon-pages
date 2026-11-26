# MOON 策略业绩

GitHub Pages 纯静态页面，沿用现有 MOON 页面的布局和统计口径。

- 策略：全天候2.0、全天候1.0、DZI、ATLAS。
- 范围：最近10年、5年、3年、1年、今年。
- 内容：净值、夏普、年化收益、所选区间回撤、月度和年度收益、DZI 与 ATLAS 最近三个有成交日期的记录。
- 网页只读取同一站点的 `data/moon.json`，不请求原服务器；无需登录。

## 数据更新

生产服务器复用现有 `dashboard_server.py`、`moon_dashboard.py` 中的统计函数，导出展示字段。每五分钟更新一次 JSON、推送 GitHub，随后由 Actions 发布 `site/`。页面每60秒检查新数据。实际可见时间包括发布和缓存延迟。

导出失败时保留上一份 JSON；不会推送不完整的数据。导出脚本不会修改原网站、登录数据库或交易数据。发布文件不含账户编号、内部订单号、访问凭据或原始服务器配置。

手工导出：

```bash
python scripts/export_snapshot.py \
  --dashboard-dir /path/to/Dashboard_Server \
  --output-dir site/data
```

在服务器专用的本仓库副本中配置 `MOON_DASHBOARD_DIR`、`MOON_PYTHON`，运行：

```bash
bash scripts/publish_snapshot.sh
```

推送使用服务器已有的 GitHub SSH 身份验证，不在仓库保存密钥。

## Pages 设置

仓库 Settings → Pages → Build and deployment → Source 选择 GitHub Actions。
工作流只发布 `site/`，不会发布导出工具和服务器配置。

## JSON 结构

`schema_version` 为格式版本，`generated_at` 为北京时间导出时间，`periods` 包含五档范围的展示数据。各策略的 `equity_curve`、`monthly_returns`、`annual_returns`、`risk_metrics`、`recent_trades` 均由生产统计函数产生。

回撤为当前净值相对所选区间截至当时最高净值的变化；副图最低点与顶部最大回撤一致。近期成交的平仓盈亏沿用原系统匹配结果，未扣手续费。

本网站及其 JSON 为公开数据，请仅导出准备公开的展示内容。

## 本地查看

```bash
python -m http.server 8765 --directory site --bind 127.0.0.1
```

打开 `http://127.0.0.1:8765/`。
