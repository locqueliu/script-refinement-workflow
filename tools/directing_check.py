"""分镜导演层校验（0 token）。

校验：
- 主角 P/R/N 比例、连续段、场次覆盖、特写占比、关联点多样性；
- 场末落点（landing）；
- 意象镜（image）与场间过渡（transition），配置开启时才校验；
- 计划与成稿的镜头数/顺序/时间对账。

用法（由 storyboard_check.py 调用）：
    import directing_check as D
    fails, warns, stats = D.check_plan(plan, shot_profile)
"""
from __future__ import annotations

import re
from pathlib import Path

import common as C

P_ANCHORS = {
    "face", "eyes", "body", "action", "hand", "pov", "voice",
    "reaction", "decision",
}
R_ANCHORS = {
    "pov", "ots", "foreground", "frame", "observe", "object", "hand",
    "voice", "reaction", "cause", "sound", "reflection", "shadow",
}
N_ANCHORS = {"none"}
SUBJECT_TYPES = {"protagonist", "support", "environment", "prop", "spectacle"}
RELATIONS = {"P", "R", "N"}
HANDOFFS = {"sound", "eyeline", "action", "object", "match_cut"}
TRANSITION_TYPES = {"scene_cut", "time_jump", "location_change", "event_block"}
TRANSITION_TECHNIQUES = {"sound_bridge", "match_cut", "pov", "foreground", "empty_shot"}
GAZE_TYPES = {"agency", "micro_emotion", "object", "distance", "aftermath", "non_objectifying"}
FORBIDDEN_GAZE_TAGS = ("胸特写", "腿特写", "臀特写", "唇部特写", "胸部特写", "腿部特写")
CLOSEUP_RE = re.compile(r"特写")


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _marks(plan, key):
    root = plan.get("marks") or {}
    if not isinstance(root, dict):
        return []
    value = root.get(key) or []
    return value if isinstance(value, list) else []


def _shot_text(shot):
    parts = [shot.get("shot") or "", shot.get("action") or "",
             shot.get("frame_range") or "", " ".join(shot.get("tags") or [])]
    return " ".join(p for p in parts if p)


def _shot_duration(shot):
    try:
        return max(0.0, float(shot.get("end") or 0) - float(shot.get("start") or 0))
    except (TypeError, ValueError):
        return 0.0


def _protagonist(plan, profile=None, root=None):
    """Return (name, aliases, mode)."""
    name, aliases, mode = "", [], "single"
    prot = plan.get("protagonist")
    if isinstance(prot, dict):
        name = prot.get("name") or ""
        aliases = [x for x in (prot.get("aliases") or []) if x]
        mode = prot.get("mode") or mode
    elif isinstance(prot, str):
        name = prot
    if not name and isinstance(profile, dict):
        p = profile.get("protagonist") or {}
        if isinstance(p, dict):
            names = [x for x in (p.get("names") or []) if x]
            if names:
                name = names[0]
                aliases = names[1:]
            mode = p.get("mode") or mode
    if not name:
        root = Path(root or C.ROOT)
        data = C.load_json_safe(root / "work" / "meta" / "protagonist.json", {}) or {}
        if isinstance(data, dict):
            name = data.get("protagonist") or ""
            aliases = data.get("aliases") or []
            mode = data.get("mode") or mode
    return name, aliases, mode


def _names(name, aliases):
    return [x for x in [name] + list(aliases or []) if x]


def _cast_has(scene, names):
    cast = scene.get("cast") or []
    return any(C.has_name(x, names) for x in cast)


def iter_plan_shots(plan):
    """Yield (scene, group, shot, global_index)."""
    idx = 0
    for scene in plan.get("scenes") or []:
        for group in scene.get("groups") or []:
            for shot in group.get("shots") or []:
                idx += 1
                yield scene, group, shot, idx


def _find_shot(plan, group_no, shot_no):
    for scene in plan.get("scenes") or []:
        for group in scene.get("groups") or []:
            if int(group.get("no") or -1) != int(group_no):
                continue
            for shot in group.get("shots") or []:
                if int(shot.get("no") or -1) == int(shot_no):
                    return scene, group, shot
    return None, None, None


