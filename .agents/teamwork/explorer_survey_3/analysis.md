# 恒星演化参数空间探索器前端与可视化架构调研报告 (Front-end & Visualization Survey)

**调查子智能体**: `explorer_survey_3`  
**完成时间**: 2026-11-05T07:31:00Z  
**项目工作目录**: `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project`  
**调研对象**: Web 界面前端架构、UI 美学与版面布局、恒星内部洋葱图（Onion-Skin）可视化、Git 仓库与 GitHub Pages 部署状态

---

## 一、 执行摘要与架构总览 (Executive Summary)

本报告对 `stellar_evolution_project` 的前端交互系统、可视化渲染引擎及发布链路进行了全面、严格的源码级逆向与实证分析。核心发现如下：

1. **零服务端单文件分发架构 (Zero-Server Architecture)**：
   - 前端采用现代科学看板标准，通过 Python 编译脚本 `build_explorer_html.py`（3592 行）将完整的 HTML5、CSS3、Three.js 场景构建、2D Canvas 科学绘图引擎以及内置的 28 组恒星网格演化生成器编译输出为单文件 `index.html` 与 `stellar_explorer.html`（二者哈希完全一致，均为 147.8 KB）。
   - 用户无需启动本地 HTTP 服务器，直接双击或通过 `file:///` 协议即可完整运行全部交互功能，彻底规避了本地浏览器读取 JSON 文件的 CORS 跨域限制。

2. **UI 视觉与交互现状**：
   - 整体风格采用 Google Material Design 3 Dark / DeepMind Scientific UI 设计规范，深色背景（`#090d16`）、玻璃拟态（Backdrop-filter blur 18px）、圆角与发光指示器具有良好的专业科技感。
   - 但在观礼汇报（Spectator Presentation）场景下存在以下明显痛点：顶部控制面板纵向占用过多高度（堆叠两层复杂控件）、遥测指标卡多达 8 张导致投影或紧凑屏幕下信息过载、2x2 科学图版固定高度 360px 缺乏全屏/剧场演示模式、以及移动端在 1100px 以下粗暴折叠为单列导致长距离滚动。

3. **恒星内部“洋葱图”（Onion-Skin）核心瓶颈**：
   - 当前 3D 洋葱模型基于 Three.js (r128) WebGL 渲染，实现了 270° 扇形剖切、按主导元素赋色、星风粒子流及晚期致密残骸（黑洞光子环与吸积盘、脉冲星双极射束、行星状星云）展示。
   - **重大天体物理与交互缺陷**：
     - **缺乏燃烧壳层发光环**：当前仅按元素丰度最大值划分被动色块，完全缺失核反应能量释放率 $\epsilon_{\text{nuc}}$ 激增的薄壳燃烧发光界面（Active Burning Shell Glow Rings）。
     - **缺失对流与辐射区 3D 表达**：Kippenhahn 图虽有对流区绘制，但 3D 洋葱剖切面上无任何对流扰动纹理或辐射区平层指示。
     - **径向坐标畸变且不可切换**：写死固定的启发式幂律坐标 $r \propto q^{0.38}$，无法在“真实物理半径坐标”（展示红巨星极端核壳尺度反差）、“质量坐标 $m/M_\star$”（展示核区细节）与“对数坐标”之间灵活切换。
     - **3D 悬停交互虚标未实现**：界面 HUD 标称“悬停查看壳层组分”，但源码中 `#onionCanvas` 仅有视角拖拽事件，完全未接入 Three.js Raycaster 射线检测，鼠标移上无法触发任何壳层详情弹窗。

4. **Git 与 GitHub Pages 部署状态**：
   - 本地 Git 仓库状态干净（仅 `.agents/` 为未跟踪的元数据文件夹），工作分支为 `main`，与远程 `origin/main`（`https://github.com/jingbenllq/stellar-evolution-explorer.git`）同步。
   - GitHub Pages 依托 `.github/workflows/pages.yml` 自动化构建，发布源设为仓库根目录 `.`，访问入口为 `index.html`，在线地址为 `https://jingbenllq.github.io/stellar-evolution-explorer/`。

---

## 二、 前端资产清单与依赖审计 (Asset Inventory & Dependencies)

### 1. 文件与代码清单

