# 恒星演化参数空间与 MESA 数值模拟技术报告 (v2.0 审计修订版)

## 1. 课题背景与设计目标
本报告针对“恒星演化模拟与 MESA 参数空间探索”课题，构建了一套兼顾天体物理严谨性与交互可视化体验的参数空间系统。系统覆盖初始质量 $M_{\text{init}} \in [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]\,M_\odot$ 与初始金属丰度 $Z_{\text{init}} \in [0.0001, 0.001, 0.014, 0.03]$ 的 28 组完整演化序列。

## 2. 恒星结构与演化核心控制方程（MESA 求解框架）
一维球对称流体静力学恒星演化由关于拉格朗日内部质量坐标 $m \in [0, M_*]$（或归一化坐标 $q = m/M_*$）的四组耦合偏微分方程控制：

1. **质量守恒方程**：
   $$\frac{\partial r}{\partial m} = \frac{1}{4\pi r^2 \rho}$$
2. **流体静力学平衡方程**：
   $$\frac{\partial P}{\partial m} = -\frac{G m}{4\pi r^4}$$
3. **能量守恒方程**：
   $$\frac{\partial L_r}{\partial m} = \epsilon_{\text{nuc}} - \epsilon_\nu + \epsilon_{\text{grav}}$$
4. **能量输运方程**：
   $$\frac{\partial \ln T}{\partial \ln P} = \nabla = \min(\nabla_{\text{rad}}, \nabla_{\text{ad}})$$
   其中辐射温度梯度为：
   $$\nabla_{\text{rad}} = \frac{3}{16\pi a c G} \frac{\kappa P L_r}{m T^4}$$

## 3. v2.0 关键物理修正与定标验证
| 质量区间 | 代表模型 | 核心混合与聚变机制 | 关键物理修正 (v2.0) | 终态残骸 |
| :--- | :--- | :--- | :--- | :--- |
| $M \le 0.35\,M_\odot$ | $0.3\,M_\odot$ | 全星对流混合 + pp-I 链 | 燃料比例修正为 $f_{\text{core}}=0.85$ ($t_{\text{MS}} \approx 787\,\text{Gyr}$)，径向丰度 $X_i(q)$ 全星平坦，末期经历蓝矮星收缩而非红巨星膨胀 | $\text{He WD}$ ($0.29\,M_\odot$) |
| $0.5\text{–}2.0\,M_\odot$ | $1.0\,M_\odot$ | 辐射核 + 对流包层，简并氦核氦闪 | 区分 ZAMS ($0.70\,L_\odot, 5600\,\text{K}$) 与今日 $4.57\,\text{Gyr}$ 太阳 ($1.0\,L_\odot, 5772\,\text{K}$) | $\text{CO WD}$ ($0.54\,M_\odot$) |
| $2.2\text{–}6.5\,M_\odot$ | $3.0, 5.0\,M_\odot$ | 对流核 + 辐射包层，非简并平稳氦点火（蓝环） | 修正蓝环有效温度随金属丰度 $Z$ 降低而向高温侧显著延伸的规律 | $\text{CO WD}$ ($0.70\text{–}0.85\,M_\odot$) |
| $7.0\text{–}9.5\,M_\odot$ | $8.0\,M_\odot$ | 超渐近巨星支（Super-AGB）偏心碳点火 | 引入金属丰度命运分岔：$Z \ge 0.014$ 形成 $\text{ONeMg WD}$；$Z \le 0.001$ 触发电子俘获超新星 (ECSN) 形成中子星 | $\text{ONeMg WD}$ / $\text{NS}$ |
| $M \ge 10\,M_\odot$ | $15.0, 25.0\,M_\odot$ | 完整核合成链 ($\text{H}\to\text{Fe}$) + 辐射压/电子散射 | 修正高光度端质光幂律展平 ($\text{slope}\approx 2.75$) 及铁核相对质量边界 $q_{\text{Fe}} = M_{\text{Ch,eff}}/M_{\text{final}}$ 缩放 | $\text{NS}$ ($1.46\,M_\odot$) / $\text{BH}$ ($2.95\,M_\odot$) |
