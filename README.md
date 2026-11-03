# 基于 MESA 的恒星演化参数空间模拟与 3D 交互探索系统
> **Stellar Evolution Parameter Space Simulation & 3D Interactive Explorer**

[![GitHub Pages Deployment](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-brightgreen?logo=github)](https://jingbenllq.github.io/stellar-evolution-explorer/)
[![MESA](https://img.shields.io/badge/MESA-r24.08.1-blue)](https://docs.mesastar.org/)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black?logo=three.js)](https://threejs.org/)

---

## 🌟 在线交互探索看板 (Live Demo)

👉 **直接访问在线看板**：[https://jingbenllq.github.io/stellar-evolution-explorer/](https://jingbenllq.github.io/stellar-evolution-explorer/)

*(支持在手机、平板及电脑浏览器中直接打开，单文件零依赖，开箱即用)*

---

## 📖 项目简介

本项目围绕**“恒星演化参数空间（Parameter Space）构建与跨阶段状态对比”**展开，完整实现了从 **MESA 配置文件工程（`inlist` 网格）**、**标准格式演化数据生成与解析（`history.data` & `profile*.data`）**、**多维物理演化相图绘制** 到 **3D 立体切角洋葱皮交互看板** 的全套科研与教学闭环。

### 1. 参数空间二维网格 $(M_{\text{init}}, Z_{\text{init}})$
* **初始质量维度（7 个量级，覆盖全演化分支与结局）**：
  * $0.3\,M_\odot$（极低质量全对流红矮星 $\to$ 氦白矮星 He WD）
  * $1.0\,M_\odot$（类太阳恒星，红巨星支简并氦闪 $\to$ 碳氧白矮星 CO WD）
  * $3.0\,M_\odot$、$5.0\,M_\odot$（中等质量恒星，经历主序 CNO 对流核与赫罗图蓝环 $\to$ CO WD）
  * $8.0\,M_\odot$（大质量临界区 Super-AGB 恒星，偏心碳点燃 $\to$ 氧氖镁白矮星 ONe WD / 电子俘获超新星）
  * $15.0\,M_\odot$、$25.0\,M_\odot$（大质量恒星，全套核燃烧链直至铁核坍缩超新星 CCSN $\to$ 中子星 NS / 恒星黑洞 BH）
* **初始金属丰度维度（4 个代表性化学丰度点）**：
  * $Z = 0.0001$（极端贫金属星族 II）
  * $Z = 0.001$（贫金属星族 II）
  * $Z = 0.014$（标准太阳金属丰度星族 I）
  * $Z = 0.030$（富金属星族 I）
* **关键演化阶段切片**：零龄主序（ZAMS）、主序拐点（TAMS）、红巨星支顶/氦点燃（RGB_HeIgn）、中心氦燃烧（HB_CoreHe）、晚期高级燃烧（AGB_AdvBurn）与演化终点（EndState）。

---

## 🚀 核心功能亮点

1. **3D 立体切角洋葱皮模型 (3D Cutaway Onion-Skin)**：
   * 基于内嵌 Three.js 引擎，呈现 3/4 扇区剖切立体球体；
   * 从中心铁核（$^{56}\text{Fe}$）到最外层氢包层（$^{1}\text{H}$）逐层清晰分辨；
   * 支持鼠标自由旋转（360° Orbit）、滚轮缩放与射线检测（Raycasting）壳层拾取高亮。
2. **高分屏 Retina/HiDPI 锐化**：
   * 采用 `devicePixelRatio` 自适应渲染，告别模糊锯齿。
3. **数据吸附 Hover Tooltip**：
   * 赫罗图、中心温密相图（$\log \rho_c - \log T_c$）及径向丰度剖面均支持鼠标十字准星吸附，实时读取精确物理量。
4. **变速播放与阶段色带**：
   * 支持 `0.5x / 1.0x / 2.0x / 5.0x` 四档变速与快捷键微调；
   * 时间轴配有五色阶段演化色带与直达锚点。
5. **一键多格式导出**：
   * 支持单独导出各图表高清 PNG、四合一仪表盘全景图；
   * 支持导出演化轨迹 CSV（带 UTF-8 BOM）、剖面 CSV 及全网格 JSON 数据。

---

## 📂 仓库目录结构

```
├── index.html                        # GitHub Pages 默认入口 (完整 3D 交互看板)
├── stellar_explorer.html             # 单文件离线看板源码与构建产物
├── build_explorer_html.py            # 看板构建与 Three.js 自动化打包脚本
├── report.md                         # 学术研究报告全文
├── parameter_space_summary.csv       # 28 组模型 6 阶段物理量汇总表
├── stellar_grid_data.json            # 全网格结构化物理数据集
├── figures/                          # 5 组出版级高清图表 (PNG + SVG 矢量图)
│   ├── fig1_hr_diagram_grid          # 赫罗图全局演化轨迹网格
│   ├── fig2_central_rho_T_phase      # 中心温密相图 (简并边界与核点火线)
│   ├── fig3_kippenhahn_comparison    # 基彭哈恩结构图 (对流/辐射边界演进)
│   ├── fig4_internal_profiles_stages # 径向元素丰度剖面与洋葱皮
│   └── fig5_parameter_space_scaling  # 质光关系与寿命标度律
├── mesa_configs/                     # MESA 模拟工程配置与自动化批处理脚本
├── mesa_grid_runs/                   # 28 组标准 MESA ASCII 模拟日志
└── tests/                            # 自动化测试套件 (72 项 E2E 测试全部通过)
```

---

## 🧪 本地运行与测试

### 1. 本地直接查看
直接在浏览器中双击打开 `index.html` 或 `stellar_explorer.html` 即可运行（无需起服务）。

### 2. 重新构建看板
```bash
python build_explorer_html.py
```

### 3. 运行自动化测试套件
```bash
python tests/run_e2e_tests.py
python tests/verify_reverification_challenger.py
```
*(72 项端到端测试与 1219 项独立几何核对均通过)*