def _scene_last_shot(scene):
    last = None
    for group in scene.get("groups") or []:
        for shot in group.get("shots") or []:
            last = shot
    return last


def stats_from_plan(plan, profile=None, root=None):
    """Compute directing stats from plan metadata."""
    name, aliases, mode = _protagonist(plan, profile, root)
    names = _names(name, aliases)
    records = list(iter_plan_shots(plan))
    total = len(records)
    p = r = n = 0
    missing_relation = 0
    max_n_run = 0
    run = 0
    max_support_run = 0
    support_run = 0
    anchors = set()
    observe = 0
    p_closeup = 0
    all_closeup = 0
    related_duration = 0.0
    protagonist_duration = 0.0
    total_duration = 0.0
    first_p = None
    last_shot = records[-1][2] if records else None
    scene_ends = []

    per_scene = {}
    for scene, group, shot, idx in records:
        sname = scene.get("scene") or ""
        per_scene.setdefault(sname, {"scene": scene, "p": 0, "r": 0, "n": 0})
        rel = str(shot.get("relation") or "").upper()
        if rel not in RELATIONS:
            missing_relation += 1
            rel = "N"
        if rel == "P":
            p += 1
            if first_p is None:
                first_p = idx
        elif rel == "R":
            r += 1
        else:
            n += 1
        per_scene[sname][rel.lower()] += 1

        if rel == "N":
            run += 1
            max_n_run = max(max_n_run, run)
        else:
            run = 0

        if rel == "N" and str(shot.get("subject_type") or "") == "support":
            support_run += 1
            max_support_run = max(max_support_run, support_run)
        else:
            support_run = 0

        anchor = str(shot.get("anchor") or "")
        if rel in ("P", "R") and anchor:
            anchors.add(anchor)
        if rel == "R" and anchor == "observe":
            observe += 1

        text = _shot_text(shot)
        if CLOSEUP_RE.search(text):
            all_closeup += 1
            if rel == "P":
                p_closeup += 1

        dur = _shot_duration(shot)
        total_duration += dur
        if rel in ("P", "R"):
            related_duration += dur
        if rel == "P":
            protagonist_duration += dur

    # scene endings (last shot of each scene)
    for scene in plan.get("scenes") or []:
        groups = scene.get("groups") or []
        last = None
        for group in groups:
            for shot in group.get("shots") or []:
                last = shot
        if last is None:
            continue
        rel = str(last.get("relation") or "N").upper()
        scene_ends.append({
            "scene": scene.get("scene") or "",
            "cast_has_protagonist": _cast_has(scene, names) if names else False,
            "last_relation": rel,
            "last_duration": round(_shot_duration(last), 2),
        })

    scene_missing = []
    for sname, rec in per_scene.items():
        scene = rec["scene"]
        if names and _cast_has(scene, names) and rec["p"] + rec["r"] == 0:
            scene_missing.append(sname)

    related = p + r
    gaze_beats = _marks(plan, "gaze_beats")
    gaze_types = sorted({str(x.get("type")) for x in gaze_beats
                         if isinstance(x, dict) and x.get("type")})
    stats = {
        "protagonist": name,
        "protagonist_mode": mode,
        "total": total,
        "p": p,
        "r": r,
        "n": n,
        "related": related,
        "related_ratio": round(related / total, 3) if total else 0.0,
        "protagonist_ratio": round(p / total, 3) if total else 0.0,
        "n_ratio": round(n / total, 3) if total else 0.0,
        "max_n_run": max_n_run,
        "max_support_run": max_support_run,
        "scene_missing": scene_missing,
        "closeup_share": round(p_closeup / all_closeup, 3) if all_closeup else None,
        "anchor_variety": len(anchors),
        "observe_share": round(observe / related, 3) if related else 0.0,
        "first_p": first_p,
        "duration_share": round(related_duration / total_duration, 3) if total_duration else 0.0,
        "protagonist_duration_share": round(protagonist_duration / total_duration, 3) if total_duration else 0.0,
        "episode_last_relation": str(last_shot.get("relation") or "N").upper() if last_shot else "",
        "episode_last_duration": round(_shot_duration(last_shot), 2) if last_shot else 0.0,
        "scene_ends": scene_ends,
        "missing_relation": missing_relation,
        "shot_count": total,
        "image_count": len(_marks(plan, "image")),
        "transition_count": len(_marks(plan, "transition")),
        "landing_count": len(_marks(plan, "landing")),
        "gaze_beat_count": len(gaze_beats),
        "gaze_types": gaze_types,
    }
    return stats


