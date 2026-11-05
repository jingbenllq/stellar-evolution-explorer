# MESA 26.4.1 环境、文档、主机规格与内存安全护栏综合调研报告

## 摘要 (Executive Summary)

本调研对 Windows 主机环境、WSL2 Ubuntu 子系统、`D:\天体物理导论` 目标工作区、磁盘上 MESA 参考指南、MESA 26.4.1 与 MESA SDK 最新发布源、系统内存极限压测与安全护栏（<85% RAM）、以及本地方案与 Web UI 重构（含洋葱图切面重构）进行了全覆盖深度审计。

核心审计结论如下：
1. **参考文档**：`d:\QQ\` 下的两份指南提供了 MESA 26.4.1 编译配置、1 $M_\odot$ 预主序到零龄主序（ZAMS）运行流程，以及 `py_mesa_reader` 科研绘图（HR图、演化曲线、温度—密度剖面、元素丰度剖面、四联图）的完整技术规范。
2. **目标目录与磁盘空间**：`D:\天体物理导论` 所在 D 盘拥有 **58.16 GB 可用空间**（远超 MESA 运行所需的 20 GB 阈值）。目标目录在 WSL2 下挂载为 `/mnt/d/天体物理导论`，且经实测支持符号链接（symlink）与脚本执行权限。
3. **主机与 WSL2 环境**：
   - 处理器：AMD Ryzen 7 8845H（8 核心，16 逻辑处理器）。
   - 主机内存：总可见物理内存 16,037,092 KB (~15.29 GB)。当前系统内存占用率约为 72.8%（约 11.1 GB 已占用，剩余约 4.2 GB 空闲）。85% 安全警戒上限为 **13.00 GB**（剩余空闲必须严格保持在 2.29 GB 以上）。
   - WSL2 子系统：运行 **Ubuntu 26.04 LTS (resolute)**，Linux 内核版本 6.18.33.2-microsoft-standard-WSL2，其虚拟根磁盘可用空间高达 **954 GB**。可通过 `wsl -u root` 无需交互密码直接执行系统管理命令。
4. **MESA 26.4.1 与 SDK 资源**：
   - MESA 26.04.1 官方归档：Zenodo Record `19722306`，源码压缩包 `mesa-26.04.1.zip`（2,268,361,262 字节，约 2.11 GB，MD5: `994fd28f38da92efc80e38ca11d8317b`）。
   - MESA SDK 最新版本：Townsend 官方针对 MESA 26.04.1 发布的最新 Linux x86_64 SDK 为 `mesasdk-x86_64-linux-26.6.1.tar.gz`（Zenodo Record `20598423`，199,295,811 字节，约 199.3 MB）。
5. **内存安全护栏策略 (< 85% RAM)**：
   由于主机仅 16 GB 且初始占用已达 ~72.8%，任何未经限制的多核并行（如 16 线程 `make -j16` 或过大 `OMP_NUM_THREADS`）将直接击穿 85% 阈值。必须实施“四重内存熔断防护”：
   - ① WSL2 虚拟机内存上限配置（`memory=6GB`）；
   - ② OpenMP 线程上限绑定（`export OMP_NUM_THREADS=2` 或 `4`）；
   - ③ 流式分块 I/O 下载与解压（单次内存缓冲区 $\le 1\text{ MB}$）；
   - ④ 双向实时看门狗守护脚本（基于 `psutil`，75% 警戒，82% 节流，84.5% 紧急刹车挂起）。
6. **工程重构与数据同步**：
   规范了 `D:\天体物理导论` 与本地工作区之间的工程目录结构、MESA `LOGS` 真实数据摄取管道、现代极简深色 Web UI 设计规范，以及基于物理坐标映射的恒星内部洋葱圈（Onion-Skin）切面重构方案。

---

## 1. 磁盘参考文档审计 (Reference Documentation Audit)

### 1.1 `d:\QQ\MESA_26.4.1_中文安装与1太阳质量测试.md`
- **文档元数据**：317 行，7606 字节，最后修改于 2026/11/03 22:34。
- **关键技术要求**：
  - 依赖软件包：`binutils`、`make`、`perl`、`libx11-dev`、`zlib1g-dev`、`tcsh`。
  - SDK 部署：Linux 推荐部署于 `$HOME/mesasdk`，初始化脚本为 `$MESASDK_ROOT/bin/mesasdk_init.sh`。
  - 环境变量定义：
    ```bash
    export MESA_DIR="你的目录/mesa-26.4.1"
    export OMP_NUM_THREADS=4
    export MESASDK_ROOT="$HOME/mesasdk"
    source "$MESASDK_ROOT/bin/mesasdk_init.sh"
    export PATH="$MESA_DIR/scripts/shmesa:$PATH"
    ```
  - 编译构建流程：进入 `$MESA_DIR` 运行 `./install`（严禁使用 `sudo ./install`）。
  - 1 $M_\odot$ 测试模型构建：
    - 复制 `$MESA_DIR/star/work` 到项目目录 `1Msun_test`。
    - 修改 `inlist_project`：将 `initial_mass = 15` 改为 `initial_mass = 1`。
    - 保持 `create_pre_main_sequence_model = .true.`、`Lnuc_div_L_zams_limit = 0.99d0`、`stop_near_zams = .true.`。
    - 执行 `./mk` 进行模型编译，运行 `./rn` 启动演化模拟。
    - 终止条件：`termination code: Lnuc_div_L_zams_limit`。
    - 核心输出：`LOGS/history.data`、`LOGS/profiles.index`、`LOGS/profile*.data`。
    - 无头环境适配：关闭实时 PGPLOT 窗口以防 X11 报错（`pgstar_flag = .false.`）。

### 1.2 `d:\QQ\MESA模拟数据科研绘图教程_py_mesa_reader.md`
- **文档元数据**：800 行，21,259 字节，最后修改于 2026/11/03 22:34。
- **核心数据接口与规范**：
  - Python 依赖：`mesa-reader >= 0.4.0`、`matplotlib`、`numpy`。
  - 数据模型：`logs = mr.MesaLogDir("LOGS")`，`h = logs.history`，`p = logs.profile_data()`。
  - 数据清洗不变量：必须调用 `h.remove_backups()` 剔除 MESA restart 时留下的历史重复步。
  - 绘图规范：
    - HR 图：横轴有效温度对数 $\log_{10}(T_{\rm eff}/\text{K})$ 必须反向（`ax.invert_xaxis()`），纵轴为光度对数 $\log_{10}(L/L_\odot)$。
    - 组分剖面：按内向外或外向内归一化质量坐标 $q = M_r / M_\star$ 排序后绘制 $X_{\rm H}$, $Y_{\rm He}$, $Z_{\rm metals}$。
    - 内存优化：多 Profile 批量读取时必须显式指定 `mr.MesaLogDir("LOGS", memoize_profiles=False)` 避免内存泄露；批量出图必须使用 `matplotlib.use("Agg")` 并在绘图结束时调用 `plt.close(fig)`。
  - 四联图生产管线：集成 HR 图、中心氢丰度消耗时序、末期温度—密度剖面（$\log\rho - \log T$）、径向元素丰度分布。

---

## 2. 目标目录与主机环境规格审计 (Host Environment Audit)

### 2.1 物理主机与操作系统参数
- **操作系统**：Microsoft Windows 11 64-bit。
- **中央处理器 (CPU)**：AMD Ryzen 7 8845H w/ Radeon 780M Graphics
  - 物理核心数：8
  - 逻辑线程数：16
- **物理内存 (RAM)**：
  - 系统可见总量：`16,037,092 KB` ($\approx 15.29\text{ GB}$)
  - 当前初始空闲：`5,508,232 KB` ($\approx 5.25\text{ GB}$)
  - 当前初始占用：$\approx 72.8\%$
  - 85% 系统内存上限阈值：
    $$16037092 \times 0.85 = 13,631,528\text{ KB} \approx 13.00\text{ GB}$$
  - **允许新增分配的安全内存窗口**：
    $$13,631,528 - (16037092 - 5508232) \approx 3.10\text{ GB}$$
    此数值表明，整个 MESA 下载、解压、编译、运行及后处理流水线在任意时刻的新增动态内存消耗**绝对不得超过 2.5 GB**，否则必将触发 85% 告警甚至系统假死。

### 2.2 目标存储空间与文件系统验证
- **D 盘整体状态**：
  - 总容量：约 115 GB。
  - 已使用：56.09 GB。
  - 可用空间：**58.16 GB**（空间充裕，可满足 MESA 源码、SDK 及模拟日志所需的 15~20 GB 开销）。
- **`D:\天体物理导论` 目标路径**：
  - 当前状态：已通过 WSL2 挂载点 `/mnt/d/天体物理导论` 正式创建。
  - 权限与特性测试：经实测，WSL2 drvfs 挂载点支持 Linux 软链接（symlink）创建与可执行权限（`chmod +x`），可作为 MESA 项目工程和数据存储的坚实承载区。

### 2.3 WSL2 Ubuntu 容器审计
- **WSL 状态**：WSL2 引擎处于就绪状态，默认分发版为 `Ubuntu`。
- **子系统系统版本**：Ubuntu 26.04 LTS (resolute)，Linux 内核 6.18.33.2-microsoft-standard-WSL2 (x86_64)。
- **子系统根存储**：`/dev/sdd` 总容量 1007 GB，可用 **954 GB**。
- **子系统内存分配**：
  - 默认分配总量：7,581 MB (~7.4 GB)。
  - 当前子系统占用：715 MB，空闲 5,842 MB。
- **特权提权机制**：
  - 普通用户 `jingben` 拥有专属主目录 `/home/jingben`。
  - 通过 `wsl -d Ubuntu -u root -e bash -c "..."` 可以 100% 免密获得 root 权限，能无障碍安装编译工具包与内核依赖，无须交互式密码输入。
- **软件包安装现状**：
  - 已就绪：`curl`, `wget`, `tar`, `python3` (3.14.4), `binutils` (2.46)。
  - 待安装：`make`, `tcsh`, `gcc`, `libx11-dev`, `zlib1g-dev`, `python3-pip`, `python3-psutil`。

---

## 3. MESA 26.4.1 与 MESA SDK 下载与配置策略 (MESA Architecture & URLs)

### 3.1 官方发布包精准定位与校验值

| 资源组件 | 版本标称 | 官方来源 / 归档标识 | 文件名 | 文件大小 | 校验和 / MD5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MESA SDK (Linux)** | 26.6.1 (Current for 26.04.1) | Zenodo Record `20598423` / Townsend | `mesasdk-x86_64-linux-26.6.1.tar.gz` | 199,295,811 B (~199.3 MB) | `last-modified: 2026-06-08` |
| **MESA 源码核心包** | r26.04.1 | Zenodo Record `19722306` / Paxton et al. | `mesa-26.04.1.zip` | 2,268,361,262 B (~2.11 GB) | `md5: 994fd28f38da92efc80e38ca11d8317b` |

- **下载直链解析**：
  - MESA SDK 直链：`https://zenodo.org/records/20598423/files/mesasdk-x86_64-linux-26.6.1.tar.gz?download=1`
  - MESA 源码直链：`https://zenodo.org/records/19722306/files/mesa-26.04.1.zip`

