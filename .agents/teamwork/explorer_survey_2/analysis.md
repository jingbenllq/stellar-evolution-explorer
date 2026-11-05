# 恒星演化项目全景技术调研与架构演进分析报告 (Codebase & MESA Pipeline Survey)

**报告编号**: EXP-SURVEY-20261104-01  
**执行角色**: Explorer Survey Subagent (`explorer_survey_2`)  
**调研对象**: `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project` 及相关参考指南与数据管道  
**时间戳**: 2026-11-04T23:32:00Z  

---

## 摘要 (Executive Summary)

本报告对恒星演化模拟与参数空间探索项目（`stellar_evolution_project`）的代码库、天体物理引擎、MESA 数值模拟数据管道、测试套件及 Web 前端可视化进行了全方位深度调研。

核心发现：
1. **代码现状与历史断代**：在 Git 提交 `c764b54` 中，项目全面引入了半解析物理引擎定标（v2.0），修正了太阳 ZAMS 初始光度、大质量恒星质光幂律展平、Kippenhahn 区域模拟等天体物理细节；但同时清理了早期粗糙的 `MESALogsReader` 与原始 MESA 仿真输出文件夹（原存在于 `mesa_grid_runs/` 下的 `LOGS/`），导致**当前代码库完全缺乏可运行的 MESA 数据解析管道与 `mesa_reader` 适配接口**。
2. **物理引擎特质**：当前 `stellar_grid_engine.py` 能够在 0.1 秒内生成覆盖 7 个质量（$0.3 \sim 25\,M_\odot$）与 4 个金属丰度（$Z=0.0001 \sim 0.03$）的 28 模型网格（200 个演化步，60 层径向丰度剖面），但本质上属于**基于定标锚点的半解析外插与分段线性/Sigmoid 混合模型**，缺少前主序（PMS/Hayashi track）、细致的燃烧壳层核反应能释放率 $\epsilon_{\text{nuc}}$ 分布、以及真实物理半径 $r(m)$ 径向坐标映射。
3. **MESA 兼容性断层**：`mesa_configs/` 具备高质量现代 MESA（r24.03.1 / r22.11.1）Inlist 模板，但当前 Python 运行环境中未安装 `mesa-reader`，亦无原生 Python ASCII 表头自适应解析器，急需建立一套既支持纯 Python 原生解析、又兼容 `mesa_reader` 的双模 MESA 数据桥接层。
4. **测试套件极度单薄**：`tests/test_stellar_grid.py` 仅有 1 个文件、49 行、5 个简单断言测试，缺乏物理热力学自洽性检验（Stefan-Boltzmann 关系、$\log T_c - \log \rho_c$ 单调性、质量守恒、简并核上限）、边缘极限测试、以及 MESA 解析单元测试。
5. **单体脚本维护困境**：`build_explorer_html.py` 高达 3592 行，硬编码混合了 HTML/CSS/JavaScript/Three.js 逻辑，且 3D 洋葱皮模型（Onion-Skin）在对流/辐射分区、核燃烧环发光、真实质量/半径坐标切换、交互式逐层检测等方面存在显著不足。

---

## 一、代码库现有资产与目录架构清查 (Codebase Inventory)

### 1.1 文件清单与职能矩阵

| 相对路径 | 文件大小 | 核心职能 | 当前状态评估 |
| :--- | :--- | :--- | :--- |
| `stellar_grid_engine.py` | 28.5 KB (663行) | 28 模型半解析恒星演化网格计算、Kippenhahn 序列计算、径向化学丰度剖面生成、导出 JSON/CSV | 单体脚本，无模块化封装；缺少 MESA 读取器 |
| `build_explorer_html.py` | 148.7 KB (3592行) | 将 `stellar_grid_data.json` 编译打包进单文件 HTML5 仪表盘（`index.html` 与 `stellar_explorer.html`） | 3500+ 行单体长字符串，混合 CSS/JS/WebGL，维护困难 |
| `generate_figures.py` | 4.6 KB (109行) | 使用 Matplotlib 离线生成 3 幅科研诊断图（HR 图、$\rho_c-T_c$ 相图、丰度剖面对比） | 运行正常（耗时 ~2s），但图表样式与新 UI 主题未联动 |
| `mesa_configs/run_mesa_grid.py` | 1.3 KB (32行) | 批量生成 28 个模型的运行目录并写入 `inlist_project` | 仅做文件替换，缺少运行控制与内存看门狗 |
| `mesa_configs/inlist_template_low_intermediate` | 1.6 KB (58行) | $0.3 \sim 8.0\,M_\odot$ 低中质量恒星 MESA 配置文件模板 | 符合现代 MESA 语法（`&kap`, `overshoot_scheme(1)`） |
| `mesa_configs/inlist_template_massive` | 1.6 KB (55行) | $10 \sim 25\,M_\odot$ 大质量恒星与超新星前身星模板 | 包含 MLT++、Dutch 星风与铁核坍缩终止判据 |
| `mesa_configs/history_columns.list` | 367 B (28项) | MESA 全局演化标量输出列配置 | 列定义完善，涵盖核心质量与中心化学组分 |
| `mesa_configs/profile_columns.list` | 283 B (32项) | MESA 内部结构径向剖面输出列配置 | 涵盖热力学量、丰度同位素、混合类型与核产能 |
| `mesa_grid_runs/` | 28 个子目录 | 存放 28 组模型的 MESA 运行工作区 | 当前仅包含 `inlist_project`，无 `LOGS/` 实际输出 |
| `tests/test_stellar_grid.py` | 2.1 KB (49行) | 单元与物理检验测试套件 | 仅 5 个简单用例，覆盖率极低（无边界/物理自洽性测试） |
| `parameter_space_summary.csv` | 3.9 KB (29行) | 28 模型关键天体物理参数汇总表 | 表头与数据结构规范 |
| `stellar_grid_data.json` | 1017.5 KB | 编译输出的 28 模型完整数据集（200 步轨迹 + 6 阶段剖面） | 结构规范，前端直接消费 |
| `index.html` / `stellar_explorer.html` | 147.8 KB | 编译生成的单文件交互式 3D 科学探索工作台 | 布局功能较全，但洋葱图与 UI 排版有较大优化空间 |
| `report.md` | 2.9 KB | 天体物理控制方程与 v2.0 定标技术说明报告 | 理论阐述清晰，但需同步最新的 MESA 数据管道设计 |

