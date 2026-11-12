# Gaze 模块：女性向 / 中性 / 男性向切换

> 目标：把“受众镜头语法”做成独立模块，主契约、主角规则、事实锁不变；切换只改 `shot-profile.json` 的 `gaze.active`。

## 一、配置

```json
"gaze": {
  "active": "female",
  "modules": {
    "female": "参考资料/分镜细则/gaze/female.md",
    "male": "参考资料/分镜细则/gaze/male.md",
    "neutral": "参考资料/分镜细则/gaze/neutral.md"
  }
}
```

- `female`：女性观众情感代入优先；当前默认。
- `neutral`：不按性别偏置；保底。
- `male`：男性向；当前占位，未启用。

切换后 planner/writer 读对应模块；主文档只保留一句“读取当前 gaze 模块”。

## 二、Plan 标记

在 `epNN_plan.json` 的 `marks.gaze_beats` 写：

```json
{
  "group": 3,
  "shot": 2,
  "type": "object",
  "note": "她反复摩挲杯沿，没有抬头"
}
```

类型：

| 类型 | 用途 |
|---|---|
| `agency` | 她的判断/决定/行动组织镜头 |
| `micro_emotion` | 情绪三拍、微表情、呼吸、手部 |
| `object` | 手/物件情感载体 |
| `distance` | 关系距离/遮挡/负空间 |
| `aftermath` | 情绪落点后的余波 |
| `non_objectifying` | 明确反客体化的处理 |

## 三、硬约束

- 每集至少 3 类；至少 1 个 `object`；至少 1 个 `aftermath`；
- `group`/`shot` 必须指向真实镜头；
- 不新增台词、不新增剧情事实、不新增文化符号；
- 不得出现胸/腿/臀/唇孤立特写或打量式身体扫描；
- gaze 标记只写 plan，不写成品正文；
- `gaze.active=neutral` 时可省略 `gaze_beats`；`female`/`male` 时必须写。

## 四、校验

`tools/directing_check.py` 检查：

- `gaze_beats` 数量、类型、镜头引用；
- 至少 3 类、1 个 object、1 个 aftermath；
- 禁用标签；
- `mode=warn` 只报告；`mode=enforce` 才失败。

## 五、校准

- 先跑 2–3 集女频，人工看：主体性、情绪颗粒度、关系距离、物件、余波、非客体化；
- 稳定后再切 `enforce`；
- 不把“眼泪数量/慢动作数量”当指标。

## 六、男性向

`gaze/male.md` 先占位。开发时共享同一组维度（主体性、情绪、关系、镜头、节奏、奇观），只调权重，不复制女性向规则。