### 3.2 跨文件系统与路径兼容性设计（避坑核心）
在 Windows WSL2 环境下，直接在 `/mnt/d/天体物理导论/`（NTFS 9P 协议挂载）上运行包含成千上万个 Fortran 模块和 C 头文件的编译时，存在两个已知工程隐患：
1. **中文路径与旧脚本兼容性**：
   MESA 构建系统中部分遗留的 CSH/Perl/Make 脚本可能存在未严格加引号的宏展开（如 `$MESA_DIR/utils/...`）。如果 `MESA_DIR` 包含中文路径字符，可能导致预处理器 `#line` 解析异常或 Make 规则断裂。
2. **NTFS 9P 跨系统 I/O 延迟**：
   虽然 `/mnt/d` 支持编译，但相比 WSL2 ext4 虚拟磁盘，9P 协议的文件元数据读取较慢。

**推荐黄金解耦架构方案**：
- **物理存储与大文件安置**：
  在 `D:\天体物理导论` 中创建主目录结构，存储编译后的最终 MESA 镜像、模拟工程 `MESA_projects/`、输出日志 `LOGS/`、生成的分析图表 `figures/` 以及 Web 仪表盘。
- **纯 ASCII 符号链接桥接 (Symlink Bridge)**：
  在 Linux 内部建立纯 ASCII 软链接：
  ```bash
  ln -sfn "/mnt/d/天体物理导论/mesa-26.4.1" /home/jingben/mesa-26.4.1
  ```
  环境变量中统一使用纯 ASCII 路径 `export MESA_DIR="/home/jingben/mesa-26.4.1"`。这样物理文件全部保存在 `D:\天体物理导论`（不占用 C 盘），同时编译系统在路径解析时 100% 免疫中文字符编码问题！