### 1.2 Git 考古与历史演进关键发现

通过 `git log` 与 `git show` 对比提交历史（`d8aa06e` $\to$ `011b0da` $\to$ `c764b54`），我们发现了极为关键的工程上下文：
1. **旧版 MESA Reader 的局限与剔除**：在 commit `011b0da` 中，存在一个 `MESALogsReader`，其通过硬编码 `lines[4]` 作为列名、`lines[5:]` 作为数据行。这种硬编码解析在真实 MESA 输出（版本升级或表头行数改变时）极易报 `IndexError` 或产生错位。在 `c764b54` 中，开发者为了先将半解析 28 模型物理定标（v2.0）快速发布上线，将未完善的 `MESALogsReader` 与数十兆的旧版合成 `LOGS/` 文件全部从仓库中移除。
2. **README 承诺与实现脱节**：`README.md` 的第 8 条特性声称：“*鲁棒的 `history.data` 自适应表头解析器：修复原版硬编码第 5 行的 Bug，支持自动扫描任意 MESA 版本的列名表头行*”。然而实际上，`stellar_grid_engine.py` 内部**并未包含任何 MESA 文件读取函数**。这明确指示我们：**构建健壮的原生 MESA 数据解析与桥接模块是本次重构的核心关键任务**。

---

## 二、天体物理引擎深度审计 (`stellar_grid_engine.py`)

### 2.1 网格参数空间与物理定标

引擎覆盖的二维网格为：
- 初始质量：$M_{\text{init}} \in [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]\,M_\odot$
- 初始金属丰度：$Z_{\text{init}} \in [0.0001, 0.001, 0.014, 0.03]$
- 定标参考基准：MESA r24.03.1、MIST (Choi et al. 2016)、SSE (Hurley et al. 2000)。

#### 1. ZAMS 定标与金属丰度不透明度漂移
引擎以太阳金属丰度对数漂移量 $\zeta = \log_{10}(Z / 0.014)$ 作为控制参量：
- 不透明度驱动的光度/半径修正：
  $$\Delta \log L_Z = -0.095 \zeta \quad (M < 10\,M_\odot), \qquad \Delta \log L_Z = -0.040 \zeta \quad (M \ge 10\,M_\odot)$$
  $$\Delta \log R_Z = +0.046 \zeta \quad (M < 10\,M_\odot), \qquad \Delta \log R_Z = +0.024 \zeta \quad (M \ge 10\,M_\odot)$$
  **物理自洽性评价**：金属丰度越低，束缚-自由（bound-free）与自由-自由（free-free）克喇末不透明度 $\kappa \propto Z (1+X) \rho T^{-7/2}$ 显著下降，恒星内部能量向外输运更顺畅，促使恒星核心收缩以维持流体静力学平衡，表现出更致密（$R$ 更小）、更高温（$T_{\text{eff}}$ 更高）、更明亮（$L$ 更大）的特征。参数化符号与斜率与 MIST 标准网格相符。

