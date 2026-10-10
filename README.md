# 清算节燃烧轨道加特林 / Reckoning Gatling

将《HELLDIVERS 2》的普通轨道加特林火力网替换为清算节燃烧版：使用游戏保留的原生燃烧弹序，在落点留下地火，保留当前弹体直击伤害、冷却和舰船升级。提供游戏内 MODS 启用开关，数值固定。

[下载 v0.1.0 安装包](https://github.com/abaabaaba234/reckoning-gatling/releases/tag/v0.1.0)

## 效果

| 项目 | 配置 |
| --- | --- |
| 弹序 | 原生燃烧弹序 `72, 254, 254, 254` |
| 地火 | 原生燃烧弹落地爆炸使用 Medium 地火模板 |
| 每轮弹数 | 60 发 |
| 基础轮数 | 4 轮；保留舰船升级 |
| 单发间隔 | 0.045 秒 |
| 散布字段 | 游戏内部配置值 `7` |
| 弹体直击伤害、冷却 | 保留当前游戏数值 |

弹序里的数字是游戏内部弹体 ID；散布字段 `7` 不直接标作实际落点半径的米数。使用原生燃烧弹序及其效果，不自行调整伤害、地火持续时间或范围。

节日背景参考 [Wiki：Festival of Reckoning](https://helldivers.wiki.gg/wiki/Festival_of_Reckoning)，普通加特林参数参考 [Wiki：Orbital Gatling Barrage](https://helldivers.wiki.gg/wiki/Orbital_Gatling_Barrage)。具体弹序与字段依据见 [原生数据夹具](tests/fixtures/native_2025.json)。该实现恢复节日行为并保留当前游戏伤害，不宣称全部数值与 2025 年历史版本逐项一致。

## 前置与支持版本

- **Bingus Shared Loader v18 / API 1**：通过 addon 发现接口加载本模组。
- **Bingus ModOptionsMenu API 1 / version 2 或更新版本**：提供 MODS 菜单开关。
- **Steam build 25480438 / 游戏 EXE 1.8.46015.0**。

前置需要另行安装，Release 安装包不包含加载器或菜单。运行时检查游戏版本、代码特征、数据布局及目标基线；不匹配或发现写入冲突时停止应用并记录原因。

## 安装

1. 关闭游戏，在 Arsenal 或 HD2MM 中导入 **ReckoningGatling_v0.1.0.zip**；只使用一个管理器。
2. 同时启用本模组、Bingus Shared Loader v18 和 ModOptionsMenu。
3. 按加载器说明设置优先级：Arsenal 默认优先级下将 Bingus Shared Loader 放在列表最底部；开启 first-mod priority 时放在最顶部。
4. 执行 **Purge / Deploy**，再启动游戏。

下载 Release 附件中的安装包。GitHub 自动生成的 Source code 压缩包是源码，需要自行构建后安装。

## MODS 开关

进入 **Esc → MODS → 清算节燃烧轨道加特林**，修改「启用」后应用。默认启用，开关状态会保存。

开关只影响之后创建的火力网；已经开始的火力网会继续执行。关闭时恢复本模组修改且仍由本模组持有的弹序。卸载时关闭游戏，在管理器中停用或移除本模组，再执行 Purge / Deploy。

## 验证状态

**2026-10-10，用户完成实机测试并反馈「测试完了没有问题」。** 这是用户报告的实机结果；未提供独立的联机测试结论，联机兼容性仍未确认。

23 组离线检查通过，覆盖实际 Lua 运行、开关与持久化、菜单 API 注册和应用、写入失败恢复、版本及冲突拦截、资源包依赖与归档检查。

安装包内的 `VALIDATION.json` 记录离线验证，其 `ingame_tested: false` 表示该自动化检查未执行游戏实测。后续实机反馈单独记录在 `USER_TEST_FEEDBACK.json`，避免把离线检查写成实机证明。

本模组保留加特林资源包的全部原生依赖，并预载原生轨道凝固汽油战备的资源引用，以覆盖地火所需资源；不打包粒子、音频等游戏资产本体。

日志与配置：

```text
%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\ReckoningGatling.log
%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\ReckoningGatling.cfg
```

## 源码与构建

- [src/core.lua](src/core.lua)：v18 addon 入口、运行时弹序替换和菜单。
- [tests/fixtures/native_2025.json](tests/fixtures/native_2025.json)：原生弹序、弹体及爆炸记录。
- [tests/fixtures/packages_build25480438.json](tests/fixtures/packages_build25480438.json)：当前安装提取的资源包依赖引用。
- [tests/fixtures/user_test_feedback.json](tests/fixtures/user_test_feedback.json)：后续实机反馈。
- [tools/build.py](tools/build.py)：离线检查与安装包构建。
- [tools/verify_environment.py](tools/verify_environment.py)：当前游戏与本地 v18 加载器指纹检查。

运行时字段研究使用 Filediver v0.7.57 的解码参考；资源依赖由 Filediver CLI v0.7.55 从当前安装提取。解码参考与当前安装尚未逐值证明等价，因此保留运行时基线检查。

```sh
python -m pip install -r requirements-dev.txt
python tests/test_runtime.py
python tools/build.py
```

构建产物：`dist/ReckoningGatling_v0.1.0.zip`。`dist/` 和自动生成的 `validation/` 不进入 Git。

可选环境检查，按实际安装位置替换路径：

```sh
python tools/verify_environment.py --game-dir "D:\steam\steamapps\common\Helldivers 2" --loader-dir "E:\code\hd2 mods\Bingus-Shared-Loader-v18"
```
