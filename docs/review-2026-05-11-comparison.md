# Review 交叉比对 — Claude vs. 另一份 review-2026-05-11.md

两份独立完成的 review：

- **A** = `docs/review-2026-05-11.md`（之前那份 AI 报告，下文称"A"）
- **B** = `docs/review-2026-05-11-claude.md`（Claude 独立报告，下文称"B"）

---

## 一句话结论

A 偏架构 / 风格 / 测试覆盖审查，**遗漏了两个会真实触发的 bug**；B 偏 bug 实证，**漏掉了 A 指出的几处合理设计观察**。两者互补，应当合并。

A 在第 7 节写"No crash-causing or data-corrupting bugs were found"——这个结论被 B 的 H1（实测会抛 TypeError）和 H2（log z 下 shared colorbar 颜色 / 刻度错位）**直接证伪**。

---

## 一对一比对

### 1. B 发现 / A 漏掉

| ID | 标题 | 严重度 | A 是否提到 |
|---|---|---|---|
| **H1** | secondary_contour 在 z/z2 NaN 模式不同时 `ax.contour` 形状不匹配抛异常 | High | ❌ 完全漏掉 |
| **H2** | shared colorbar + `ScaleOptions(z="log")` 把 LogNorm 丢失为 Normalize | High | ❌ A 的 2.4 接触到 `_shared_colorbar_mappable` 但只关心 cmap，没看到 norm 类型丢失 |
| **M1** | `_autoscale_compound_unit` 让 unscalable 组件（如 `c`）瓜分 weight，剩余 scalable 组件得不到完整 magnitude | Medium | ❌ A 提到测试覆盖不足，但没指出实际启发式偏差 |
| **M3** | 非数值 x/y 列导致底层 `astype(float)` 报 `could not convert string to float`（不是清晰报错） | Medium | ❌ |
| **M4** | EACH 模式下用户只设 `vmin` → limits **和** scale 双双全局化 | Medium | ❌ |

H1 / H2 是 B 在写报告前用最小可复现脚本验证过的，证据在 B 的 HIGH 章节。

### 2. A 发现 / B 漏掉

| A 编号 | 标题 | B 是否提到 |
|---|---|---|
| Design #1 | `api.py` 六个顶层函数高度重复，可工厂化 | ❌ B 没专门提 |
| Design #2 | `_draw_figures` 用 `*args/**kwargs` 仅为延迟导入，得不偿失 | ❌ |
| Design #3 | `_resolve_column_scale` 在 `matplotlib_axes.py` 和 `matplotlib_figure.py` 重复 | ❌ |
| Design #4 | `InputMap.secondary` 语义随 plot kind 变化 | ❌ |
| 2.3 | `_format_facet_part` 对未知列静默跳过 | ❌（B 在"不是 bug 的观察"里把它当作"优雅"，A 当作"会掩盖 typo"） |
| 2.5 | `LogNorm(vmin=None, vmax=None)` 行为依赖 matplotlib 版本 | ❌ |
| 3.1 | `_ordered_values` 在两个模块同名返回类型不同 | ❌ |
| 3.4 | `_UNSCALABLE_SYMBOLS = {"c"}` 没文档化 | ❌ |
| 5 | `pyproject.toml` 缺最小版本下限（`matplotlib>=3.5` 因为 `layout="constrained"`） | ❌ |
| 测试覆盖 | 多页 (`page>1`) 没在 render 层测试 | ❌ |

这些是真实的整洁度 / 可维护性意见，B 没单独列。

### 3. 双方都提到 — 框架相近

| 主题 | A 视角 | B 视角 | 一致性 |
|---|---|---|---|
| `_clean_csv_unit` 静默兜底 | A 2.2：用户拼错（"Mev"）会被吞 → 错单位 | B M2：CompoundUnit 自定义 separator 走 CSV 类型从 CompoundUnit 退化为 Unitless | 同一代码路径，两种触发场景，**结论一致**：应警告或拒绝 |
| `_prepare_heatmap_grid` 默认 `agg="mean"` | A 3.2：未文档化的隐式聚合 | B L2：静默聚合重复点 | 一致 |
| `_ordered_values` 排序失败兜底 | A 3.3：混合类型静默退回插入顺序 | B 未单列（读过但归到"不是 bug"） | A 更全面 |