#### 2. 分段质光关系 ($M-L$) 与质径关系 ($M-R$)
- 低质量段（$M < 0.43\,M_\odot$）：$L \propto M^{2.35}$（受低电离度分子不透明度与不完全电离影响）
- 类太阳段（$0.43 \le M < 1.0\,M_\odot$）：$\log L = -0.155 + 4.10 \log_{10} M + \Delta \log L_Z$
- CNO 循环过渡段（$1.0 \le M < 2.0\,M_\odot$）：斜率陡化至 $4.50$（CNO 循环极强温度敏感性 $\epsilon_{\text{CNO}} \propto T^{16\sim 18}$ 开启，对流核生成）
- 中等质量段（$2.0 \le M < 10.0\,M_\odot$）：斜率回落至 $3.65$（克喇末不透明度主导的辐射平衡区）
- 大质量段（$M \ge 10.0\,M_\odot$）：斜率展平至 $2.75$（辐射压 $P_{\text{rad}} = \frac{1}{3} a T^4$ 超过气体压 $P_{\text{gas}}$，且汤姆孙电子散射不透明度 $\kappa_{\text{es}} = 0.2(1+X)$ 取代克喇末不透明度，理论渐近极值为爱丁顿光度极限下的 $L \propto M$）。
- **定标点验证**：太阳模型在 ZAMS 时 $L = 0.70\,L_\odot$ ($\log L = -0.155$)，$R = 0.89\,R_\odot$ ($\log R = -0.051$)，$T_{\text{eff}} = 5600\,\text{K}$，严格避开了将今日 $4.57\,\text{Gyr}$ 太阳误当作 ZAMS 的经典错误。

#### 3. 核心燃料份额与主序寿命 ($t_{\text{MS}}$)
- 恒星主序寿命控制公式：
  $$t_{\text{MS}} = 1.0 \times 10^{10}\,\text{yr} \times \left(\frac{f_{\text{core}}}{0.105}\right) \times \left(\frac{M/M_\odot}{L_{\text{mean}}/L_\odot}\right)$$
- 全对流红矮星（$M = 0.3\,M_\odot$）：$f_{\text{core}} = 0.85$（全星对流不断将表面富氢物质输运至中心），$t_{\text{MS}} \approx 787\,\text{Gyr}$；
- 类太阳恒星（$M = 1.0\,M_\odot$）：$f_{\text{core}} = 0.105$，$t_{\text{MS}} \approx 10.0\,\text{Gyr}$；
- 大质量恒星（$M = 15.0\,M_\odot$）：对流核质量分数 $q_{\text{cc}} \approx 0.30$ 叠加超射，$t_{\text{MS}} \approx 11.89\,\text{Myr}$；
- 极大质量恒星（$M = 25.0\,M_\odot$）：$t_{\text{MS}} \approx 6.7\,\text{Myr}$。

### 2.2 演化阶段、锚点设计与不足分析

当前阶段分为 6 个离散锚点（$s \in [0, 5]$）：
- $s = 0$：ZAMS（零龄主序）
- $s = 1$：TAMS（主序拐点，中心氢枯竭）
- $s = 2$：RGB / HG（壳层氢燃烧，底巨星支或赫氏间隙）
- $s = 3$：CHeB（中心氦燃烧，水平支 HB / 蓝环 Blue Loop / 红超巨星 RSG）
- $s = 4$：AGB / 晚期碳氧燃烧（渐近巨星支或超巨星碳燃烧）
- $s = 5$：演化终点（白矮星冷却 / 铁核坍缩前夕）

#### 存在的天体物理局限性与改进空间：
1. **完全缺失前主序（PMS / Hayashi Track）**：
   原恒星经历动态坍缩后的林忠四郎径向对流收缩阶段（Hayashi Track）及辐射核形成的 Henyey Track 是理解原恒星盘与锂燃烧的关键。MESA Inlist 中显式声明了 `create_pre_main_sequence_model = .true.`，但本地半解析引擎从 $s=0$（ZAMS）开始，切断了 PMS 阶段。
2. **亚巨星（SGB）与赫氏间隙（HG）被压缩**：
   从 TAMS 到 RGB 顶端跨越了 Schönberg-Chandrasekhar 极限（等温氦核质量上限 $\sim 0.1 M_*$）引发的核急剧收缩与包层膨胀镜像效应。当前作为单一线性段 $s \in [1, 2]$，无法细致展示低质量恒星底巨星（Subgiant）的长停留与大质量恒星横穿赫氏间隙的极短时标。
3. **缺少真实超新星爆发动态（SN Bounce）**：
   大质量恒星演化终点直接定格在铁核前夕，缺乏光致蜕变（Photodisintegration: $^{56}\text{Fe} \to 13\,^4\text{He} + 4\,n$）与电子捕获引发的核心动态坍缩到原中子星核硬化反弹（Core bounce）的时标与能量学表达。
4. **单调参数化进程 $s$ 与物理时标 $\text{age}$ 脱节**：
   200 个网格步按 $s$ 等距分布，导致 90% 的网格点被分配在后主序极其短暂的晚期阶段，而主序阶段（占据恒星寿命 90% 以上）仅有前 40 步。虽然便于可视化晚期剧烈变化，但在时间轴回放时造成了“物理时间非线性极度扭曲”，必须在 UI 轴与数据结构中显式区分“物理年龄坐标”与“演化特征坐标”。

### 2.3 径向化学丰度剖面 $X_i(q)$ 与 Kippenhahn 区域建模

1. **化学元素跟踪**：跟踪 7 个核心同位素 `["H1", "He4", "C12", "O16", "Ne20", "Si28", "Fe56"]`。
2. **Sigmoid 区域混合**：利用双曲正切函数 $\text{sig}(q, q_0, w) = \frac{1}{2} [1 + \tanh((q - q_0)/w)]$ 构建核、壳层与包层之间的过渡边界。
3. **归一化保证**：计算末端采用矩阵求和与除法归一化：
   $$\sum_{i=1}^7 X_i(q) \equiv 1.0000$$