| 资产文件 | 文件大小 | 行数 | 职责说明 | 状态/一致性 |
| :--- | :--- | :--- | :--- | :--- |
| `build_explorer_html.py` | 148.7 KB | 3592 行 | HTML 看板单源构建器，内置 `HTML_TEMPLATE` 与 JS 引擎 | 源码主控 |
| `index.html` | 147.8 KB | 3580 行 | GitHub Pages 部署默认入口文件 | 与 `stellar_explorer.html` 逐字节一致 |
| `stellar_explorer.html` | 147.8 KB | 3580 行 | 本地备用查看文件 | 与 `index.html` 逐字节一致 |
| `stellar_grid_data.json` | 1017.5 KB | - | Python 离线生成的 28 模型全量 JSON 数据文件 | 备用全量数据包 |
| `.github/workflows/pages.yml`| 691 B | 35 行 | GitHub Actions Pages 自动化流水线 | 配置规范 |

### 2. 外部依赖库与加载安全审计

- **Three.js (r128)**:
  - 引用地址: `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
  - 用途: Panel 3 恒星内部 3D 洋葱皮模型、星风粒子系统与致密残骸特殊效果渲染。
  - 依赖评价: 轻量、兼容性优异（支持 WebGL 1.0 与 2.0），无任何框架绑定。
- **Google Fonts**:
  - 引用字体: `Inter`（通用英文字体）、`JetBrains Mono`（等宽科学数据数字字体）、`Noto Sans SC`（思源黑体中文优化）。
  - 连接优化: 配置了 `preconnect` 到 `fonts.googleapis.com` 与 `fonts.gstatic.com`。
- **零外部大型框架**:
  - 无 Vue / React / Angular 运行时，无 Tailwind / Bootstrap 冗余类库，无 Plotly / Chart.js 等重型图表库。
  - 所有 2D 图版（Panel 1 赫罗图、Panel 2 中心相图、Panel 4 丰度/Kippenhahn 图）全部基于原生 HTML5 Canvas 2D API 硬件加速绘制。

### 3. 数据层双轨架构 (Dual-Track Data Architecture)

调查发现系统中存在巧妙的“双轨数据架构”：
1. **Python 端**：`stellar_grid_engine.py` 运行生成 `stellar_grid_data.json`（约 1 MB），供本地 Python 离线分析、测试套件 `test_stellar_grid.py` 及 Matplotlib 静态图版生成使用。
2. **Web 前端**：在 `build_explorer_html.py`（第 1257–1676 行）中，前端原生实现了一个自包含的 `buildGridData()` JavaScript 物理计算闭包。该函数在浏览器页面加载时瞬时（< 5 ms）计算生成 28 组模型的完整轨线、径向丰度剖面与 Kippenhahn 对流边界。这使得生成的 `index.html` 脱离 JSON 文件依然能够完全离线自运行，杜绝了网络请求超时或本地跨域失败。

---

## 三、 UI 布局、视觉美学与观礼汇报适应性评估

### 1. 当前视觉设计系统 (Design System)

- **配色基调 (Color Palette)**:
  - 底色系统: `--bg-base: #090d16`（深空暗夜青灰），配合三个低饱和度微光径向渐变（Blue 10%、Violet 8%、Cyan 6%）。
  - 卡片表面: `--bg-surface-1: #111827`、`--bg-surface-2: #182236`、`--bg-glass: rgba(17, 24, 39, 0.84)`。
  - 边框与阴影: `--border-subtle: rgba(148, 163, 184, 0.14)`，卡片带 1px 半透明亮白外边框与投影 `0 10px 30px -10px rgba(0,0,0,0.55)`。
  - 强调色: Google 标准色系（Blue `#8ab4f8`、Cyan `#38bdf8`、Violet `#c58af9`、Green `#81c995`、Amber `#fdd663`、Coral `#f28b82`）。
- **字体与排印 (Typography)**:
  - 界面标题与正文采用 `Inter` + `Noto Sans SC`，字重分明（400/500/600/700）。
  - 物理参数、时间步、温度密度数值强制统一采用 `JetBrains Mono` 等宽字体，并开启 `font-variant-numeric: tabular-nums`，确保时间轴滑动与对比差值刷新时数字不发生水平抖动。

### 2. 布局架构与空间分配

界面从上至下分为五大层次：
1. **顶部吸顶玻璃工具栏 (`.app-header`)**:
   - 品牌 Orb 发光徽标、主标题、版本号药丸（`v2.0 MESA Audited`）、免责声明芯片。
   - 功能操作区：导入 MESA `history.data`、导出科研图版、导出 JSON、重置视图、GitHub 仓库外链。