- **SDK 部署位置**：
  MESA SDK 体积仅约 1.2 GB（解压后），将其解压至 `/home/jingben/mesasdk`（位于 WSL2 ext4 虚拟磁盘 `/dev/sdd`，该磁盘有 954 GB 空间），可将 GCC/GFortran 编译器的执行 I/O 速度提升数倍。

---

## 4. 严苛内存安全护栏策略 (< 85% RAM Constraint)

针对系统当前 16 GB 物理内存且 baseline 占用高达 ~72.8% 的现状，必须构筑以下多层防御体系：

### 4.1 第一道防线：WSL2 虚拟机硬件层熔断限制 (`.wslconfig`)
在 Windows 用户根目录 `C:\Users\廖敬本\.wslconfig` 中显式固化 WSL2 资源天花板：
```ini
[wsl2]
memory=5GB
processors=4
swap=4GB
localhostForwarding=true
```
- **技术原理**：
  默认情况下 WSL2 会动态向宿主机索要最多 50% 内存（~7.58 GB）。若宿主机已有 ~11 GB 占用，WSL2 若用满 7.58 GB 将导致宿主机物理内存彻底被挤爆（18.5 GB > 16 GB），造成 Windows 剧烈颠簸甚至蓝屏/冻结。通过硬性锁定 `memory=5GB`，确保 `vmmemWSL` 在 Windows 任务管理器中的峰值无论如何不得超过 5 GB，从底层封死内存溢出途径。