def _add(fails, warns, msg, hard, enforce):
    if hard and enforce:
        fails.append(msg)
    else:
        warns.append(msg)


def _check_landing(plan, directing, enforce, fails, warns):
    landing_cfg = directing.get("landing") or {}
    if not landing_cfg.get("enabled", True):
        return
    scene_last_min = float(landing_cfg.get("scene_last_min", 2.5))
    group_last_min = float(landing_cfg.get("group_last_min", 2.0))
    major_total = landing_cfg.get("major_scene_total") or [4.0, 6.0]
    hook = landing_cfg.get("episode_hook") or [2.5, 4.0]
    marks = _marks(plan, "landing")
    marked_scenes = set()
    for item in marks:
        if not isinstance(item, dict):
            _add(fails, warns, "landing 标记不是对象", True, enforce)
            continue
        scene_no = item.get("scene") or ""
        group_no = item.get("group")
        shot_nos = item.get("shots")
        if shot_nos is None and item.get("shot") is not None:
            shot_nos = [item.get("shot")]
        shot_nos = [int(x) for x in _as_list(shot_nos) if str(x).isdigit()]
        if not scene_no or group_no is None or not shot_nos:
            _add(fails, warns, f"landing 标记缺 scene/group/shots：{item}", True, enforce)
            continue
        marked_scenes.add(scene_no)
        scene, group, shot = _find_shot(plan, group_no, shot_nos[-1])
        if shot is None:
            _add(fails, warns, f"landing 引用不存在的镜头 {scene_no} 分镜{group_no} 镜头{shot_nos[-1]}", True, enforce)
            continue
        handoff = str(item.get("handoff") or "")
        if handoff not in HANDOFFS:
            _add(fails, warns, f"landing {scene_no} handoff 非法：{handoff or '空'}", True, enforce)
        if _scene_last_shot(scene) is not shot:
            _add(fails, warns, f"landing {scene_no} 未指向场末最后一镜", True, enforce)
        total = sum(_shot_duration(_find_shot(plan, group_no, x)[2] or {}) for x in shot_nos)
        last = shot
        last_dur = _shot_duration(last)
        if item.get("major"):
            lo, hi = float(major_total[0]), float(major_total[1])
            if total < lo - 0.06:
                _add(fails, warns, f"landing {scene_no} 重点场收束 {round(total, 2)}s < {lo}s", True, enforce)
            if total > hi + 0.06:
                _add(fails, warns, f"landing {scene_no} 重点场收束 {round(total, 2)}s > {hi}s", False, enforce)
        if last_dur < scene_last_min - 0.06:
            _add(fails, warns, f"landing {scene_no} 末镜 {round(last_dur, 2)}s < {scene_last_min}s", True, enforce)

    # every scene should be marked
    for scene in plan.get("scenes") or []:
        sname = scene.get("scene") or ""
        if sname and sname not in marked_scenes:
            _add(fails, warns, f"场景 {sname} 缺场末 landing 标记", True, enforce)

    # group-level last shot duration (all groups)
    for scene in plan.get("scenes") or []:
        for group in scene.get("groups") or []:
            shots = group.get("shots") or []
            if not shots:
                continue
            dur = _shot_duration(shots[-1])
            if dur < group_last_min - 0.06:
                _add(fails, warns,
                     f"分镜{group.get('no')} 末镜 {round(dur, 2)}s < 组末落点 {group_last_min}s",
                     False, enforce)

    # episode hook
    records = list(iter_plan_shots(plan))
    if records:
        last = records[-1][2]
        rel = str(last.get("relation") or "N").upper()
        dur = _shot_duration(last)
        lo, hi = float(hook[0]), float(hook[1])
        if dur < lo - 0.06:
            _add(fails, warns, f"集末钩子 {round(dur, 2)}s < {lo}s", False, enforce)
        if dur > hi + 0.06:
            _add(fails, warns, f"集末钩子 {round(dur, 2)}s > {hi}s", False, enforce)
        if rel not in ("P", "R"):
            _add(fails, warns, f"集末钩子关系为 {rel}，建议 P/R", False, enforce)


