# 分镜计划器规则（先计划，后写稿）

计划器只产出结构化计划，不写最终分镜正文，不输出解释。

> 本分支成品布局为 `scene_shotlist`：plan 仍保留 `groups` / `duration` / `start` / `end` 用于节奏、主角和功能镜校验；writer 会把 plan 压平成“场景 + 连续镜头”，成品不显示分镜组与时长。

## 一、输入与输出

必读：

1. `storyboard-profile.json`（当前 profile）。
2. `参考资料/分镜细则/` 全部文件。
3. `work/source/epNN.md`（SOURCE，唯一事实源）。
4. `work/meta/source_dialogue.tsv`（台词台账，含无标签句）。
5. `work/meta/facts_lock.md`、`work/meta/handoff.json`（仅本集接点）。
6. `work/preflight/optimized/epNN.json`（本集修复记录，若有）。
7. `shot-profile.json`（导演层配置：主角模式、P/R/N 阈值、落点/意象/过渡开关）。
8. `work/meta/protagonist.json`（主角与别名，若存在）。
9. `work/preflight/protagonist.json`（本集 `scene_map`：哪些场次有主角在场，若存在）。
10. `shot-profile.json` 的 `gaze.active` 对应模块 `参考资料/分镜细则/gaze/{active}.md` 与 `05-gaze.md`（女性向/中性切换）。

输出：`work/storyboard/epNN_plan.json`，结构如下：

```json
{
  "ep": 1,
  "profile": "B_bilingual_full",
  "protagonist": {"name": "Nora", "aliases": [], "mode": "single"},
  "marks": {
    "landing": [
      {"scene": "1-1", "group": 1, "shots": [1], "handoff": "sound"}
    ],
    "gaze_beats": [
      {"group": 1, "shot": 1, "type": "micro_emotion", "note": "她听到名字时指尖停住"}
    ],
    "formal": [
      {"group": 1, "shot": 1, "type": "front", "purpose": "建立主角与空间"}
    ]
  },
  "scenes": [
    {
      "scene": "1-1",
      "heading": "1-1 日 外 城市街道",
      "cast": ["Nora", "Lina"],
      "groups": [
        {
          "no": 1,
          "duration": 12.0,
          "space_start": "本组 0.0 秒仍在场全部人物的站点、朝向、距离、参照物；摄影机位置与方向",
          "shots": [
            {
              "no": 1,
              "start": 0.0,
              "end": 3.0,
              "relation": "P",
              "anchor": "action",
              "subject": "Nora",
              "subject_type": "protagonist",
              "role": "story",
              "shot": "近景，右前侧，固定机位",
              "frame_range": "竖屏，Nora 胸部以上；Lina 在画外上方",
              "offscreen": "Lina 不入画",
              "action": "本镜实际动作、表演、反应、姿态与落幅",
              "dialogue": [
                {"sid": "EP01-D0003", "speaker": "Nora", "label": "对白", "text": "Lina!"}
              ],
              "tags": ["近景·固定·反应"]
            }
          ],
          "sound": "风声、脚步、呼吸",
          "prohibit": "无背景音乐，无字幕"
        }
      ]
    }
  ]
}
```

- `dialogue[].text` 必须是台账原文；拆分时每个片段各出现一次，按顺序拼回等于原文。
- `label` 只用 `对白 / VO / OS`（台账中的 `O.S.` 已归一为 OS）；源无标签时留空。
- `sid` 必填；同一 sid 可拆成多个片段，但必须连续、按序、无重复全文。
- `relation`/`anchor`/`subject`/`subject_type` 为导演层字段：P/R/N 与锚点定义见 `03-protagonist.md`；只写 plan，不写正文。
- `marks.landing` 每场一个，`shots` 用组内镜号；`marks.image`/`marks.transition` 只在 `shot-profile.json` 开启时填写。

## 二、规划顺序

1. **锁定事实**：按场读 SOURCE，列出人物、道具、动作结果、情绪变化、台词/OS/VO。
2. **分场**：沿用 SOURCE 场次，不增删场景。
3. **排真实时间**：
   - 英文按约 2—3 词/秒估算；中文按语义对应英文时长；
   - 先算台词/动作/反应的真实重叠时间，再切镜头；
   - 单镜 ≤4 秒，组 ≤15 秒，集 ≤150 秒。