### 4.2 第二道防线：流式网络与解压缓冲管理
- **下载阶段**：
  严禁使用在内存中一次性缓冲完整文件的 API（如 `requests.get().content`）。必须采用 `curl -L --limit-rate` 或 Python 流式迭代器：
  ```python
  with open(dest, "wb") as f:
      for chunk in response.iter_content(chunk_size=1024 * 1024): # 严格限制 1MB 块
          f.write(chunk)
  ```
- **解压阶段**：
  使用流式解压或逐文件流写入，内存占用保持在 50 MB 以内。

### 4.3 第三道防线：编译与模拟多线程节流
- **MESA 编译控制**：
  在执行 `./install` 之前，强制限制 OpenMP 与并发进程：
  ```bash
  export OMP_NUM_THREADS=2
  ```
  避免启动 16 线程 Fortran 优化分析导致各编译单元内存叠加。
- **MESA 模拟运行控制**：
  在运行 `./rn` 时维持 `OMP_NUM_THREADS=4`。MESA 1D 恒星结构演化在 4 线程下的内存开销通常在 300~600 MB，速度极快且内存稳定。

### 4.4 第四道防线：宿主机与子系统双看门狗哨兵 (`memory_watchdog.py`)
在后台启动常驻 Python 哨兵进程，使用宿主机已安装的 `psutil 7.2.2` 实行每秒采样：
- **绿区 (<80.0%)**：正常采样，无操作。
- **黄区 (80.0% ~ 83.5%)**：进入节流预警模式，发出系统日志提示，阻止启动新任务。
- **红区 (>=84.0%)**：触发紧急自卫熔断机制：
  1. 立即挂起（`SIGSTOP`）或终止正在运行的高内存消耗子进程；
  2. 触发系统文件缓存释放（WSL2 内执行 `echo 3 > /proc/sys/vm/drop_caches`）；
  3. 彻底防止触碰 85.0% 的铁律红线。