def _check_mark_refs(plan, key, cfg, enforce, fails, warns, kind):
    max_count = 0
    if isinstance(cfg, (list, tuple)) and len(cfg) >= 2:
        max_count = int(cfg[1])
    if max_count <= 0:
        return
    marks = _marks(plan, key)
    if len(marks) < int(cfg[0]) or len(marks) > max_count:
        _add(fails, warns, f"{kind} 数量 {len(marks)} 不在 {cfg}", True, enforce)
    records = list(iter_plan_shots(plan))
    for item in marks:
        if not isinstance(item, dict):
            _add(fails, warns, f"{kind} 标记不是对象", True, enforce)
            continue
        gno, sno = item.get("group"), item.get("shot")
        if gno is None or sno is None:
            _add(fails, warns, f"{kind} 标记缺 group/shot：{item}", True, enforce)
            continue
        scene, group, shot = _find_shot(plan, gno, sno)
        if shot is None:
            _add(fails, warns, f"{kind} 引用不存在的镜头 分镜{gno} 镜头{sno}", True, enforce)
            continue
        idx = next((i for i, rec in enumerate(records) if rec[2] is shot), None)
        dur = _shot_duration(shot)
        if kind == "意象镜":
            if dur < 1.5 - 0.06 or dur > 3.0 + 0.06:
                _add(fails, warns, f"意象镜 分镜{gno}镜头{sno} 时长 {round(dur, 2)}s 不在 1.5–3.0s", True, enforce)
            if shot.get("dialogue"):
                _add(fails, warns, f"意象镜 分镜{gno}镜头{sno} 不应带台词", True, enforce)
            if not item.get("motif") or not item.get("source_basis"):
                _add(fails, warns, f"意象镜 分镜{gno}镜头{sno} 缺 motif/source_basis", True, enforce)
            if idx == 0:
                _add(fails, warns, "意象镜不应放在集首", True, enforce)
        else:
            if dur < 1.0 - 0.06 or dur > 2.0 + 0.06:
                _add(fails, warns, f"过渡镜 分镜{gno}镜头{sno} 时长 {round(dur, 2)}s 不在 1.0–2.0s", True, enforce)
            if shot.get("dialogue"):
                _add(fails, warns, f"过渡镜 分镜{gno}镜头{sno} 不应带台词", True, enforce)
            if str(item.get("type") or "") not in TRANSITION_TYPES:
                _add(fails, warns, f"过渡镜 分镜{gno}镜头{sno} type 非法：{item.get('type')}", True, enforce)
            technique = str(item.get("technique") or "")
            if technique and technique not in TRANSITION_TECHNIQUES:
                _add(fails, warns, f"过渡镜 分镜{gno}镜头{sno} technique 非法：{technique}", False, enforce)
            if not item.get("reason"):
                _add(fails, warns, f"过渡镜 分镜{gno}镜头{sno} 缺 reason", True, enforce)
            # scene boundary: first or last shot of a scene
            boundary = False
            for sc in plan.get("scenes") or []:
                sc_shots = [sh for g in (sc.get("groups") or []) for sh in (g.get("shots") or [])]
                if sc_shots and (sc_shots[0] is shot or sc_shots[-1] is shot):
                    boundary = True
                    break
            if not boundary:
                _add(fails, warns, f"过渡镜 分镜{gno}镜头{sno} 不在场界", True, enforce)


