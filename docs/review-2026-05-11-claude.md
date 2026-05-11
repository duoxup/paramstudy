# paramstudy 独立代码 Review — Claude (2026-05-11)

Reviewer：Claude (Opus 4.7)
范围：`src/paramstudy/**`, `tests/**`, `examples/**`（全部 0.1.0 代码）
方法：通读 ~2,500 行源码 + ~1,250 行测试，针对怀疑点构造最小可复现案例验证。

本报告独立完成，未参考 `docs/review-2026-05-11.md`。最后会做交叉比对。

---

## 摘要

| 级别 | # | 已验证 |
|---|---|---|
| HIGH（会在现实使用中触发） | 2 | ✅ 复现 |
| MEDIUM（边界/启发式不准/语义意外） | 4 | 部分验证 |
| LOW / 风格 | 5 | — |

总体印象：代码组织清晰，dataclass-based 选项分层合理，测试覆盖核心 API 路径。问题主要集中在 (a) 渲染层与数据空集 / 缺失值的交互、(b) shared colorbar 与 log z 的耦合、(c) 复合单元 autoscale 启发式在含 unscalable 组件时退化。

---

## HIGH

### H1. secondary_contour 在 z 与 z2 NaN 模式不同时形状错乱

文件：`src/paramstudy/render/matplotlib_axes.py:134-180` (`draw_heatmap_axes`), `:464-491` (`_draw_secondary_grid_contour`)

`draw_heatmap_axes` 先用 `subset = df[[x_col, y_col, z_col]].dropna()` 计算主网格的 `xs, ys, z_grid`。随后调用 `_draw_secondary_grid_contour(ax, df, xs, ys, ...)` 时把 **完整 df** 传入，函数内再次调用 `_prepare_heatmap_grid(df, primary, secondary, z2_col, options)`，由 z2 的非 NaN 行重新计算 xs/ys 并构造 `z2_grid`。但函数 **丢弃** z2 自己的 xs/ys，反而把主网格的 `xs, ys` 喂给 `ax.contour(xs, ys, z2_grid)`。

- 当 z 与 z2 的非 NaN 唯一坐标集相同：尺寸刚好对齐 → 跑得过去（现有两个测试都是这种情形）。
- 当二者的非 NaN 唯一坐标集长度不同：`TypeError: Length of x (3) must match number of columns in z (4)`。
- 当长度相同但具体值不同：**静默** 把 z2 网格画到错位的 x/y 坐标上。

最小复现：

```python
df = pd.DataFrame({
    'x': [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4],
    'y': [10]*4 + [20]*4 + [30]*4,
    'z':  [1, 2, 3, np.nan, 4, 5, 6, np.nan, 7, 8, 9, np.nan],  # x=4 永远 NaN
    'z2': [10, 20, 30, 40, 15, 25, 35, 45, 20, 30, 40, 50],
})
# → TypeError: Length of x (3) must match number of columns in z (4)
```

`_draw_secondary_tri_contour` (`matplotlib_axes.py:493-518`) 走的是独立 dropna 路径（不依赖共享 xs/ys），所以不受影响。

修复建议：在 `_draw_secondary_grid_contour` 内用 `[primary, secondary, z2_col]` 的子集自行计算 xs2/ys2/z2_grid，然后传给 `ax.contour(xs2*x_mult, ys2*y_mult, z2_grid)`。

---

### H2. Shared colorbar (FIGURE/ROW/COL) 与 `ScaleOptions(z="log")` 不兼容

文件：`src/paramstudy/render/matplotlib_figure.py:441-452` (`_shared_colorbar_mappable`), `matplotlib_axes.py:428-444` (`_apply_color_limits`)

`_apply_color_limits` 在 z=log 时给每个子图的 mappable 配 `LogNorm`，但 `_shared_colorbar_mappable` 在合并时无条件用 `Normalize(...)` 构造新的 `ScalarMappable`，丢弃了 LogNorm。

实证（图形渲染正常，但 colorbar 的 yscale 是 linear）：

