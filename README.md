# Forme 云端账号、设计与订单平台

基于 `Mafubo-Mark/forme` 的提交 `81522d76856ddc6baeaf98ef68d3d063b9877063` 扩展。

本次版本增加邮箱／账号注册登录、按用户持久保存设计、视频与建模历史、报价后下单、付款凭证及管理员审核、物流更新、确认收货，以及中文管理平台。云端服务是 `cloud/app.py`，公开站点仍为 `dist/`。数据库使用 MySQL，用户密码使用 scrypt 哈希，视频与凭证放私有目录。

生产目标为 `https://my-robot-home.com/`，管理页面是 `/admin.html`，管理员认证按用户要求固定为 `forme / 123456`，服务端实现；账号可访问全部业务数据，密码容易猜测，应注意这一已知风险。

**当前交付状态：本地功能验收通过，部署包已上传至宝塔独立暂存目录。终端连接和证书协议确认尚待完成，生产数据库、服务、HTTPS 和自动备份还未部署。** 具体状态、宝塔查看步骤和备份方案见 `docs/本次部署状态与数据库说明.md`（交付 ZIP 内）。旧 `deploy/` 文档描述原型 SSH 隧道方案，仅作为历史背景；本次云端版本不依赖 Mac 在线。

## 代码结构

- `dist/`：主页、邮箱登录／注册、设计向导、用户设计／订单／配送／账户、管理员页面和本地 3D 资源。
- `cloud/app.py`：个人账户、会话、私有上传、建模事件、订单、付款审核和物流接口。
- `cloud/deploy.py`：目标网站备份、独立数据库、后端服务、站点 Nginx 和每日备份的部署脚本；运行前需先为目标站点准备有效 HTTPS 证书，并检查服务器实际配置。
- `cloud/backup.py`：MySQL 与私有资料备份，含 SHA-256 清单。备份包含连接配置，应保持私有。
- `cloud/test_app.py`：业务全流程、用户隔离、Cookie 和恢复验证。
- `database/schema.sql`：本次应用数据表 DDL 参考；实际初始化由 `app.py` 中 SQLAlchemy 元数据执行。

## 本地测试

Python 3.11 或更新版本：

```sh
python3 -m venv .venv
.venv/bin/pip install -r cloud/requirements.txt
.venv/bin/pip install httpx pytest
.venv/bin/pytest -q cloud/test_app.py
```

服务器只发布 `dist/`；不要把 `cloud/`、私有数据库、上传文件、生产连接配置或备份包放进公开网站目录。

原仓库不含自动视频重建／COLMAP／Blender 建模工作器。本版本完整持久保存提交、支持人工更新和上传实际模型；没有声称自动生成可打印、已适配的保护套。付款是凭证提交和人工审核，不是第三方自动扣款网关。
