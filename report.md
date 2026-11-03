# 恒星演化参数空间半解析模拟与多阶段状态对比研究报告

> **数据来源声明 (Data Source Notice)**：
> 本研究所呈现的恒星演化轨迹与内部径向剖面基于半解析恒星演化物理模型（Tout et al. 1996; Hurley et al. 2000; Kippenhahn et al. 2012）计算生成，并以标准 MESA ASCII 数据格式组织存储，非 MESA 微分方程求解器的直接数值积分产物。

---

## 一、 课题背景与设计思路

根据课题指导要求，本工程围绕**“恒星演化参数空间（Parameter Space）构建与跨阶段状态对比”**展开，完整实现了从 **MESA 配置文件工程（`inlist` 网格）**、**标准格式演化数据生成与解析（`history.data` & `profile*.data`）**、**多维物理演化相图绘制** 到 **交互式参数空间探索器（Web 看板）** 的全套流程。

### 1. 参数空间二维网格设计 $(M_{\text{init}}, Z_{\text{init}})$
* **初始质量维度（7 个代表性质量点，覆盖全部恒星演化分支与结局）**：
  * $0.3\,M_\odot$（极低质量全对流红矮星 $\rightarrow$ 氦白矮星 He WD）
  * $1.0\,M_\odot$（类太阳低质量恒星，经历红巨星支简并氦闪 $\rightarrow$ 碳氧白矮星 CO WD）
  * $3.0\,M_\odot$、$5.0\,M_\odot$（中等质量恒星，经历主序 CNO 对流核与赫罗图蓝环 $\rightarrow$ 碳氧白矮星 CO WD）
  * $8.0\,M_\odot$（大质量临界区 Super-AGB 恒星，偏心碳点燃 $\rightarrow$ 氧氖镁白矮星 ONe WD / 电子俘获超新星）
  * $15.0\,M_\odot$、$25.0\,M_\odot$（大质量与超大质量恒星，全套核反应链直至铁核坍缩超新星 CCSN $\rightarrow$ 中子星 NS / 黑洞 BH）
* **初始金属丰度维度（4 个代表性化学丰度点）**：
  * $Z = 0.0001$（极端贫金属星族 II）
  * $Z = 0.001$（贫金属星族 II）
  * $Z = 0.014$（标准太阳金属丰度星族 I）
  * $Z = 0.030$（富金属星族 I）
* **关键演化阶段切片（6 个演化里程碑，根据恒星质量自适应命名）**：
  1. `ZAMS`：零龄主序（中心氢聚变稳定开启）
  2. `TAMS`：主序拐点（中心氢耗尽，$X_{\text{c}}(^1\text{H}) \to 0$）
  3. `RGB_HeIgn` / `HG_HeIgn` / `Subgiant_HeCore`：红巨星支顶氦点燃 / 赫氏间隙氦点燃 / 亚巨星收缩
  4. `HB_CoreHe`：中心氦燃烧阶段（水平支 Red Clump、蓝环 Blue Loop 或超巨星阶段）
  5. `AGB` / `AdvBurn_COSi` / `SuperAGB_CO` / `HeCore_HShell`：渐近巨星支 / 晚期碳氧硅燃烧 / 氦核收缩氢壳层
  6. `EndState`：演化终点（白矮星冷却序列或大质量恒星铁核坍缩前夕“洋葱皮”状态）

---

## 二、 核心参数空间对比结果汇总表（$Z = 0.014$ 太阳金属丰度基线）

下表提取自本工程生成的 `parameter_space_summary.csv`，对比了不同初始质量恒星在零龄主序（ZAMS）、主序拐点（TAMS）、氦点燃及演化终点的核心物理状态：