```
#cbar axes: 1
  cbar yscale = linear
Subplot mappable norms:
  LogNorm: vmin=10.0, vmax=1e8
  LogNorm: vmin=10.0, vmax=1e8
```

后果：子图按 log 着色，但 colorbar 的刻度按线性显示 → 数值与色彩对应错乱。

修复建议：在 `_shared_colorbar_mappable` 中检查 `items[0][0].norm` 类型；若是 `LogNorm` 则用 `LogNorm(min(vmins), max(vmaxs))`。更稳的写法是直接复用 `type(items[0][0].norm)`。

---

## MEDIUM

### M1. CompoundUnit autoscale 在含 unscalable 组件时退化

文件：`src/paramstudy/scale.py:170-264` (`_autoscale_compound_unit`)

启发式把总倍率 `M_left` 按 `target_mult = M_left**w` 分配到每个未 pin 的组件，其中 `w = abs(dim) / unpinned_weight`。`unpinned_weight` 计入了 `_UNSCALABLE_SYMBOLS`（如 `c`）的维度，但 unscalable 组件强制 multiplier=1.0 → 实际乘积达不到 `M_left`。

实证（1000 MeV/c 值，期望显示 GeV/c）：

```
unit = CompoundUnit([SimpleUnit('eV', MEGA), SimpleUnit('c', dimension=-1)])
resolve_compound_scale([1000, 1100, 1200], unit)
→ unit = 'MeV/c', multiplier = 1.0   # 仍然显示成 1000 MeV/c
```

理想结果应是 GeV/c，multiplier=1e-3。功能上不崩，但 unit-aware autoscale 的初衷被削弱。

`tests/test_scale.py::test_resolve_compound_scale_c_stays_fixed` 只断言 `c` 留在 NONE 前缀，不检查 `eV` 端是否合理重缩放，所以现有测试覆盖不到这个回归。

修复建议：在计算 `unpinned_weight` 与 `n_total` 时排除 `_UNSCALABLE_SYMBOLS` 的组件，把全部 magnitude 让 scalable 组件承担。

---

### M2. CompoundUnit 自定义 `separator` 在 CSV 往返时丢失类型

文件：`src/paramstudy/metadata.py:261-268` (`_clean_csv_unit`), `unit.py:236-238` (`parse_unit`)

`CompoundUnit(separator='.')` 渲染为 `"mm.mrad"`，但 `parse_unit` 只识别空格作为乘法分隔符。CSV 读取时 `parse_unit("mm.mrad")` 抛 `ValueError`，被 `_clean_csv_unit` 兜底为 `Unitless(label="mm.mrad")`。

实证：

```
原: CompoundUnit(separator='.') -> render "mm.mrad"
CSV 重建后: Unitless, render "mm.mrad"   # 类型从 CompoundUnit 变成 Unitless
```

后果：scale-aware 行为全部失效（autoscale 直接 short-circuit 为 multiplier=1）。JSON 路径正确（`unit_to_dict` 显式存了 separator）。

修复建议：要么在 CSV 路径上同样存 separator（用单独列或更结构化的格式），要么把默认 separator 限定为空格并对自定义 separator 报警/拒绝写入 CSV。

---

### M3. 非数值 x/y 列触发底层 `astype(float)` 错误而非清晰报错

文件：`src/paramstudy/render/matplotlib_axes.py:381-383` (`_apply_scale`)

`_resolve_column_scale` 对非数值列返回 `None`（正确），但 `_apply_scale` 仍执行 `values.astype(float).to_numpy()`：

```python
draw_line_axes(ax, df, spec)  # x='mode'，df['mode'] = ['A','B','C',...]
→ ValueError: could not convert string to float: 'A'
```

API 没有文档化"仅支持数值列"。建议在 `PlotSpec.validate` 或 `_require_columns` 中检查 dtype，给出明确错误。

---

### M4. `_resolve_slot_color_settings` 在 EACH + user_override 时把限制 / scale 全部全局化

文件：`src/paramstudy/render/matplotlib_figure.py:386-403`