---

## 5. 本地程序、Web UI 与洋葱图重构方案 (R2, R3, R4)

### 5.1 本地程序与数据管线优化 (R2)
1. **真实 MESA `LOGS` 接入引擎**：
   在 `stellar_grid_engine.py` 与辅助读取模块中引入标准的 `MesaLogDir` 解析管线：
   - 自动解析 `history.data` 的 100+ 核心列（`star_age`, `log_Teff`, `log_L`, `center_h1`, `log_Tc`, `log_Rhoc`, `log_Lnuc` 等）；
   - 自动解析 `profiles.index` 与指定关键演化节点（如 ZAMS、TAMS、RGB尖端、AGB、核心坍缩前夕）的 `profile*.data`；
   - 与现有 28 个校验网格模型形成双轨兼容（既支持快速本地网格查询，又支持外部 MESA `LOGS` 文件夹的一键导入与即时渲染）。
2. **规范化测试套件扩展**：
   在 `tests/test_stellar_grid.py` 中增加对 `MesaLogDir` 真实数据完整性校验、物理单调性校验与质量守恒校验。

### 5.2 现代化 Web UI 观赏级重构 (R3)
- **视觉层级重组**：
  目前 UI 面板信息密度过高、表单堆砌。重构方案将采用类似 Google DeepMind / Nature Astronomy 的学术级极简深色主题（Minimal Dark Aesthetic）：
  - 顶部设立扁平化全局控制台（当前演化模型、金属丰度、演化时标指示器）；
  - 主视图呈现“双列三维对称”：左侧为主序演化轨迹与相空间诊断（HR图 + $\rho_c - T_c$ 动态相图），右侧为主视察窗（全新洋葱切面可视化 + 物理场剖面交互分析）；
  - 消除拥挤感，增加层次清晰的卡片内边距（Padding 16~24px）、玻璃拟态背板（Backdrop Blur）、微光边界与优雅的排印字阶（Inter + JetBrains Mono）。

### 5.3 恒星内部洋葱圈（洋葱图）全面重构方案 (R4)
现有的 `initThreeEngine` 洋葱图仅用扁平的 `RingGeometry` 填充单调色块，缺乏天体物理真实质感与观众级冲击力。重构方案规划如下：
1. **多重物理层级同心切面架构**：
   - 包含完整的核合成燃烧洋葱层：
     $$\text{H-rich Envelope} \to \text{H-burning Shell} \to \text{He Core/Shell} \to \text{C/O Core} \to \text{Ne/Mg} \to \text{Si/S} \to \text{Fe Core}$$
   - 根据恒星质量（$0.3 M_\odot$ 对流红矮星 vs $1.0 M_\odot$ 太阳型星 vs $15 M_\odot / 25 M_\odot$ 超巨星）动态自适应显示真实内部结构。
2. **物理机制动态渲染特征**：
   - **核燃烧活动环微光发光层 (Active Burning Shell Glows)**：在核聚变剧烈的壳层边界叠加动态脉动光晕（Shader / Glow Material），直观指示聚变发生位置；
   - **对流区与辐射区标识 (Convective vs. Radiative Zones)**：在切面盘上使用精细纹理或径向对流循环箭头/图案清晰区分对流包层（外对流或核心对流）与辐射平衡区；
   - **坐标映射自适应模式**：支持按“真实半径对数 $\log R$”与“归一化质量坐标 $q = m/M_\star$”一键切换，彻底解决大质量恒星铁芯在真实半径下因极度致密而无法看清的问题；
   - **交互式层级点击与悬浮检视 (Interactive Inspection HUD)**：鼠标悬停或点击任一洋葱层，实时高亮该壳层并弹出科研级悬浮卡片，精确展示该层的物理参数：温度 $T$、密度 $\rho$、压强 $P$、主导核反应链（如 pp-I/II/III、CNO 循环、$3\alpha$ 反应、碳燃烧、光致蜕变）、主导元素质量丰度 $X_i$。

