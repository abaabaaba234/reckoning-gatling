# 清算节燃烧轨道加特林 / Reckoning Gatling

将《HELLDIVERS 2》的普通轨道加特林火力网替换为清算节燃烧版：使用游戏保留的原生燃烧弹序，在落点留下地火，保留当前弹体直击伤害、冷却和舰船升级。提供游戏内 MODS 启用开关与中文/英文选择；介绍在两种模式下均显示中英双语，玩法数值固定。

[下载 v0.1.1 安装包](https://github.com/abaabaaba234/reckoning-gatling/releases/tag/v0.1.1)

**v0.1.1**：新增本模组语言选择和始终显示的中英双语菜单介绍。沿用原有启用选项 ID 和配置；旧配置默认使用中文，原有启用状态保留。未改变燃烧弹序、直击伤害、冷却或舰船升级。

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

1. 关闭游戏，在 Arsenal 或 HD2MM 中导入 **ReckoningGatling_v0.1.1.zip**；只使用一个管理器。
2. 同时启用本模组、Bingus Shared Loader v18 和 ModOptionsMenu。
3. 按加载器说明设置优先级：Arsenal 默认优先级下将 Bingus Shared Loader 放在列表最底部；开启 first-mod priority 时放在最顶部。
4. 执行 **Purge / Deploy**，再启动游戏。

下载 Release 附件中的安装包。GitHub 自动生成的 Source code 压缩包是源码，需要自行构建后安装。

## MODS 开关与语言

进入 **Esc → MODS → 清算节燃烧轨道加特林 / Reckoning Gatling**，修改「启用 / Enable」或「Language」后应用。默认启用、默认中文，开关和语言状态会保存。语言选择只改变本模组标题和选项名；中文与英文介绍始终同时显示。切换语言后关闭并重新打开 Esc 菜单刷新文字。

开关只影响之后创建的火力网；已经开始的火力网会继续执行。关闭时恢复本模组修改且仍由本模组持有的弹序。卸载时关闭游戏，在管理器中停用或移除本模组，再执行 Purge / Deploy。

## 验证状态

**2026-10-10，用户对 v0.1.0 完成实机测试并反馈「测试完了没有问题」。** 这是旧版本用户报告的实机结果；v0.1.1 的菜单语言改动仅完成离线验证，尚未做新版游戏内界面实测。未提供独立的联机测试结论，联机兼容性仍未确认。

23 组离线检查通过，覆盖实际 Lua 运行、开关与语言持久化、旧配置兼容、中英介绍同显、真实菜单 API 注册与文字刷新、写入失败恢复、版本及冲突拦截、资源包依赖与归档检查。

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

构建产物：`dist/ReckoningGatling_v0.1.1.zip`。`dist/` 和自动生成的 `validation/` 不进入 Git。

可选环境检查，按实际安装位置替换路径：

```sh
python tools/verify_environment.py --game-dir "D:\steam\steamapps\common\Helldivers 2" --loader-dir "E:\code\hd2 mods\Bingus-Shared-Loader-v18"
```

## English

Replaces the ordinary Orbital Gatling Barrage with the native Festival of Reckoning incendiary sequence. Impacts leave ground fire while current direct-hit damage, cooldown and ship upgrades remain unchanged. The fixed sequence is `72, 254, 254, 254`: 60 rounds per salvo, four base salvos, a 0.045-second round interval and internal spread field `7`. That spread field is not documented here as a radius in metres. Fire uses the game's native Medium ground-fire template; no custom fire damage, duration or radius is added.

Version **0.1.1** adds a Chinese/English menu language choice. Both choices always show Chinese and English descriptions. Only the mod title and option labels follow the selected language. The existing enable option ID and saved state remain compatible; older configs use Chinese by default. Gameplay parameters are unchanged.

Requirements: **Bingus Shared Loader v18 / API 1**, **Bingus ModOptionsMenu API 1 / version 2 or newer**, and **Steam build 25480438 / EXE 1.8.46015.0**. Install the loader and menu separately; this ZIP contains neither dependency. Unsupported builds, unexpected data layouts and conflicting writes cause the mod to stop applying changes.

1. Close the game and import **ReckoningGatling_v0.1.1.zip** into Arsenal or HD2MM. Use one manager.
2. Enable this mod, Bingus Shared Loader v18 and ModOptionsMenu. Follow the loader's priority instructions: bottom in Arsenal's default order, top when first-mod priority is enabled.
3. Run **Purge / Deploy**, then start the game. Install the Release attachment; GitHub's automatic Source code archives require a local build.
4. Open **Esc → MODS → Reckoning Gatling**, change **Enable** or **Language**, and apply. Enabled and Chinese labels are the defaults. Close and reopen Esc after changing language. Both option descriptions remain bilingual.

The toggle affects newly created barrages; an existing barrage continues. Disabling restores fields still owned by the mod. To uninstall, close the game, disable or remove the mod in your manager, then run Purge / Deploy.

**Validation:** 23 offline groups pass, including execution of the actual Lua addon, the real menu API/options modules, language refresh, bilingual descriptions, persistence, old configs, restoration and archive checks. Native UI rendering and text services are mocked. The user reported successful gameplay with **v0.1.0 on 2026-10-10**; the **v0.1.1 menu update has not been tested in game**. Multiplayer compatibility remains unconfirmed. `VALIDATION.json` records offline results, and `USER_TEST_FEEDBACK.json` preserves the earlier user report.

The package retains native Gatling dependency references and adds native Orbital Napalm references for ground-fire assets. It does not redistribute the particle, audio or other game assets themselves. Logs and settings are under `%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\ReckoningGatling.log` and `ReckoningGatling.cfg`.

For source builds, install `requirements-dev.txt`, run `python tests/test_runtime.py`, then `python tools/build.py`. To include verification against an available ModOptionsMenu source, set `HD2_MOD_OPTIONS_MENU_SOURCE` to its extracted Lua file before running the build. Output: `dist/ReckoningGatling_v0.1.1.zip`.
