# 智能植物养护系统

一盆植物的局域网养护原型。团队 4 人，软件侧 3 人、硬件侧 2 人，负责人跨两侧。

当前已提供：FastAPI + SQLite、手机 Web、模拟数据、MQTT 只读采集入口、ESP32 传感器采集程序。水泵控制尚未实现，接口保持锁定；实物验收和 7 天试运行尚未完成。模拟演示不代表实物已通过测试。

## 在电脑启动

需要 Python 3.10 及以上。在项目根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn gateway.app:app --host 0.0.0.0 --port 8000
```

打开 <http://localhost:8000>。同一局域网的手机访问 `http://电脑局域网IP:8000`；仅对可信局域网开放端口。接口文档在 `/docs`。模拟数据每 10 秒生成一次并持久保存，默认数据库为 `data/demo.sqlite3`，浇水不会执行。

测试：

```powershell
.venv\Scripts\python -m pytest -q
```

Linux 对应使用 `.venv/bin/python`。真实设备部署、配置和接线前检查见 [硬件与部署.md](docs/硬件与部署.md)。

## 团队入口

- [执行计划](大创项目说明/执行计划.md)：16 个有效工作周、分工、第一周任务。
- [接口约定](docs/接口约定.md)：数据接口、MQTT 消息、后续控制验收条件。
- [验收记录](docs/验收记录.md)：逐项记录实际结果，不能预先勾选。

第一周先做开机和模拟页面；第 3–6 周再联通传感器。摄像头、AI、语音和微信小程序后置。