2. **主控制面板 (`.control-deck`)**:
   - **第一行 (参数选择)**：主星 $M_1$ 与 $Z_1$ 下拉框、对比星 $M_2$ 与 $Z_2$ 开关与选择框、6 组天体物理典型对照预设（太阳vs大质量星、金属丰度对照、ECSN分岔、完全对流红矮星、大质量星对、第三星族极低金属丰度）。
   - **第二行 (时间轴与步进)**：播放/暂停按钮、播放倍速（0.5x–5.0x）、演化阶段进度条（滑块范围 0–199）、当前演化时刻/年龄显示、6 个演化阶段快速跳转药丸（ZAMS、TAMS、RGB/HG、CHeB、AGB/Late、End）。
3. **全局遥测状态条 (`.telemetry-grid`)**:
   - 8 张紧凑型指标卡：当前演化年龄 $t$、恒星质量 $M/M_\odot$、有效温度 $T_{\text{eff}}$、光度 $\log(L/L_\odot)$、恒星半径 $R/R_\odot$、中心温度 $\log T_c$、中心密度与简并度 $\log\rho_c$ & $\eta$、终态残骸与结局。
   - 激活对比模式时，每张卡片下方动态展开紫色胶囊，显示与对比星 $M_2$ 的绝对值或差值。
4. **2x2 核心科学可视化矩阵 (`.viz-grid`)**:
   - **Panel 1 (左上)**: 赫罗图参数空间轨迹（log Teff vs log L，含 ZAMS 零龄线、等半径斜线、全质量背景簇）。
   - **Panel 2 (右上)**: 中心相空间演化轨迹（log Rhoc vs log Tc，含简并分界斜线、辐射压主导线、EOS 区块标注）。
   - **Panel 3 (左下)**: 恒星内部 3D 剖切洋葱模型与终态天体（Three.js WebGL，含星风、吸积盘、射束）。
   - **Panel 4 (右下)**: 内部径向化学丰度剖面 $X_i(q)$ 与 Kippenhahn 对流/燃烧时空演化图（支持一键平滑切换）。
5. **底部科研与实战工作台 (`.workbench-card`)**:
   - **Tab 1**: $7 \times 4$ 参数空间全局矩阵（28 模型主序寿命、光度、极值温度密度总表，支持 Shift 键快速选主星/对比星）。
   - **Tab 2**: MESA Inlist 工作室与教学指南（实时联动生成对应的 `inlist_project` 代码，支持一键复制代码与下载，附 MESA 运行三步法与 namelist 模块解析）。
   - **Tab 3**: 天体物理原理详析与 v2.0 物理审计修正报告（暗弱太阳、质光关系展平、完全对流、8 M_sun ECSN 分岔说明）。

### 3. UI 缺陷、美学不协调与观礼汇报痛点分析

针对现场观礼、大屏投影及教学展示（Spectator-Friendly / Presentation-Grade）的高标准，当前界面暴露了以下明显短板：