def _check_gaze(plan, profile, enforce, fails, warns):
    gaze = (profile or {}).get("gaze") or {}
    active = gaze.get("active", "neutral")
    if active == "neutral":
        return
    beats = _marks(plan, "gaze_beats")
    if not beats:
        _add(fails, warns, f"gaze={active} 但计划缺 gaze_beats", True, enforce)
        return
    types = set()
    for item in beats:
        if not isinstance(item, dict):
            _add(fails, warns, "gaze_beats 标记不是对象", True, enforce)
            continue
        t = str(item.get("type") or "")
        if t not in GAZE_TYPES:
            _add(fails, warns, f"gaze_beats type 非法：{t or '空'}", True, enforce)
            continue
        gno, sno = item.get("group"), item.get("shot")
        if gno is None or sno is None:
            _add(fails, warns, f"gaze_beats 缺 group/shot：{item}", True, enforce)
            continue
        if _find_shot(plan, gno, sno)[2] is None:
            _add(fails, warns, f"gaze_beats 引用不存在的镜头 分镜{gno} 镜头{sno}", True, enforce)
            continue
        types.add(t)
    if len(types) < 3:
        _add(fails, warns, f"gaze_beats 类型 {len(types)} < 3", True, enforce)
    if "object" not in types:
        _add(fails, warns, "gaze_beats 缺 object（手/物件情感镜）", True, enforce)
    if "aftermath" not in types:
        _add(fails, warns, "gaze_beats 缺 aftermath（情绪余波）", True, enforce)
    for _scene, _group, shot, _idx in iter_plan_shots(plan):
        text = _shot_text(shot)
        for tag in FORBIDDEN_GAZE_TAGS:
            if tag in text:
                _add(fails, warns, f"出现非客体化禁用标签：{tag}", False, enforce)