4. **洋葱皮（Onion-Skin）多层构建**：在 $15\,M_\odot$ 阶段 5 呈现典型的 Fe 核 ($q < q_{\text{Fe}}$) $\to$ Si 壳 $\to$ O-Ne 壳 $\to$ C-O 壳 $\to$ He 壳 $\to$ H 包层。
5. **缺陷**：
   - 壳层过渡宽度 $w = 0.015 \sim 0.03$ 是经验给定的，未能反映实际对流超射（Convective Overshoot）引起的微观扩散或半对流阶跃；
   - 缺少核燃烧功率密度 $\epsilon_{\text{nuc}}(q)$ 与引力势能释放率 $\epsilon_{\text{grav}}(q)$ 剖面；
   - 质量坐标 $q = m/M_*$ 无法直观展示实际空间半径膨胀（如 RSG 半径膨胀至近 $1000\,R_\odot$，而铁核仅千公里级）。

---

## 三、MESA 数据仿真数据管道与解析器架构深度剖析

### 3.1 MESA 输出文件体系结构标准

依据官方文档与 `d:\QQ\MESA模拟数据科研绘图教程_py_mesa_reader.md`，一次标准 MESA 模拟在 `LOGS/` 中生成三类核心文件：

```
LOGS/
├── history.data        # 全局时间序列：model_number, star_age, star_mass, log_L, log_Teff, log_center_T/Rho, core masses...
├── profiles.index      # 索引映射表：model_number -> priority -> profile_number
├── profile1.data       # 内部剖面切片：zone, mass, q, logR, logT, logRho, h1, he4, c12, mixing_type, eps_nuc...
├── profile2.data
└── ...
```

#### 关键解析难点与陷阱：
1. **ASCII 表头格式动态多变**：
   - 标准 MESA 文件前几行为全局标量元数据（`version_number`, `initial_mass`, `initial_z` 等），接着是空行，然后是列名行，最后是纯浮点数据。
   - 不同 MESA 版本（如 r15140, r22.11.1, r24.03.1, 26.4.1）表头占用的行数并不固定（有时为 5 行，有时为 6 行）。若采用索引写死 `lines[4]` 或 `lines[5]`，遇到微调即崩溃。
2. **Fortran 双精度科学计数法指数标记**：
   - Fortran 输出常包含 `1.23456789D+02`，Python 内置的 `float()` 解析 `D` 时会抛出 `ValueError`，必须在词法解析阶段正则或字符替换为 `E`。
3. **Checkpoint 重启导致的备份行（Backup Duplicates）**：
   - 当 MESA 发生收敛困难减小步长或从快照重启时，`history.data` 会写入回滚前的废弃模型步，导致 `model_number` 出现非单调下降。若直接绘图会出现“走回头路”的折线伪影。官方 `mesa_reader` 提供了 `remove_backups()`，自建解析器必须原生支持该剔除逻辑。
4. **内部剖面 Zone 编号顺序与方向反转**：
   - MESA 物理网格编号通常从表面（Zone 1，表面 $q \to 1$）指向中心（Zone $K$，中心 $q \to 0$）；而理论物理与本地引擎习惯从中心 $q=0$ 指向表面 $q=1$。桥接层必须自动检测并规范化为单调递增的 $q$。

### 3.2 现有配置与运行脚本审计 (`mesa_configs/`)

- `run_mesa_grid.py`：仅通过简单的字符串替换生成 `inlist_project`，无并行任务调度、无异常退出捕获、无日志收集。
- `inlist_template_low_intermediate` 与 `inlist_template_massive`：
  - 语法审计：完全符合现代 MESA 命名空间规范（`&star_job`, `&eos`, `&kap`, `&controls`）；
  - 终止判据设置合理（低中质量：白矮星降温极限 `log_L_lower_limit = -2.0d0`；大质量：铁核坍缩下落速度 `fe_core_infall_limit = 1.0d8` cm/s）；
  - 物理参数完备（Ledoux 对流准则、半对流、指数对流超射、Reimers/Bloecker/Dutch 混合星风）。

### 3.3 统一原生与双模 MESA 桥接器设计方案 (Unified MESA Bridge)

为实现 MESA 模拟成果与本地轻量级 Web 看板的无缝集成，设计分层数据访问架构：

```
+-------------------------------------------------------------------------------+
|                       Unified Stellar Data Schema                             |
|         (StellarModel: metadata, pathway, track, kippenhahn, profiles)        |
+-------------------------------------------------------------------------------+
                                        ^
                                        | (Standard Adapter)
         +------------------------------+------------------------------+
         |                                                             |
+----------------------------------+         +----------------------------------+
|   Semi-Analytical Grid Engine    |         |        MESA Bridge Engine        |
|  (Fast local physics fallback)   |         | (Real simulation ingestion layer)|
+----------------------------------+         +----------------------------------+
                                                               ^
                                                               |
                                            +------------------+------------------+
                                            | (Auto-detect)                       |
                             +------------------------------+  +------------------------------+
                             |   Pure-Python Native Parser  |  |  mesa_reader (PyMesaReader)  |
                             | (Zero dependency, robust)    |  | (High-level official wrapper)|
                             +------------------------------+  +------------------------------+
```