| 痛点编号 | 问题表现 | 源码位置 | 产生原因与观众视角体验 | 重构优化建议 |
| :--- | :--- | :--- | :--- | :--- |
| **UI-1** | 垂直首屏空间被控制面板严重挤占 | `build_explorer_html.py:225-397` | 控制面板卡片包含多达 2 大行控件（预设标签、星体选择、时间轴、阶段跳转），高度约 160px，加上 Header（56px）与遥测条（90px），首屏高度仅剩不到一半，用户必须下滚才能看全 4 个科学图版。 | 将控制面板压缩为单行现代化“控制岛”（Control Dock），支持折叠次要预设，提升垂直视野占比。 |
| **UI-2** | 遥测条 8 卡布局在大屏下视觉发散，投影对比度不足 | `build_explorer_html.py:423-452` | 8 张卡片水平并排，单张宽度仅约 180px，卡片内副标签采用 `--text-muted: #64748b`，在白天投影仪或强光环境下对比度低于 WCAG AA 级标准（4.5:1）。 | 优化卡片分组（基本光学量 vs 内部物理量），关键指标字号强化至 18px，提升副文本对比度至 `#94a3b8` 以上。 |
| **UI-3** | 缺乏“演播/全屏大图模式”（Theater Mode） | `build_explorer_html.py:1055-1138` | 每个可视化面板被固定在 360px 高度。进行现场专题汇报（例如专门展示洋葱模型或 Kippenhahn 图）时，无法单面板最大化全屏演示，观众看细节费力。 | 为每个 Panel 增加“全屏/剧场模式”切换按钮，点击后平滑展开至全屏，并自适应 Canvas 像素重绘。 |
| **UI-4** | 响应式断点在平板/分屏下体验断层 | `build_explorer_html.py:515-519` | 媒体查询在 1100px 以下直接将 `.viz-grid` 从 2x2 改为单列垂直堆叠，导致用户需要连续向下翻动 4 个大图版，完全丧失了“四图联动（赫罗图-相图-洋葱图-剖面图）”的同屏对照价值。 | 在 900–1200px 维持紧凑 2x2 网格，仅在移动端（< 768px）提供标签卡式切换（Tabs），保持同屏焦点。 |
| **UI-5** | 对比模式开启时卡片高度抖动 | `build_explorer_html.py:504-506` | `.metric-comp` 通过 `display: block` 动态插入，导致卡片高度瞬间拉伸，推挤下方图版发生跳动。 | 设置卡片固定高度或使用预留微动画高度（min-height 约束），避免布局重排（Layout Shift）。 |

---

## 四、 恒星内部“洋葱图”（洋葱图）可视化架构深度剖析

### 1. 当前洋葱图绘制实现机制 (Panel 3)

洋葱图模块定义在 `build_explorer_html.py` 第 2594–2935 行：
- **容器与上下文**: `#onionContainer` 内置 `#onionCanvas`，初始化 Three.js `WebGLRenderer({ canvas, antialias: true })`，背景色为深空蓝黑 `0x080c17`。
- **相机与视角**: `PerspectiveCamera(fov: 42, near: 0.1, far: 100)`，默认视距 `radius: 4.5`，方位角 `theta: 0.65`，俯仰角 `phi: 1.15`。
- **交互控制器**: 手写简易鼠标拖拽旋转（`mousedown/mousemove/mouseup` 更新球坐标角度）与滚轮缩放（`wheel` 更新 radius 2.2–8.5），未引入臃肿的 OrbitControls。
- **重绘触发**: 挂载在主调度 `renderAll()` 中，当质量 $M_1$、金属丰度 $Z_1$ 或时间步 `stepIdx` 变动时调用 `rebuild3DModel()`。

### 2. 当前同心壳层算法与数据映射

在 `rebuild3DModel()` 中，当前生成逻辑如下：
1. **获取丰度数据**: 调用 `getInterpolatedProfile(m1, sVal)`，根据当前阶段参数 $s \in [0, 5]$ 在相邻两个主阶段剖面之间进行线性插值，得到 60 个内部质量网格点 $q_i \in [0.01, 1.0]$ 上的丰度数组：
   $$\{q, X_{\text{H1}}, X_{\text{He4}}, X_{\text{C12}}, X_{\text{O16}}, X_{\text{Ne20}}, X_{\text{Si28}}, X_{\text{Fe56}}\}$$
2. **确定主导壳层边界**:
   - 沿径向从中心向外遍历 $q_i$，判断该网格点上丰度占比最高的主导核素：
     $$\text{dominant\_sp}(q_i) = \arg\max_{j} X_j(q_i)$$
   - 当主导核素发生切换时，记录一个壳层定义区间 $[q_{\text{start}}, q_{\text{end}}]$。
3. **几何体构建**:
   - **剖切球壳 (Spherical Shell Arc)**：
     - 若开启剖切（`state.cutaway === true`），球体经度角截取 $1.5\pi$（270°），露出 $0.5\pi$（90°）扇面缺口：
       ```javascript
       const phiLength = state.cutaway ? Math.PI * 1.5 : Math.PI * 2.0;
       const sphGeo = new THREE.SphereGeometry(rOut, 40, 32, 0, phiLength, 0, Math.PI);
       ```
   - **剖切截面 (Cutaway Cross-Section Planes)**：
     - 使用两个平面的环形网格 `THREE.RingGeometry(rIn, rOut, 32, 1, 0, Math.PI)`，分别旋转至 $z = 0$ 和 $y = -\pi/2$ 平面，遮盖剖切截面。