| 初始质量 $M_{\text{init}}$ | 主序核心结构与产能机制 | $\log(L_{\text{ZAMS}}/L_\odot)$ | $T_{\text{eff,ZAMS}}$ (K) | 主序寿命 $\tau_{\text{MS}}$ (年) | 氦点燃方式与核简并度 $\eta_c$ | 最高中心温度 $\log(T_{c,\max}/\text{K})$ | 最终演化结局与残骸质量 |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :--- |
| **$0.3\,M_\odot$** | 全星对流（p-p 链） | $-1.84$ | $3\,337$ | $2.08 \times 10^{11}$ | 不点燃氦（$\eta_c > 12$ 强简并） | $7.17$ | **氦白矮星 (He WD)** ($0.26\,M_\odot$) |
| **$1.0\,M_\odot$** | 辐射核 + 对流包层（p-p 链） | $0.00$ | $5\,772$ | $1.00 \times 10^{10}$ | **红巨星支顶简并氦闪** ($\eta_c \approx 18.5$) | $8.28$ | **碳氧白矮星 (CO WD)** ($0.53\,M_\odot$) |
| **$3.0\,M_\odot$** | 对流核 + 辐射包层（CNO） | $1.82$ | $12\,003$ | $8.44 \times 10^{8}$ | 非简并平稳点燃 ($\eta_c \approx -0.2$，蓝环) | $8.42$ | **碳氧白矮星 (CO WD)** ($0.68\,M_\odot$) |
| **$5.0\,M_\odot$** | 对流核 + 辐射包层（CNO） | $2.59$ | $16\,226$ | $2.68 \times 10^{8}$ | 非简并平稳点燃 ($\eta_c \approx -0.2$，蓝环) | $8.42$ | **碳氧白矮星 (CO WD)** ($0.82\,M_\odot$) |
| **$8.0\,M_\odot$** | 大对流核 + 辐射包层（CNO） | $3.31$ | $21\,414$ | $9.29 \times 10^{7}$ | 非简并氦燃烧 + 半简并偏心碳点燃 | $8.82$ | **氧氖镁白矮星 (ONe WD)** ($1.18\,M_\odot$) |
| **$15.0\,M_\odot$** | 大对流核 + 辐射包层（CNO） | $4.26$ | $31\,024$ | $2.26 \times 10^{7}$ | 非简并全链燃烧（H$\to$He$\to$C$\to$Ne$\to$O$\to$Si） | $9.55$ | **铁核坍缩超新星 $\to$ 中子星** ($1.45\,M_\odot$) |
| **$25.0\,M_\odot$** | 极大对流核 + 强星风（CNO） | $5.04$ | $41\,937$ | $7.16 \times 10^{6}$ | 非简并全链燃烧 + 强辐射压星风失重 | $9.55$ | **核坍缩超新星 $\to$ 中子星/黑洞** ($2.85\,M_\odot$) |

---

## 三、 五大核心物理维度可视化与机理分析

本工程在 `figures/` 目录下自动生成了 5 张高分辨率出版级对比图（均提供矢量图 `.svg` 与高清位图 `.png`）：

### 1. 赫罗图参数空间演化轨迹对比（`fig1_hr_diagram_grid.png`）
* **质量效应**：随着初始质量从 $0.3\,M_\odot$ 增至 $25\,M_\odot$，零龄主序（ZAMS）光度跨越近 7 个数量级（$\log L/L_\odot$ 从 $-1.84$ 到 $5.04$）。低质量恒星（$1\,M_\odot$）拥有陡峭上升的红巨星支（RGB），在顶点发生氦闪后回落至水平支（Red Clump）；中等质量恒星（$3-8\,M_\odot$）在中心氦燃烧期间表现出显著的**横向蓝环（Blue Loop）**；大质量恒星（$15-25\,M_\odot$）则近乎水平地横跨赫罗图上部演变为红超巨星（RSG）。
* **金属丰度效应**：对比实线（$Z=0.014$）与虚线（$Z=0.0001$），在相同初始质量下，**贫金属恒星由于自由-束缚与束缚-束缚不透明度（Opacity $\kappa$）显著降低，辐射能量传输效率更高，因此半径更致密、表面有效温度更高（轨迹整体偏蓝）、光度更大**。

### 2. 中心温度-密度演化相图（`fig2_central_rho_T_phase.png`）
* **维里定理与核心收缩标度律**：对于非简并理想气体核心，流体静力学平衡与维里定理要求核心收缩时满足 $T_c \propto M_c^{2/3} \rho_c^{1/3}$，因此在 $\log \rho_c - \log T_c$ 图上呈现斜率为 $1/3$ 的平行上升直线。
* **电子简并阻断机制**：当核心密度过高而温度较低时，电子气进入泡利不相容原理主导的简并态（$\eta > 0$，图中蓝色阴影区），压强 $P_e \propto \rho^{5/3}$ 与温度解耦：
  * $0.3\,M_\odot$ 在氢耗尽后直接滑入简并区，中心温度永远无法达到 $10^8\,\text{K}$，演变为氦白矮星；
  * $1.0\,M_\odot$ 在简并区内达到 $10^8\,\text{K}$ 触发热失控**氦闪（Helium Flash）**，解除简并后完成氦燃烧，随后碳氧核再次进入简并区冷却为 CO 白矮星；
  * $15-25\,M_\odot$ 核心熵高、密度低，全程避开电子简并区，连续冲破碳（$5\times 10^8\,\text{K}$）、氖/氧（$1.5\times 10^9\,\text{K}$）和硅燃烧（$3.2\times 10^9\,\text{K}$）点火线，直至铁核光致蜕变引发核坍缩超新星。