#### 原生解析器设计要点（`NativeMesaParser`）：
1. **自动表头探测**：逐行扫描，寻找包含 `model_number` 与 `star_age`（或 `zone` 与 `q`/`mass`）的特征行作为数据列名，前序键值作为元数据字典存入 `header`。
2. **Fortran 浮点快速清洗**：使用高效字符串预处理或 NumPy 向量化加载（`np.genfromtxt` / 正则替换 `D` $\to$ `E`）。
3. **备份模型单调清洗**：
   ```python
   def prune_backups(model_numbers, data_dict):
       clean_idx = []
       for i, m in enumerate(model_numbers):
           while clean_idx and m <= model_numbers[clean_idx[-1]]:
               clean_idx.pop()
           clean_idx.append(i)
       return {k: [v[i] for i in clean_idx] for k, v in data_dict.items()}
   ```
4. **阶段自动识别器（Stage Identifier）**：
   根据中心化学丰度（`center_h1`, `center_he4`, `center_c12`）与核心质量演化，自动定位 6 大特征物理阶段对应的模型编号与 Profile 剖面文件编号，映射为统一的 `profiles["0"] ~ profiles["5"]`。

---

## 四、测试套件现状评估与测试矩阵设计 (`tests/`)

### 4.1 当前测试套件评估

当前 `tests/test_stellar_grid.py` 仅包含 5 个测试用例：
1. `test_28_models_present`: 检查网格字典长度为 28；
2. `test_solar_zams_vs_present_day_sun_calibration`: 检查太阳 ZAMS 光度与寿命；
3. `test_fully_convective_03msun_flat_profile`: 检查 $0.3\,M_\odot$ 平坦丰度分布；
4. `test_8msun_metallicity_fate_bifurcation`: 检查 $8.0\,M_\odot$ 在高低金属丰度下的残骸分岔；
5. `test_strict_abundance_normalization`: 检查丰度加和为 1。

**主要缺陷与隐患**：
- **测试覆盖率极低**：代码覆盖率低于 25%，只测试了最理想路径上的 3 个模型，中间质量 $3.0, 5.0\,M_\odot$ 与大质量 $15.0, 25.0\,M_\odot$ 几乎完全裸奔；
- **缺乏热力学自洽性断言**：未测试有效温度、光度与半径是否严格符合斯忒藩-玻尔兹曼辐射定律；
- **缺乏相空间轨迹物理合法性检验**：未验证中心温度 $\log T_c$ 和中心密度 $\log \rho_c$ 是否在主序至简并收缩过程中单调上升或停留在物理合理区间；
- **缺乏输入容错与边界断言**：当用户传入非法质量（如 $-1.0\,M_\odot$ 或 $500\,M_\odot$）或非法金属丰度时无异常处理测试；
- **缺少 MESA 解析与文件 I/O 测试**：没有任何测试验证 `history.data` 或 `profile*.data` 的读写。

### 4.2 现代化天体物理与软件测试矩阵设计

重构后的测试套件划分为 7 大独立测试模块，共计 40+ 项测试用例：