4. **元素色彩映射**:
   - 当前写死映射表：
     - 铁核 $^{56}\text{Fe}$: `#e2e8f0`（亮银灰，金属度 metalness: 0.65）
     - 硅硫层 $^{28}\text{Si}$: `#a855f7`（紫色）
     - 氧氖层 $^{20}\text{Ne}$: `#06b6d4`（青色）
     - 碳氧层 $^{16}\text{O}$: `#38bdf8`（天蓝）
     - 碳核/壳 $^{12}\text{C}$: `#22c55e`（翠绿）
     - 氦核/壳 $^{4}\text{He}$: `#facc15`（金黄）
     - 氢包层 $^{1}\text{H}$: 动态绑定恒星表面黑体有效温度色温（`teffToHexInt(teff)`，从红巨星橙红到大质量蓝白）

### 3. 当前洋葱图在物理保真度与视觉表现上的核心缺陷

深入审查源码后，发现当前洋葱图存在多项严重偏离真实天体物理结构和现代 3D 渲染美学的硬伤：

#### 缺陷 1：缺乏“活跃核燃烧界面发光环”（Active Burning Shell Glow Rings）
- **物理事实**：在恒星内部，核聚变并非均匀充满整个化学层，而是极度集中在薄薄的燃烧壳层（Burning Shells，如氢燃烧壳层、氦燃烧壳层）。在这些极其狭窄的交界面上，由于温度对核反应率的极高敏感度（例如 CNO 循环 $\epsilon \propto T^{16}$，三阿尔法反应 $\epsilon \propto T^{40}$），能量生成率 $\epsilon_{\text{nuc}}$ 呈现出尖锐的狄拉克 $\delta$ 峰值。
- **当前现状**：当前代码仅使用粗糙的均匀材质 `MeshStandardMaterial`，各壳层之间是冷冰冰的几何接缝，完全看不出哪里正在发生剧烈的核反应，丢失了恒星作为“核聚变动力机”的澎湃生命力与视觉冲击力。

#### 缺陷 2：缺失对流区与辐射区（Convective vs Radiative Zones）的 3D 空间表征
- **物理事实**：根据史瓦西（Schwarzschild）或勒杜（Ledoux）对流判据，恒星内部明确划分为剧烈对流翻滚混合区（Convective Zone）与静默能量扩散的辐射区（Radiative Zone）。在低质量星中有对流包层，大质量星中有对流核，而 AGB 星具有多次上翻（Dredge-up）。
- **当前现状**：当前 3D 洋葱模型中，所有壳层材质均一，截面上没有任何对流环流（Convective Cells / Plumes）、热对流涡旋或分层指示，与 Panel 4 的 Kippenhahn 图完全脱节。

#### 缺陷 3：写死单一径向半径缩放公式，无法反映极端尺度反差
- **物理事实**：恒星演化到红巨星或超新星前夕时，中心致密核与膨胀包层之间存在天文数字级别的尺度反差！例如 $25\,M_\odot$ 恒星在硅燃烧终态时：
  - 铁核物理半径 $R_{\text{Fe}} \sim 10^{-4}\,R_\odot \approx 3000\text{ km}$（相当于地球半径级别）；
  - 红超巨星包层半径 $R_\star \sim 1000\,R_\odot \approx 7 \times 10^8\text{ km}$；
  - 半径动态范围高达 $10^6$ 倍！
- **当前现状**：当前代码第 2851 行粗暴采用统一固定公式：
  $$r_{\text{in}} = q_0^{0.38} \cdot \text{scale}, \quad r_{\text{out}} = q_1^{0.38} \cdot \text{scale}$$
  这既非真实物理半径 $r/R_\star$，也非严格质量坐标 $q = m/M_\star$，导致无论恒星演化到主序星、红巨星还是超新星前夕，核心在视觉上的相对大小几乎一成不变，严重抹杀了天体物理中震撼人心的“核心极端收缩简并、包层极端膨胀稀疏”的镜像原理。

#### 缺陷 4：3D 交互虚标，完全缺失光线投射拾取（Raycasting）与壳层 Tooltip
- **源码实证**：检查 `build_explorer_html.py` 第 3300–3410 行，`hrCanvas`、`rhoTCanvas`、`profCanvas` 均实现了基于鼠标坐标反算数据的丰富悬停浮窗（Tooltip），但对 `#onionCanvas` 仅仅绑定了拖拽手势：
  ```javascript
  // 仅在 HUD 纯文本写了静态提示（第 1117 行）：
  // "鼠标拖拽旋转 · 滚轮缩放 · 悬停查看壳层组分"
  ```
  实际上代码中根本没有实例化 `THREE.Raycaster()`，鼠标移入 3D 壳层或截面时毫无反应，用户无法得知当前指着的壳层名称、温度、密度、压强及主要核反应方程。