### 4. 严重程度分歧

| 项 | A | B | 仲裁 |
|---|---|---|---|
| `_shared_colorbar_mappable` | A 标 Low（仅 per-subplot cmap 自定义场景） | B 标 High（log z 下色条刻度错） | B 有复现脚本，**更严重** |
| secondary_contour 路径 | A 测试覆盖里只提"tricontour/tripcolor 没测 SecondaryContourOptions" | B 直接复现形状不匹配 | B 是真 bug；A 的"覆盖不足"是同源问题的较弱表述 |
| `_format_facet_part` 跳过 | A Low | B "优雅" | 主观；A 的"掩盖 typo"角度更稳 |

### 5. 仅 A 提出的"高优"建议

A 的 "Recommendations" 表里把以下三项标为 High：

1. `_draw_figures` 直接对齐签名 — B 同意是改善但严重度更低（不影响行为）。
2. 统一 heatmap 网格排序逻辑（`sort_primary`） — B 同意，归 Low（行为最终正确）。
3. `_clean_csv_unit` 静默兜底加 warning — B **同意，并且**在 M2 强调应当连 CompoundUnit-separator 一并处理。

B 自己的 High 是 **H1 + H2**，两者都是会触发的运行时 bug，应当排在 A 的所有 High 之前。

---

## 我（Claude）的自我校准

读完 A 后觉得 B 漏掉的 **应当补进 B**：

- B 没专门强调 `api.py` 的重复模板 — 同意 A 是合理的整洁度意见。
- B 把 `_format_facet_part` 的列缺失兜底归为"优雅"，但 A 视为"掩盖 typo" — A 的角度更稳；面向用户的 API 不应静默忽略 typo。
- B 没看 `pyproject.toml` 是否带最小版本约束 — A 注意到了，是有效观察。

A 误判的我仍然坚持：

- A 第 7 节"无 crash / 数据损坏 bug"被 H1 和 H2 反例。
- A 的 2.4（`_shared_colorbar_mappable`）只看 cmap，但 norm 类型丢失才是真 bug。建议把 A 的 2.4 严重度从 Low 升到 High。

---

## 合并优先级表（建议）

| Pri | 来源 | 项 |
|---|---|---|
| **P0** | B-H1 | `_draw_secondary_grid_contour` 用主 subset 的 xs/ys + z2 全 df 的 z2_grid，NaN 模式不同就崩 |
| **P0** | B-H2 | shared colorbar 在 log z 下丢 LogNorm，色条线性化 |
| **P1** | A-2.2 + B-M2 | `_clean_csv_unit` 静默兜底；同时审视 CompoundUnit 自定义 separator 走 CSV 的退化 |
| **P1** | B-M1 | `_autoscale_compound_unit` 排除 unscalable 出 weight 池 |
| **P1** | A-Design #3 | 合并两份 `_resolve_column_scale` |
| **P2** | B-M3 | `_apply_scale` 对非数值列报清晰错误 |
| **P2** | B-M4 | EACH + user_override 时不要全局化 scale |
| **P2** | A-Design #1, #2 | `api.py` 模板化 + 去掉 `_draw_figures` 的 `*args/**kwargs` |
| **P3** | A-5 | `pyproject.toml` 加 `matplotlib>=3.5` 等下限 |
| **P3** | A-3.1, A-3.4 | 重命名 `_ordered_values`；README 文档化 `_UNSCALABLE_SYMBOLS` |
| **P3** | B-L1..L5 | scrub 项目 |

---

## 元评论（关于两份报告本身）

- A 写得更系统化（章节齐全：架构 / bug / 质量 / 测试 / 打包 / 推荐），适合作为基线 audit。
- B 写得更偏 root-cause（每条都跟最小复现挂钩），但漏掉了"软"项。
- 真正的发布前 review 最好两者并轨：一个跑结构化清单（A 的形态），一个抓边界 bug 并要求复现（B 的形态）。