| 模块名 | 测试目标 | 关键测试用例 (Test Cases) |
| :--- | :--- | :--- |
| `test_zams_physics.py` | 零龄主序物理标度律 | • 太阳 ZAMS 定标点 ($L=0.70L_\odot, R=0.89R_\odot, T_{\text{eff}}=5600\text{K}$)<br/>• 质光关系各质量区间分段斜率 ($M^{2.35}, M^{4.1}, M^{4.5}, M^{3.65}, M^{2.75}$)<br/>• 低金属丰度不透明度下降导致的高温致密效应验证 ($\zeta$ 偏导性检验)<br/>• 主序寿命 $t_{\text{MS}}$ 随质量增加单调递减检验 ($0.3M_\odot > 1M_\odot > 15M_\odot > 25M_\odot$) |
| `test_tracks_and_phases.py` | 演化轨迹与热力学自洽性 | • 斯忒藩-玻尔兹曼恒等式一致性：$\lvert \log L - (2\log R + 4(\log T_{\text{eff}} - 3.7613)) \rvert < 10^{-3}$<br/>• 物理时间单调性：$\Delta \text{age} \ge 0$<br/>• 质量连续性与恒星风损失：$0 < M(t) \le M_{\text{init}}$<br/>• 核心热力学收缩：除晚期极度膨胀或冷却外，$\log T_c$ 与 $\log \rho_c$ 演化方向符合位力定理 |
| `test_pathways_and_remnants.py` | 演化归宿与简并核极限 | • 钱德拉塞卡极限约束：白矮星残骸质量 $M_{\text{rem}} \le 1.44\,M_\odot$<br/>• 残骸类型全覆盖检验 (He WD, CO WD, ONeMg WD, NS, BH)<br/>• $8\,M_\odot$ 超渐近巨星支在 $Z=0.014$ (ONeMg WD) 与 $Z=0.0001$ (ECSN NS) 的分岔判据 |
| `test_abundance_profiles.py` | 内部径向核合成与归一化 | • 严格丰度归一化：所有网格 $\sum_i X_i(q) = 1.0000 \pm 10^{-5}$<br/>• 组分非负性：$X_i(q) \ge 0.0$<br/>• $0.3\,M_\odot$ 全星对流无化学梯度：$\max(X_{\text{H}}) - \min(X_{\text{H}}) < 0.005$<br/>• $15\,M_\odot$ 终态同心洋葱皮核层结构拓扑顺序检验 ($\text{Fe} \to \text{Si} \to \text{O/Ne} \to \text{C/O} \to \text{He} \to \text{H}$) |
| `test_kippenhahn.py` | 对流与燃烧区域拓扑边界 | • 区域归一化约束：$0 \le q_{\text{conv}}, q_{\text{shell}} \le 1.0$<br/>• 太阳主序无对流核 ($q_{\text{cc}} = 0$) 且对流包层位于表层 ($q_{\text{ce}} > 0.95$)<br/>• 大质量恒星主序存在显著对流核 ($q_{\text{cc}} \ge 0.25$) 且辐射包层主导 |
| `test_mesa_reader.py` | MESA ASCII 文件读取与鲁棒性 | • 自动检测表头行数（支持 4~8 行动态变化）<br/>• Fortran 双精度科学计数法 `D+` 转换与容错解析<br/>• 剔除回滚备份步（`remove_backups` 单调性恢复）<br/>• `profiles.index` 与多个 `profile*.data` 自动关联加载<br/>• 将 MESA 仿真数据转换为标准 `StellarModel` 实例并检验字段完整性 |
| `test_pipeline_and_cli.py` | CLI 与构建管道端到端测试 | • `stellar_grid_engine.py` 命令行重新生成 JSON/CSV 成功<br/>• `generate_figures.py` 静态图生成与图像文件非空验证<br/>• `build_explorer_html.py` HTML 单文件编译与包含关系检查 |

---

## 五、Web 交互看板与洋葱图（Onion-Skin）可视化重构审计

### 5.1 现有 Web UI 架构缺陷分析

当前 `build_explorer_html.py` 编译出的页面布局与交互逻辑虽然功能丰富，但在**面向学术观众展示与直观易读性**上存在明显痛点：
1. **信息层级过于拥挤紧凑**：
   - 顶部控制条、8 个遥测指标卡、2x2 四大画布（HR 图、相图、洋葱图、剖面图）、外加底部庞大的 MESA Inlist 生成器和 28 模型矩阵，堆叠在单个视口内，元素视觉噪声高，缺乏“呼吸感”。
2. **移动端与高分屏适配瑕疵**：
   - 某些 Canvas 在窗口动态缩放或不同设备像素比（DPI）缩放时，坐标轴刻度字体会发生微小的模糊或重叠。
3. **颜色对比度与辅助信息**：
   - 部分次级文本对比度偏低，缺乏符合 WCAG AA 标准的视觉层次。

### 5.2 洋葱图（洋葱皮剖切模型）核心重构方案 (R4 对照)

依据任务书 R4 要求：*“提供清晰、美观、天体物理准确的同心核燃烧壳层（$\text{H}\to\text{He}\to\text{C}\to\text{Ne}\to\text{O}\to\text{Si}\to\text{Fe}$）剖切视觉，呈现对流区与辐射区纹理差异、活动核燃烧环脉动发光、真实质量/半径坐标映射、化学丰度气泡提示及交互式层级点击检测”*。

现有 3D 渲染器存在的关键差距与具体重构方案：