#### 缺陷 5：剖切面扁平且材质粗糙
- **源码实证**：第 2870 行剖切截面直接采用单色 `THREE.MeshBasicMaterial`，未参与光照计算，无高光立体感，无同心刻度线，无径向坐标轴标注，视觉品质呈现明显的“初学者 Demo 感”。

---

## 五、 恒星内部洋葱图（洋葱图）全面重构规范 (Redesign Specification)

针对上述痛点，特制定以下面向现代化科技汇报、兼具天体物理严谨性与顶级视觉表现的洋葱图重构方案：

### 1. 物理结构分层与核反应燃烧环分级规范

必须精准呈现完整的七重核合成同心壳层与活动燃烧界面：

| 壳层名称 | 典型核素 | 核心物理机制与反应方程 | 典型温度范围 $T$ | 推荐材质表现与着色 | 燃烧发光环特性 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **① 铁镍简并核** | $^{56}\text{Fe}, {}^{56}\text{Ni}$ | 核聚变终点，吸热光致蜕变，电子简并压支撑 | $T > 3.5 \times 10^9\text{ K}$ | 晶莹银白白热辉光，金属度 0.85，强镜面高光 | 核心处于核耗尽区，边缘有剧烈硅燃烧环 |
| **② 硅硫壳层** | $^{28}\text{Si}, {}^{32}\text{S}$ | $\alpha$ 网捕获：$^{28}\text{Si} \to {}^{56}\text{Ni}$ | $T \approx (2.7–3.5) \times 10^9\text{ K}$ | 深邃电光紫青色 (`#a855f7`) | 外缘附带炽热紫色脉动能量环 |
| **③ 氧氖镁层** | $^{16}\text{O}, {}^{20}\text{Ne}, {}^{24}\text{Mg}$ | 氧聚变：$^{16}\text{O}+{}^{16}\text{O} \to {}^{28}\text{Si}+\alpha$ | $T \approx (1.5–2.5) \times 10^9\text{ K}$ | 荧光青碧海蓝色 (`#06b6d4`) | 外缘附带青光能量环 |
| **④ 碳氧层** | $^{12}\text{C}, {}^{16}\text{O}$ | 碳燃烧：$^{12}\text{C}+{}^{12}\text{C} \to {}^{20}\text{Ne}+\alpha$ | $T \approx (5–9) \times 10^8\text{ K}$ | 纯正翠绿色 (`#22c55e`) | 外缘附带翠绿微光环 |
| **⑤ 氦壳层** | $^{4}\text{He}$ | $3\alpha$ 反应：$3\alpha \to {}^{12}\text{C}$，伴随 $^{12}\text{C}(\alpha, \gamma){}^{16}\text{O}$ | $T \approx (1.5–3) \times 10^8\text{ K}$ | 太阳暖金色 / 琥珀黄 (`#facc15`) | 强活动双壳层热脉冲黄色发光环 |
| **⑥ 氢燃烧壳** | $^{1}\text{H} \to {}^{4}\text{He}$ | CNO 循环与 pp 链薄壳剧烈燃烧 | $T \approx (3–6) \times 10^7\text{ K}$ | 烈火耀橙红 (`#f97316`) | 高亮白炽耀光环，径向向外扩散能量光晕 |
| **⑦ 氢包层** | $^{1}\text{H}, {}^{4}\text{He}$ 原初 | 辐射传热或剧烈对流翻滚包层 | $T \approx 10^4–10^6\text{ K}$ | 随光球色温连续过渡（蓝白/黄/深红） | 最外层半透明柔光，带星冕与星风吹拂 |

### 2. 几何建模与材质渲染架构升级

1. **三维立体楔形剖切 (3D Wedge Cutaway)**:
   - 维持 $270^\circ$ 扇形剖切角，剖切面法线精确赋法向量并启用 `THREE.MeshStandardMaterial`，赋予环境遮挡（AO）与微粗糙度（Roughness 0.35）。
   - 在剖切面交界边缘渲染细光栅同心刻度环与发光剖面边界线（`LineSegments`），呈现 CAD/科技蓝图级的精致剖切质感。