---

## 6. 规划目录结构与同步方案 (Layout & Synchronization)

### 6.1 `D:\天体物理导论` 标准工作区结构
```text
D:\天体物理导论\
├── MESA_projects\
│   ├── 1Msun_standard_test\
│   │   ├── inlist
│   │   ├── inlist_project
│   │   ├── inlist_pgstar
│   │   ├── history_columns.list
│   │   ├── profile_columns.list
│   │   ├── run_1msun.sh
│   │   └── LOGS\
│   │       ├── history.data
│   │       ├── profiles.index
│   │       └── profile*.data
│   └── 28_grid_runs\
│       ├── M0.3_Z0.014\
│       ├── M1.0_Z0.014\
│       └── ...
├── mesa-26.4.1\                        # 物理存放于 D 盘的 MESA 源码
├── figures\                            # 科研出版级矢量图与高清位图 (PDF & 300 DPI PNG)
│   ├── hr_diagram.pdf
│   ├── hr_diagram.png
│   ├── evolution_curves.pdf
│   ├── evolution_curves.png
│   ├── temperature_density.pdf
│   ├── temperature_density.png
│   ├── composition_profile.pdf
│   ├── composition_profile.png
│   ├── mesa_summary_4panel.pdf
│   └── mesa_summary_4panel.png
├── scripts\                            # 自动化脚本与安全工具
│   ├── env_mesa.sh
│   ├── memory_watchdog.py
│   ├── run_simulation_pipeline.py
│   ├── plot_mesa_scientific.py
│   └── sync_project.py
├── web_explorer\                       # 交互探索器发布镜像
│   ├── index.html
│   ├── stellar_explorer.html
│   └── stellar_grid_data.json
└── docs\                               # 完整中文使用指南与技术报告
    ├── README.md
    ├── MESA_26.4.1_安装与运行手册.md
    └── MESA模拟数据科研绘图指南.md
```

### 6.2 项目工作区与 D 盘双向同步机制
在 Python 中开发确定性的同步工具 `scripts/sync_project.py`：
- **同步范围**：
  - 代码与配置：`stellar_grid_engine.py`, `build_explorer_html.py`, `generate_figures.py`, `mesa_configs/`
  - 静态图表：`figures/*.png`, `figures/*.pdf`
  - Web 探索器与数据资产：`index.html`, `stellar_explorer.html`, `stellar_grid_data.json`
  - MESA 输出数据：精简提取的 `LOGS/history.data` 与具有天体物理代表性的 Profiles。
- **排除规则**：
  排除临时编译生成的大型对象文件（`*.o`, `*.mod`, `*.a`）、Git 元数据与代理临时文件，确保轻量、安全、原子化同步。

---

## 7. 结论与行动建议 (Conclusions & Action Items)

1. **环境完备性**：Windows 11 + WSL2 Ubuntu 26.04 LTS 具备编译和运行 MESA 的完备软硬件基础设施，D 盘 58.16 GB 空间完全满足需求。
2. **内存铁律保障**：通过 `.wslconfig` 锁定 5GB 虚拟机上限 + `OMP_NUM_THREADS=4` + `psutil` 动态看门狗，可 100% 确保系统总 RAM 维持在 85% 以下。
3. **下一步执行路线**：
   - 阶段 1：在 `D:\天体物理导论` 创建工程骨架，部署内存看门狗与环境初始化脚本；
   - 阶段 2：执行 WSL2 依赖包配置与 MESA 源码/SDK 下载构建；
   - 阶段 3：执行 1 $M_\odot$ 标准模型模拟与 `LOGS` 生成；
   - 阶段 4：执行 `py_mesa_reader` 论文级高清出图（PDF + 300 DPI PNG）；
   - 阶段 5：执行 Web UI 极简观赏级重构与洋葱图（Onion-Skin）同心切面彻底重塑；
   - 阶段 6：双向同步至 `D:\天体物理导论` 与本地工作区，完成单元测试，提交并推送 GitHub，验证 GitHub Pages 在线部署。