| 维度 | 现有实现缺陷 | 深度重构方案 (Overhaul Architecture) |
| :--- | :--- | :--- |
| **壳层划分机制** | 简单根据当前点元素丰度最大值划分，忽略了重叠壳层与反应能量集中区 | **物理化学混合分层**：基于主要元素丰度阈值与核反应产物界定同心层边界，显式划分出 7 大核心圈层与交界处的活动燃烧壳层（Burning Shells）。 |
| **燃烧壳层发光** | 壳层之间为均质材质，无燃烧特征 | **燃烧反应环脉动光效 (Nuclear Flame Glow)**：在活动氢燃烧壳层、氦燃烧壳层及碳氧硅燃烧边界，叠加带有径向渐变或粒子脉动的发光环材质（Shader / Emissive Ring），动态表达 $\epsilon_{\text{nuc}}$ 的剧烈能量释放。 |
| **对流与辐射区** | 全星表面与内部均采用单一平滑材质，无法区分物理传能机制 | **物理机制分色与纹理表达**：<br/>• **对流区（Convective）**：采用微动湍流纹理、沸腾胞状图案或半透明对流环流箭头贴图；<br/>• **辐射区（Radiative）**：采用分层紧密、光洁均匀的层流同心色调。 |
| **坐标系统映射** | 固定使用经验幂律 $r \propto q^{0.38}$，无法感知真实物理尺度 | **双模/多模坐标平滑切换**：<br/>• **质量坐标模式 (Mass $q=m/M_*$)**：展示各壳层所占真实质量份额（适合观察铁核与包层质量比）；<br/>• **几何半径模式 (Radius $r/R_*$ / $\log r$)**：展示真实内部空间尺度，直观反映红超巨星庞大包层与极其致密的微小内核之间的巨大空间悬殊；<br/>• 提供一键 Toggle 按钮与平滑补间动画（Tween/Lerp）。 |
| **2D / 3D 视效互补** | 仅有 3D 剖切球体，在特定视角下由于三维透视投影难以准确读取各层厚度 | **2D 经典教材切面图 + 3D 自由旋转切角双重视角**：在洋葱图面板提供 3D 剖切（视角可自由拖拽旋转）与 2D 高精切面图（精确标注文字指引线、核聚变主方程，如 $4^1\text{H} \to ^4\text{He}$, $3\alpha \to ^{12}\text{C}$）的无缝切换。 |
| **交互式逐层探测** | 仅在角落展示静态 HUD 文本，无法点击层级 | **射线投射交互 (Raycasting & Layer Inspector)**：支持鼠标悬停（Hover）或点击任意同心壳层，高亮选中层，并在悬浮卡片中精确展示：层级名称、边界质量区间 $[q_0, q_1]$、主导核反应、局部温度 $T$、局部密度 $\rho$、主要同位素质量分数。 |

---

## 六、重构与模块化架构设计方案 (Refactoring Architecture Plan)

为彻底解决脚本庞大单体化、无模块可复用、无 MESA 解析接口等问题，制定以下全模块化工程架构设计：

### 6.1 目标工程目录树

```text
stellar_evolution_project/
├── stellar_evolution/                  # 核心 Python 架构包 (全新引入)
│   ├── __init__.py                     # 包暴露接口与版本信息 (v2.1.0)
│   ├── constants.py                    # 物理与天体物理常数、太阳标定常量、元素符号定义
│   ├── core/                           # 核心数据模型与基础枚举
│   │   ├── __init__.py
│   │   ├── models.py                   # 强类型数据模型 (Dataclasses: TrackPoint, StellarModel, GridData)
│   │   └── pathways.py                 # 演化阶段判据、残骸分类与超新星类型路由
│   ├── physics/                        # 恒星物理学与半解析理论引擎
│   │   ├── __init__.py
│   │   ├── zams.py                     # ZAMS 质光/质径/中心温密标度关系与不透明度修正
│   │   ├── tracks.py                   # 200 步演化轨迹插值、Hook 与行星状星云循环
│   │   ├── profiles.py                 # 60 点径向丰度剖面生成与归一化
│   │   └── kippenhahn.py               # 对流核、对流包层与燃烧壳层几何边界计算
│   ├── mesa/                           # MESA 数值模拟接口与解析管道
│   │   ├── __init__.py
│   │   ├── parser.py                   # 纯 Python 鲁棒 ASCII 日志解析器 (history & profile)
│   │   ├── bridge.py                   # MESA 数据至统一数据模型的自动特征映射与阶段对齐
│   │   └── generator.py                # MESA Inlist 生成器与内存监控启动器
│   ├── viz/                            # 可视化与科学制图
│   │   ├── __init__.py
│   │   ├── static_plots.py             # Matplotlib 科研诊断图离线渲染引擎
│   │   └── html_builder.py             # Web 探索器多组件编译装配引擎
│   └── cli.py                          # 统一命令行接口 (CLI Entrypoint)
│
├── web/                                # Web 前端资产与模板目录 (彻底分离长字符串)
│   ├── templates/                      # HTML 框架模板
│   │   └── explorer.html.j2 / .html
│   ├── css/                            # 模块化样式表
│   │   ├── variables.css               # 调色板、圆角、玻璃拟态变数
│   │   ├── layout.css                  # 栅格系统、自适应布局
│   │   └── components.css              # 仪表盘卡片、控制台、热力矩阵
│   └── js/                             # 模块化前端脚本
│       ├── state.js                    # 响应式状态管理 (双星参数, 演化时间步)
│       ├── charts.js                   # Canvas 2D 绘图 (HR 图, 相图, 剖面图, Kippenhahn)
│       ├── onion_viewer.js             # 3D/2D 深度洋葱皮切面、燃烧环发光与交互探测
│       └── main.js                     # 顶层事件绑定与初始化
│
├── mesa_configs/                       # MESA 原生配置与模板 (保持原样并扩展)
│   ├── history_columns.list
│   ├── profile_columns.list
│   ├── inlist_template_low_intermediate
│   └── inlist_template_massive
│
├── tests/                              # 现代化单元与集成测试套件
│   ├── __init__.py
│   ├── test_zams_physics.py
│   ├── test_tracks_and_phases.py
│   ├── test_pathways_and_remnants.py
│   ├── test_abundance_profiles.py
│   ├── test_kippenhahn.py
│   ├── test_mesa_reader.py
│   └── test_pipeline_and_cli.py
│
├── stellar_grid_engine.py              # 根目录向后兼容引导脚本 (Thin wrapper -> stellar_evolution)
├── generate_figures.py                 # 根目录向后兼容引导脚本 (Thin wrapper -> stellar_evolution.viz)
├── build_explorer_html.py              # 根目录向后兼容引导脚本 (Thin wrapper -> stellar_evolution.viz)
├── parameter_space_summary.csv         # 数据产物
├── stellar_grid_data.json              # 数据产物
├── index.html                          # 编译产物 (部署用)
└── stellar_explorer.html               # 编译产物 (备用部署)
```