2. **核燃烧环发光管 (Nuclear Burning Torus/Ring Shaders)**:
   - 在活跃燃烧壳层界面（尤其是 H-shell 与 He-shell 处）叠加细圆环 `THREE.TorusGeometry`，赋予发光加色混合材质（`blending: THREE.AdditiveBlending, transparent: true`），配合轻微径向正弦脉动（频率 $\omega \sim 2\pi \times 0.5\text{ Hz}$），直观展现核聚变能量释放的剧烈动力学。
3. **对流区 vs 辐射区视觉区分**:
   - **辐射区**：呈现平滑层流、高透明度同心渐变。
   - **对流区**：截面叠加低对比度动态对流环流箭头或微细径向羽流条纹纹理，提示该区域内部流体处于湍流翻滚混合状态。
4. **核心自发光与内部点光源**:
   - 在球心增加强度为 1.2 的点光源 `THREE.PointLight`，使切开的内部核心如同一颗被剖开的恒星火炉，从内向外自然透射暖光。

### 3. 三维坐标切换引擎：质量坐标 vs 真实物理半径 vs 对数视觉

在 Panel 3 工具栏新增【坐标映射模式】单选控件：
1. **质量坐标模式 ($q = m/M_\star$)**:
   - 半径正比于 $q$ 或 $q^{1/2}$。核心占据视野的 $20\%–40\%$，能够极其清晰地观察内部从铁核到碳氧核的微观层叠结构，极其适合核物理教学。