def check_plan(plan, shot_profile=None, root=None):
    """Return (fails, warns, stats)."""
    fails, warns = [], []
    profile = shot_profile or {}
    if not profile.get("enabled", True):
        return fails, warns, {}
    directing = profile.get("directing") or {}
    if not directing.get("enabled", True):
        return fails, warns, {}
    enforce = profile.get("mode", "warn") == "enforce"
    stats = stats_from_plan(plan, profile, root)

    if stats["missing_relation"]:
        _add(fails, warns, f"计划有 {stats['missing_relation']} 个镜头未标 relation", True, enforce)
    if stats["total"] and stats["missing_relation"] == stats["total"]:
        warns.append("计划未标注 P/R/N，跳过主角比例校验")
    else:
        th = profile.get("shots") or {}
        related_min = float(th.get("related_ratio_min", 0.70))
        p_min = float(th.get("protagonist_share_min", 0.35))
        n_max = float(th.get("n_ratio_max", 0.30))
        n_run_max = int(th.get("n_run_max", 2))
        support_max = int(th.get("support_run_max", 2))
        closeup_min = float(th.get("protagonist_closeup_share_min", 0.30))
        anchor_min = int(th.get("anchor_variety_min", 3))
        observe_max = float(th.get("observe_share_max", 0.30))

        if stats["related_ratio"] < related_min - 0.001:
            _add(fails, warns, f"主角关联占比 {stats['related_ratio']:.3f} < {related_min:.2f}", True, enforce)
        if stats["protagonist_ratio"] < p_min - 0.001:
            _add(fails, warns, f"主角本人镜占比 {stats['protagonist_ratio']:.3f} < {p_min:.2f}", True, enforce)
        if stats["n_ratio"] > n_max + 0.001:
            _add(fails, warns, f"非主角镜占比 {stats['n_ratio']:.3f} > {n_max:.2f}", True, enforce)
        if stats["max_n_run"] > n_run_max:
            _add(fails, warns, f"连续 N 镜 {stats['max_n_run']} > {n_run_max}", True, enforce)
        if stats["max_support_run"] > support_max:
            _add(fails, warns, f"连续配角互动 N 镜 {stats['max_support_run']} > {support_max}", True, enforce)
        if stats["scene_missing"]:
            _add(fails, warns, f"有主角在场但无 P/R 的场次：{', '.join(stats['scene_missing'])}", True, enforce)
        if stats["closeup_share"] is not None and stats["closeup_share"] < closeup_min - 0.001:
            _add(fails, warns, f"主角特写占比 {stats['closeup_share']:.3f} < {closeup_min:.2f}", True, enforce)
        if stats["anchor_variety"] < anchor_min:
            _add(fails, warns, f"关联点类型 {stats['anchor_variety']} < {anchor_min}", True, enforce)
        if stats["observe_share"] > observe_max + 0.001:
            _add(fails, warns, f"R-OBSERVE 占比 {stats['observe_share']:.3f} > {observe_max:.2f}", True, enforce)

    if stats["first_p"] is None:
        _add(fails, warns, "全集没有 P 镜", True, enforce)
    elif stats["first_p"] > 2:
        _add(fails, warns, f"首次 P 镜在第 {stats['first_p']} 镜（建议前 2 镜内）", False, enforce)
    if stats["duration_share"] < 0.65 - 0.001:
        _add(fails, warns, f"主角关联屏幕时间占比 {stats['duration_share']:.3f} < 0.65", False, enforce)
    if stats["protagonist_duration_share"] < 0.30 - 0.001:
        _add(fails, warns, f"主角本人屏幕时间占比 {stats['protagonist_duration_share']:.3f} < 0.30", False, enforce)

    _check_landing(plan, directing, enforce, fails, warns)
    _check_mark_refs(plan, "image", directing.get("image_shots_per_ep"), enforce, fails, warns, "意象镜")
    _check_mark_refs(plan, "transition", directing.get("transitions_per_ep"), enforce, fails, warns, "过渡镜")
    _check_gaze(plan, profile, enforce, fails, warns)
    return fails, warns, stats


def check_plan_draft(plan, ep, tol=0.06):
    """Compare plan shot structure against parsed draft. Return (fails, warns)."""
    fails, warns = [], []
    plan_groups = [g for sc in (plan.get("scenes") or []) for g in (sc.get("groups") or [])]
    ep_groups = ep.get("groups") or []
    if len(plan_groups) != len(ep_groups):
        fails.append(f"成稿分镜组数 {len(ep_groups)} ≠ 计划 {len(plan_groups)}")
    for pg in plan_groups:
        no = int(pg.get("no") or -1)
        eg = next((g for g in ep_groups if int(g.get("no") or -1) == no), None)
        if eg is None:
            fails.append(f"成稿缺分镜{no}")
            continue
        ps = pg.get("shots") or []
        es = eg.get("shots") or []
        if len(ps) != len(es):
            fails.append(f"分镜{no} 成稿镜头数 {len(es)} ≠ 计划 {len(ps)}")
        for a, b in zip(ps, es):
            if int(a.get("no") or -1) != int(b.get("no") or -1):
                fails.append(f"分镜{no} 镜头号不一致：计划{a.get('no')} / 成稿{b.get('no')}")
                continue
            for key in ("start", "end"):
                try:
                    av, bv = float(a.get(key) or 0), float(b.get(key) or 0)
                except (TypeError, ValueError):
                    continue
                if abs(av - bv) > tol:
                    fails.append(f"分镜{no} 镜头{a.get('no')} {key} 不一致：{av} / {bv}")
    return fails, warns


def summary(stats):
    if not stats or not stats.get("total"):
        return ""
    return (f"P{stats.get('p')}/R{stats.get('r')}/N{stats.get('n')} "
            f"related={stats.get('related_ratio')} p={stats.get('protagonist_ratio')} "
            f"n={stats.get('n_ratio')} nrun={stats.get('max_n_run')}")
