const element = id => document.getElementById(id);
const format = value => value == null ? "--" : Number(value).toLocaleString("zh-CN", {maximumFractionDigits: 1});
let chart;

async function getJSON(path) {
  const response = await fetch(path, {signal: AbortSignal.timeout(6000)});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function refresh() {
  try {
    const [latest, history] = await Promise.all([
      getJSON("/api/latest"), getJSON(`/api/history?hours=${element("hours").value}`)
    ]);
    element("error").hidden = true;
    element("mode").textContent = latest.mode === "demo" ? "模拟数据" : "真实设备";
    element("status").textContent = latest.online ? (latest.mode === "demo" ? "模拟数据更新中" : "在线") : "离线 / 数据过期";
    const r = latest.reading;
    element("soil").textContent = format(r?.soil_percent);
    element("temperature").textContent = format(r?.temperature_c);
    element("humidity").textContent = format(r?.humidity_percent);
    element("light").textContent = format(r?.light_lux);
    element("raw").textContent = `ADC ${r?.soil_raw ?? "--"}${r && r.soil_percent == null ? " · 待标定" : ""}`;
    element("updated").textContent = r ? new Date(r.received_at).toLocaleString("zh-CN") : "尚未收到数据";
    element("sensor-errors").textContent = r ? (r.errors.length ? r.errors.join(" / ") : "采集状态正常") : "等待设备上报";
    const rows = history.readings;
    element("samples").textContent = `${rows.length} 条记录`;
    const chartReady = typeof Chart !== "undefined";
    element("chart-empty").hidden = chartReady && rows.some(row => row.soil_percent != null);
    element("chart-empty").textContent = !chartReady ? "图表资源未加载" : (rows.length ? "土壤传感器待标定" : "暂无记录");
    if (chartReady) {
      const data = {labels: rows.map(row => new Date(row.received_at).toLocaleTimeString("zh-CN")),
        datasets: [{label: "土壤相对湿度 %", data: rows.map(row => row.soil_percent), borderColor: "#348461", backgroundColor: "#34846115", borderWidth: 2, pointRadius: rows.length < 2 ? 3 : 0, fill: true, spanGaps: false}]};
      if (chart) { chart.data = data; chart.update("none"); }
      else chart = new Chart(element("history"), {type: "line", data, options: {responsive: true, maintainAspectRatio: false, animation: false, plugins: {legend: {display: false}}, scales: {y: {min: 0, max: 100}, x: {ticks: {maxTicksLimit: 6}, grid: {display: false}}}}});
    }
  } catch (error) {
    element("status").textContent = "连接中断";
    element("error").textContent = "无法获取最新数据，当前数值可能已过期。";
    element("error").hidden = false;
  }
}
element("hours").addEventListener("change", refresh);
async function poll() { await refresh(); setTimeout(poll, 10000); }
poll();