```python
if mode in (ColorbarMode.NONE, ColorbarMode.EACH) and not user_override:
    # per-slot scale, limits=None
    ...
    return result

if mode in (ColorbarMode.NONE, ColorbarMode.EACH, ColorbarMode.FIGURE):
    # global limits AND global scale from full df
    limits, scale = _column_limits_and_scale(df, column, meta, axes_options)
    return {slot.index: _ColorSlotSettings(limits, scale) for slot in plan.slots}
```

用户对 EACH 模式只设置 `vmin=0`（未触发 user_override 时本意是仅覆盖一边），但因为 `user_override = vmin is not None or vmax is not None`，整个分支被切换到 "全局 limits + 全局 scale"，连 vmax 也变成全局 max。

修复思路：在 user_override 时仍走 per-slot，但用 vmin/vmax 覆盖各 slot 自动计算的对应边。

---

## LOW

### L1. `_resolve_contour_levels` 把 `int N` 转成 `linspace(..., N+1)`

`matplotlib_axes.py:447-453`。原本 matplotlib `contour(levels=N)` 表示画 N 条线，这里若 `color_limits` 非空就改成 N+1 个边界 → N+1 条等高线。语义偏移。

### L2. `_prepare_heatmap_grid` 默认 `agg="mean"` 静默聚合重复点

`matplotlib_axes.py:421-425`。同一 (x,y) 多行被 mean 聚合，没有警告。对于"应当唯一"的规则网格输入，静默掩盖了数据问题。

### L3. `_autoscale_simple_unit` 用 `np.nanmedian(finite[finite>0])`

`scale.py:128`。对对称分布在 0 附近的数据，正值中位数会偏倚。极端情形（全负数）会触发 `finite[finite>0].size == 0` 路径正常退化，但 `nanmedian` 实际上对已过滤后的数组没必要再用 nan-aware。

### L4. `ColumnMetaRegistry.from_dict` 在缺失 `type` 字段时静默接受

`metadata.py:115`：`payload.get("type") not in (None, cls._TYPE)`。读取任意 JSON dict（不带类型标记）也会成功，破坏了版本化序列化的契约。

### L5. `ColumnMeta.from_csv_row` 的 `row.get("unit", "").strip()` 假设值非 None

`metadata.py:61,63`。`csv.DictReader` 在标准用法下不会给出 None，但若调用者构造 dict 时传入 `{"unit": None}` 会抛 AttributeError。属于内部假设，但没有 type-narrow。

---

## 测试覆盖观察

- `tests/test_matplotlib_figure.py` 对 shared colorbar 有不少断言，但所有测试都用 linear z scale，所以 H2 没被发现。
- `tests/test_matplotlib_axes.py` 的 secondary_contour 用例没有引入 NaN，所以 H1 没被发现。
- 没有针对 `_autoscale_compound_unit` 在 "scalable + unscalable 混合" 时最终 multiplier 是否合理的回归测试。
- 没有 dtype 校验测试（非数值列输入的行为）。

---

## 不是 bug 的观察（仅供参考）

- 整体 API（dataclass 选项、frozen、`field(default_factory=...)`）一致性好。
- `_subset_for_slot` 与 planner 的语义衔接正确：planner 用 dropna 后的 unique values 决定页面/行/列，render 端用 `==` 过滤一致。
- 复合单元的 JSON `unit_to_dict`/`unit_from_dict` 严格往返，且包含负维度的回归测试 (`test_compound_with_neg_dim_roundtrip`)。
- `_format_facet_part` 在 column 不在 df 中时跳过 scale，行为优雅。

---

## 优先级建议

1. **H1**：影响范围窄但触发即崩，**修**。3 行代码搞定。
2. **H2**：用户启用 log z 又用 shared colorbar 时一定踩到，**修**。
3. **M2**：罕见但静默退化为 Unitless 会让单位换算整体失效，**修**或在 `to_csv` 时拒绝非空格 separator。
4. **M1**：启发式改进，**择期**。
5. **M3 / M4**：错误体验问题，可顺带改善。
6. **L1–L5**：scrub 时清理。