### 3. 基彭哈恩结构演化图对比（`fig3_kippenhahn_comparison.png`）
* **$1.0\,M_\odot$ 类太阳恒星**：主序阶段核心温度梯度平缓，呈现**中心辐射核 + 表面薄对流层**；进入红巨星阶段后，外部对流包层向内剧烈延伸（第一次吸积挖掘 First Dredge-Up），中心氦闪解除简并后形成短暂的对流氦核。
* **$15.0\,M_\odot$ 大质量恒星**：主序阶段 CNO 循环对温度极度敏感（$\epsilon_{\text{CNO}} \propto T^{16\sim 18}$），中心核产能高度集中，导致强大的**中心对流核（占总质量约 40%）+ 外部辐射包层**；随演化推进，对流核质量逐渐后退（Receding Convective Core），晚期依次嵌套形成氦核、碳氧核与约 $1.45\,M_\odot$ 的铁核，同时伴随强烈的星风质量损失。

### 4. 内部径向化学丰度剖面与“洋葱皮结构”（`fig4_internal_profiles_stages.png`）
* 对比了 $1.0\,M_\odot$ 从 TAMS（中心氢耗尽）到最终 CO 白矮星（内部 $95\%$ 质量为 $^{12}\text{C} + {}^{16}\text{O}$，外覆极薄氦/氢壳层）的剖面演化；
* 展示了 $15.0\,M_\odot$ 在铁核坍缩前夕经典的**“洋葱皮多层同心结构（Onion-Skin Structure）”**：从内向外依次为 $^{56}\text{Fe}$ 核 $\rightarrow$ $^{28}\text{Si}$ 层 $\rightarrow$ $^{16}\text{O}/^{20}\text{Ne}$ 层 $\rightarrow$ $^{12}\text{C}/^{16}\text{O}$ 层 $\rightarrow$ $^{4}\text{He}$ 层 $\rightarrow$ $^{1}\text{H}$ 包层。

### 5. 参数空间标度律与寿命对比（`fig5_parameter_space_scaling.png`）
* 验证了零龄主序的分段幂律质光关系（低质量 $L \propto M^{2.3}$、中等至大质量 $L \propto M^{3.5\sim 4.0}$），以及由此决定的主序寿命从 $0.3\,M_\odot$ 的逾 $200\,\text{Gyr}$（远超宇宙年龄 $13.8\,\text{Gyr}$）骤降至 $25\,M_\odot$ 的约 $7.2\,\text{Myr}$。

---

## 四、 工程文件清单与使用说明

本工程已在工作区生成完整的配置文件、模拟脚本、数据集、图表及交互式探索系统：

1. **MESA 配置文件模板与批量网格运行器（`mesa_configs/`）**
   * `inlist_template_low_intermediate`：低至中等质量恒星（$0.3-8.0\,M_\odot$）标准 MESA `inlist_project` 模板（包含 Ledoux 对流判据、指数超射、Reimers/Bloecker 星风及白矮星冷却终止条件）。
   * `inlist_template_massive`：大质量恒星（$15.0-25.0\,M_\odot$）标准 MESA `inlist_project` 模板（启用 `approx21.net` 21 核素 $\alpha$ 链反应网络、Dutch 星风方案与铁核坍缩速度阈值 `fe_core_infall_limit = 1d8`）。
   * `history_columns.list` & `profile_columns.list`：配置好的全局历史与内部剖面输出列定义。
   * `run_mesa_grid.py`：自动化构建 `mesa_grid_runs/` 下各 $(M, Z)$ 子目录并支持一键调用本地 MESA `./rn` 批量计算的脚本。
2. **参数空间物理引擎与 MESA 标准格式日志生成/读取器**
   * `stellar_grid_engine.py`：生成全网格 28 个模型（168 个关键阶段剖面）的 `stellar_grid_data.json`、`parameter_space_summary.csv`，并在 `mesa_grid_runs/*/LOGS/` 下输出与 MESA ASCII 格式完全一致的 `history.data`、`profiles.index` 与 `profile1.data`..`profile6.data`（内置 `MESALogsReader` 可无缝读取真实 MESA 输出）。
3. **出版级高清静态图集（`figures/`）**
   * `fig1_hr_diagram_grid.png` / `.svg`
   * `fig2_central_rho_T_phase.png` / `.svg`
   * `fig3_kippenhahn_comparison.png` / `.svg`
   * `fig4_internal_profiles_stages.png` / `.svg`
   * `fig5_parameter_space_scaling.png` / `.svg`
4. **交互式恒星演化参数空间探索器 Web 看板**
   * `stellar_explorer.html`：单文件零依赖 HTML5 交互式可视化系统，双击即可在任意浏览器中打开，支持自由切换 $(M, Z)$ 参数组合、拖动演化时间步滑块、自动播放演化动画、实时查看内部同心“洋葱皮”壳层渲染，以及直接拖拽导入本地 MESA `history.data` 文件。