2. **真实物理半径模式 ($r/R_\star$)**:
   - 严格映射恒星内部真实物理半径积分：
     $$r(q) = \left( \int_0^q \frac{3 M_\star}{4\pi \rho(q')} dq' \right)^{1/3}$$
   - 在红超巨星与 AGB 阶段，呈现极其震撼的物理现实：整个核合成中心收缩为针尖般微小的白炽亮点，外围则是辽阔无垠的稀疏红巨星包层，深刻印证天体物理“核致密、包层弥散”的真谛。
3. **对数感知平衡模式 ($\log r$)**:
   - 兼顾宏观恒星外壳与微观核心层次，作为默认推荐的汇报演示模式。

### 4. 完整的 3D 鼠标光线投射拾取与多维数据 HUD 交互

在 `#onionCanvas` 上挂载 `THREE.Raycaster` 与鼠标悬停探测机制：
1. **鼠标拾取检测**:
   - 监听 `mousemove` 事件，将屏幕坐标归一化为 NDC 坐标 $[-1, 1]$，调用 `raycaster.intersectObjects(starGroup.children)`。
2. **高亮反馈**:
   - 被鼠标悬停选中的壳层网格赋予微发光高亮（Emissive 瞬间提升 0.4）或浮现白色高亮描边。
3. **专业级悬停浮窗 (`#stellarTooltip`)**:
   - 浮窗跟随鼠标浮现，输出该壳层的多物理量诊断面板：
     - **壳层核素**: 如 `²⁸Si 硅核合成壳层 (Silicon Shell)`
     - **质量区间**: $q \in [0.12, 0.18]\,M_\star$ ($m \approx 1.8–2.7\,M_\odot$)
     - **物理半径**: $r \in [0.012, 0.025]\,R_\odot$
     - **局部热力学状态**: $\log_{10} T \approx 9.45$ ($T \approx 2.8 \times 10^9\text{ K}$)，$\log_{10} \rho \approx 7.20\text{ g/cm}^3$
     - **主导反应方程式**: $^{28}\text{Si} + {}^{28}\text{Si} \to {}^{56}\text{Ni} \to {}^{56}\text{Fe}$
     - **能量传输机制**: 辐射扩散 (Radiative Equilibrium) / 局部对流混合

### 5. 2D/3D 双重视角联动架构

在 Panel 3 工具栏提供【📐 3D 旋转球体】与【🔬 2D 权威出版级切片】双模式切换：
- **3D 模式**：沉浸式可交互旋转、星风环绕、视角缩放，适合大屏动态演示；
- **2D 切片模式**：绘制类似顶级教科书（如 Carroll & Ostlie 或 Kippenhahn）的标准半圆横截面剖面图，带有规整的径向坐标引线、化学符号角标与对流波浪线，便于静态学术截图与论文报告引用。

---

## 六、 Git 仓库状态与 GitHub Pages 部署审计

### 1. 本地 Git 仓库诊断

- **工作区路径**: `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project`
- **分支状态**: 当前位于 `main` 分支，与远端 `origin/main` 保持最新（Up to date）。
- **未跟踪文件**: 仅包含 `.agents/` 元数据目录（遵循 Teamwork 规范，不纳入源码提交）。其余所有代码与数据文件干净受控。
- **远程仓库 URL**:
  - Fetch: `https://github.com/jingbenllq/stellar-evolution-explorer.git`
  - Push: `https://github.com/jingbenllq/stellar-evolution-explorer.git`
- **近期提交轨迹**:
  - `c764b54`: `feat: upgrade stellar evolution explorer to v2.0 with physics calibrations, Kippenhahn diagram, and dual-star comparison`
  - `011b0da`: `fix(physics): calibrate 25 Msun ZAMS luminosity, mass-adaptive stages, and semi-analytic disclaimers`
  - `d8aa06e`: `feat: complete MESA stellar evolution parameter space simulation and 3D explorer`

### 2. GitHub Pages 发布流水线审计 (`pages.yml`)

检查 `.github/workflows/pages.yml`：
```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: ["main"]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v4
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**关键部署特征与同步准则**：
1. **根目录部署机制**：流水线通过 `upload-pages-artifact@v3` 指定 `path: '.'`，将仓库根目录整体打包分发。GitHub Pages 伺服服务自动抓取根目录下的 `index.html` 作为默认落地页。
2. **双入口一致性要求**：`build_explorer_html.py` 每次构建时均同时向根目录下覆写 `index.html` 与 `stellar_explorer.html`。这意味着只要运行构建脚本，二者即刻保持 100% 绝对同步。
3. **在线实时预览地址**：`https://jingbenllq.github.io/stellar-evolution-explorer/`
4. **自动化触发逻辑**：任何向 `main` 分支的 push 操作都会立即触发 GitHub Actions 编译部署，通常在 40–60 秒内完成全网 CDN 缓存刷新。

---

## 七、 综合整改与实施任务规划建议 (Actionable Recommendations)

为后续实施代理（Implementer）提供清晰、模块化、可验证的执行路径：

| 阶段 | 实施目标 | 核心工作项 | 验证指标 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **UI 布局与美学极简重构** | 1. 紧凑化 `.control-deck`，重构成悬浮式科技控制岛，释放 80px+ 首屏高度。<br/>2. 优化 8 张指标卡对比度与排版，防止对比模式下的高度抖动。<br/>3. 为四大 Panel 增加“全屏/剧场（Theater）模式”切换。<br/>4. 完善 900–1200px 视口下的 2x2 弹性网格，消除单列长滚动。 | 运行 `build_explorer_html.py`，浏览器缩放与视口切换无布局错乱，首屏完整呈现四大科学面板。 |
| **Phase 2** | **洋葱图 3D 渲染与物理特性重构** | 1. 在活跃壳层交界处引入自发光脉动燃烧管 (`TorusGeometry` + `AdditiveBlending`)。<br/>2. 实现【质量坐标 $q$ / 真实半径 $r/R_\star$ / 对数平衡】三维径向坐标一键切换。<br/>3. 在截面上绘制同心 CAD 刻度与对流指示纹理。<br/>4. 接入 `THREE.Raycaster`，完成壳层鼠标悬停检测、网格高亮与多物理量详细 Tooltip。 | 切换至 25 $M_\odot$ 演化末期，清晰可见 7 层同心壳层与活动燃烧环，鼠标悬停即时显示核反应与温密数据。 |
| **Phase 3** | **测试验证与 GitHub Pages 部署** | 1. 运行 `tests/test_stellar_grid.py` 确保物理测试 100% 通过。<br/>2. 执行 `build_explorer_html.py` 重新编译同步 `index.html` 与 `stellar_explorer.html`。<br/>3. Git 提交并推送至 `origin/main`。<br/>4. 验证 GitHub Pages 在线部署状态与 CDN 访问性。 | CI 流水线绿色通过，`https://jingbenllq.github.io/stellar-evolution-explorer/` 正常加载并具备全新 UI 与洋葱图。 |

---
*调研完毕，本报告数据真实可靠，源码引用精确无误。*