### 6.2 核心数据模型定义规范 (`stellar_evolution.core.models`)

采用强类型 Python `@dataclass`，保证所有字段语义严谨，支持与字典及 JSON 的零损耗双向互转：

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ZAMSProperties:
    log_L: float
    log_R: float
    log_Teff: float
    log_Tc: float
    log_Rhoc: float
    t_ms: float
    f_core: float
    zeta: float

@dataclass
class EvolutionaryPathway:
    regime: str
    core_structure: str
    max_burning: str
    remnant_type: str
    remnant_code: str
    remnant_mass: float
    supernova: str

@dataclass
class StellarTrack:
    s: List[float]
    age_yr: List[float]
    mass: List[float]
    log_Teff: List[float]
    log_L: List[float]
    log_R: List[float]
    log_Tc: List[float]
    log_Rhoc: List[float]
    eta: List[float]

@dataclass
class KippenhahnSeries:
    conv_core: List[float]
    conv_env: List[float]
    h_shell: List[Optional[float]]
    he_shell: List[Optional[float]]

@dataclass
class ChemicalProfile:
    q: List[float]
    H1: List[float]
    He4: List[float]
    C12: List[float]
    O16: List[float]
    Ne20: List[float]
    Si28: List[float]
    Fe56: List[float]

@dataclass
class StellarModel:
    mass_init: float
    z_init: float
    zams: ZAMSProperties
    pathway: EvolutionaryPathway
    stage_names: List[str]
    stage_step_indices: List[int]
    track: StellarTrack
    kippenhahn: KippenhahnSeries
    profiles: Dict[str, ChemicalProfile]
```

### 6.3 根目录脚本向后兼容保证 (Backward Compatibility)

为确保现有工作流与自动化调用不发生破坏，所有根目录原有脚本（`stellar_grid_engine.py`, `build_explorer_html.py`, `generate_figures.py`）将保留为标准入口引导文件（Thin Wrappers）。例如：

```python
# stellar_grid_engine.py
#!/usr/bin/env python3
"""Backward-compatible entry point for Stellar Evolution Grid Engine."""
from pathlib import Path
from stellar_evolution.physics.grid_engine import build_full_grid

if __name__ == "__main__":
    build_full_grid(Path(__file__).parent)
```

这样既完成了代码的深度解耦与模块化，又无缝保持了现有命令行命令（如 `python3 stellar_grid_engine.py`）的 100% 行为一致。

---

## 七、调研结论与执行行动建议 (Conclusions & Action Items)

1. **核心结论**：
   - 现存半解析物理网格在天体物理原理定标上具备优良基础，但工程架构为完全扁平的单体脚本集合。
   - 必须补全**原生 MESA ASCII 数据解析与桥接模块**，以达成用户关于 MESA 模拟成果与本地可视化系统无缝对接的要求。
   - 必须实施**全面模块化重构**（`stellar_evolution` 基础包），并将测试套件从 5 个用例扩充为 40+ 项严格的科学与功能验证集。
   - Web 界面与洋葱皮剖面图必须完成质感与可读性重构，实现双星同屏对比、发光燃烧壳层、对流/辐射分区、质量/半径坐标切换与逐层悬浮交互探测。

2. **后续实施推进顺序建议**：
   - **阶段一 (Phase 1)**：搭建 `stellar_evolution` 核心包体系架构与强类型数据模型，将物理计算逻辑拆分解耦入 `physics/` 子包，重构根脚本作为 Wrapper。
   - **阶段二 (Phase 2)**：实现 `stellar_evolution/mesa/parser.py`（纯 Python 自适应表头 MESA 解析器）与 `bridge.py`（MESA 到 Explorer 格式对齐转换器），编写对应的高覆盖度单元测试。
   - **阶段三 (Phase 3)**：重写并扩充测试套件（覆盖 7 大测试模块与 40+ 项测试用例），实现 100% 自动化测试通过。
   - **阶段四 (Phase 4)**：全面重构 Web 前端与洋葱图（Onion-Skin Visualizer），优化排版层级、暗色空间美学、双重视角切换、发光反应环与交互式气泡探测。
   - **阶段五 (Phase 5)**：执行端到端构建、更新诊断图与技术文档，准备向协同编排器（Orchestrator）与实施 Subagent 进行交付。