4. **分组**：每组 3—5 镜（目标实际 3—5），同一连续发言优先同组；组间用动作/视线/声音/道具衔接。
5. **写空间起点**：本组 0.0 秒全部在场人物逐人写站点、朝向、距离、参照物；摄影机位置/方向；不得用“同上/承接上一/位置不变”。
6. **逐镜计划**：
   - 镜头给最能推进信息/情绪/关系的人，不机械跟说话者；
   - 相邻镜不得同主体+相近景别+同构图；
   - 写 `画面范围`、`画外锁定`（有则写）、动作、反应、台词、标签；
   - 关键动作链写触发—动作—接触—结果；
   - 倾听者有可见反应；
   - 开头/结尾用近景或特写，不用普通空镜（场间转场镜、新场首镜 ≤2.0 秒除外）。
7. **台词拆分**：
   - 超长句按标点/语义边界拆到连续镜头；
   - 极短回应不拆；
   - 拆分后每片只出现一次，拼回原文。
8. **自检**：时间求和、组/集上限、空间起点、台词覆盖、标签、无 `△/SPECTACLE/[EN]`。

## 二之二、主角与功能镜规划

在逐镜计划前，先做导演层规划；细节见 `03-protagonist.md` 与 `04-directing-marks.md`。

1. **主角贯穿线**：读 `work/meta/protagonist.json` 与 `work/preflight/protagonist.json`，逐场写“主角要什么 → 阻力 → 决定 → 状态变化”。
2. **先排 P**：首次揭示、决定、动作结果、情绪落点优先给主角本人。
3. **再排 R**：配角互动段必须通过 POV/过肩/前景/框内观察/手部物件/VO/OS/反应切/因果回切/声音桥锚定主角。
4. **最后排 N**：环境、奇观、纯配角段；连续 N ≤2，连续配角互动 N ≤2。
5. **功能镜预算**：先留场末落点（每场 1 个，重点场 1–2 镜）；`shot-profile.json` 开启意象/过渡/周正时再留对应预算：意象 2–3 个（纯空景 ≤1）、周正 2–3 个、过渡 1–2 个。
6. **自检比例**：`(P+R)/total ≥70%`、`P/total ≥35%`、`N/total ≤30%`、有主角在场场次至少 1 个 P/R；不达标先改计划。
7. **写 marks**：`marks.landing` 必填；`marks.image` / `marks.transition` / `marks.formal` 按配置决定是否填。
8. **写 gaze_beats**：`gaze.active=female` 时必填；每集至少 3 类、至少 1 个 `object`、1 个 `aftermath`；`group`/`shot` 必须指向真实镜头。

## 三、密度目标

- 每集 28—50 镜，6—12 组，约 4500—9000 中文字（B 含中英双语栏；A 只算英文+动作），均为生成目标；超过 9000 仅提示。单集总字符数（含所有标点、空格、换行）目标≤9000，9001—10000可通过；仅>10000为长度硬错误。planner 应按组估算并分配最终稿长度预算，writer 应在生成中逐组控制；返工触发限于硬错误且每集最多2次。
- 每个源 `△` 原子通常展开为 1.5—2.5 个镜头；不得把原子直接复制成镜头。
- 150 秒是硬上限，不是目标：短集按真实内容做 80—120 秒；不要为接近 150 秒加镜、加动作或加环境描写。
- 不为凑密度加无功能空镜、重复反应、装饰运镜。
- 功能镜预算：每集预留 2–6 镜给场末落点/意象/过渡；超预算时先砍过渡，再砍意象，最后才动落点；不得删台词或硬锁。

## 三之二、导演层硬约束

- `shot-profile.json` 的 `enabled=true` 时，每个镜头必须有 `relation`（P/R/N）与 `anchor`；缺字段按 N 统计并告警。
- 有主角在场的场次至少 1 个 P/R；连续 N ≤2；连续配角互动 N ≤2。
- 每个场景必须有 `marks.landing`；场末最后一镜 ≥2.5 秒（重点场收束 4–6 秒）；组末最后一镜 ≥2.0 秒。
- `image`/`transition` 只在 `directing.image_shots_per_ep` / `directing.transitions_per_ep` 开启时规划；未开启时不要加。
- `formal` 只在 `directing.formal_shots_per_ep` 开启时规划：每集 2–3 个，类型 `front/profile/symmetrical/eye_level`，同场 ≤2、不得连续。
- 开启意象时每集 2–3 个；`kind` 为 `object/borrowed/empty`，纯空景最多 1 个，至少 1 个 `object/borrowed`。
- `gaze.active != neutral` 时，`marks.gaze_beats` 必填：至少 3 类、至少 1 个 `object`、1 个 `aftermath`；类型只用 `agency/micro_emotion/object/distance/aftermath/non_objectifying`。
- P/R/N 与 marks 只写在 plan JSON，不写进成品正文。

## 四、返回

只回一行：`PLAN EPnn OK groups=G shots=S dur=D`；失败回 `PLAN EPnn FAILED: 原因`。
