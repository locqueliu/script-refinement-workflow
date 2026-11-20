"""竖屏分镜稿硬校验（0 token）。

支持两种布局：
- `timed`：分镜组 + 镜头时间轴；
- `scene_shotlist`：场景 + 连续镜头（镜头1…N，不显示分镜组与时长；内部时间由 plan 校验）。

校验目标：结构、空间起点、声音/禁止字段、台词标签（含 O.S./VO/OS）、
禁用旧字段与占位词；以及 shot-profile.json 开启时的主角 P/R/N、场末落点、
意象/过渡标记和计划-成稿对账。

用法：
  python tools/storyboard_check.py --docx 测试/目标稿.docx
  python tools/storyboard_check.py --dir work/storyboard
  python tools/storyboard_check.py --eps 1,2 --report-only
  python tools/storyboard_check.py --dir work/storyboard --no-directing
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import directing_check as D

GROUP_RE = re.compile(r"^分镜\s*(\d+)\s*[（(]\s*时长\s*[：:]\s*([0-9]+(?:\.[0-9]+)?)\s*秒\s*[）)]")
GROUP_SOP_RE = re.compile(r"^分镜\s*(\d+)\s*[｜|]\s*预计\s*([0-9]+(?:\.[0-9]+)?)\s*秒")
SHOT_RE = re.compile(r"^镜头\s*(\d+)\s*[（(]\s*([0-9]+(?:\.[0-9]+)?)\s*[—\-–~]\s*([0-9]+(?:\.[0-9]+)?)\s*秒\s*[）)]")
SHOT_LIST_RE = re.compile(r"^镜头\s*(\d+)\s*$")
SCENE_RE = re.compile(r"^(\d+)[-－](\d+)\s+")
CAST_RE = re.compile(r"^(?:人物|出场人物)\s*[：:]")


def new_ep(no):
    return {"no": no, "scenes": [], "groups": [], "raw": []}


def new_scene(heading):
    return {"heading": heading, "cast": [], "space_start": "", "sound": "",
            "prohibit": "", "shots": [], "tags": [], "action": [], "dialogues": []}


def new_group(no, duration):
    return {"no": no, "duration": duration, "space_start": "", "sound": "",
            "prohibit": "", "shots": [], "tags": [], "action": [], "dialogues": []}


def new_shot(no, start, end):
    return {"no": no, "start": start, "end": end, "frame_range": "", "offscreen": "",
            "tags": [], "action": [], "dialogues": []}


def parse(lines, profile):
    layout = profile.get("layout") == "scene_shotlist"
    episodes = []
    ep = None
    scene = None
    group = None
    shot = None
    for raw in lines:
        s = C.normalize_line(raw)
        if not s:
            continue
        n = C.episode_number(s)
        if n is not None:
            ep = new_ep(n)
            episodes.append(ep)
            scene = group = shot = None
            ep["raw"].append(s)
            continue
        if ep is None:
            continue
        ep["raw"].append(s)
        if SCENE_RE.match(s):
            scene = new_scene(s)
            ep["scenes"].append(scene)
            group = shot = None
            continue
        if CAST_RE.match(s):
            if scene is not None:
                scene["cast"] = [x.strip() for x in re.split(r"[、,，\s]+", s.split("：", 1)[-1].split(":", 1)[-1]) if x.strip()]
            continue

        if layout:
            m = SHOT_LIST_RE.match(s)
            if m:
                if scene is not None:
                    shot = new_shot(int(m.group(1)), None, None)
                    scene["shots"].append(shot)
                continue
            if re.match(r"^空间(?:起点)?\s*[：:]", s) and scene is not None:
                scene["space_start"] = re.sub(r"^空间(?:起点)?\s*[：:]\s*", "", s)
                continue
            if s.startswith("画面范围") and shot is not None:
                shot["frame_range"] = re.sub(r"^画面范围\s*[：:]\s*", "", s)
                continue
            if s.startswith("画外锁定") and shot is not None:
                shot["offscreen"] = re.sub(r"^画外锁定[^：:]*[：:]\s*", "", s)
                continue
            if re.match(r"^(?:声音设计|声音)\s*[：:]", s) and scene is not None:
                scene["sound"] = re.sub(r"^(?:声音设计|声音)\s*[：:]\s*", "", s)
                continue
            if re.match(r"^(?:硬性禁止|禁止)\s*[：:]", s) and scene is not None:
                scene["prohibit"] = re.sub(r"^(?:硬性禁止|禁止)\s*[：:]\s*", "", s)
                continue
            if s.startswith("【"):
                (shot or scene or ep).setdefault("tags", []).append(s)
                continue
            rec = C.parse_storyboard_dialogue(s)
            if rec:
                rec["line"] = s
                (shot or scene or ep).setdefault("dialogues", []).append(rec)
                continue
            (shot or scene or ep).setdefault("action", []).append(s)
            continue

        m = GROUP_RE.match(s) or GROUP_SOP_RE.match(s)
        if m:
            group = new_group(int(m.group(1)), float(m.group(2)))
            ep["groups"].append(group)
            shot = None
            continue
        m = SHOT_RE.match(s)
        if m:
            if group is not None:
                shot = new_shot(int(m.group(1)), float(m.group(2)), float(m.group(3)))
                group["shots"].append(shot)
            continue
        if re.match(r"^空间(?:起点)?\s*[：:]", s) and group is not None:
            group["space_start"] = re.sub(r"^空间(?:起点)?\s*[：:]\s*", "", s)
            continue
        if s.startswith("画面范围") and shot is not None:
            shot["frame_range"] = re.sub(r"^画面范围\s*[：:]\s*", "", s)
            continue
        if s.startswith("画外锁定") and shot is not None:
            shot["offscreen"] = re.sub(r"^画外锁定[^：:]*[：:]\s*", "", s)
            continue
        if re.match(r"^(?:声音设计|声音)\s*[：:]", s) and group is not None:
            group["sound"] = re.sub(r"^(?:声音设计|声音)\s*[：:]\s*", "", s)
            continue
        if re.match(r"^(?:硬性禁止|禁止)\s*[：:]", s) and group is not None:
            group["prohibit"] = re.sub(r"^(?:硬性禁止|禁止)\s*[：:]\s*", "", s)
            continue
        if s.startswith("【"):
            (shot or group or ep).setdefault("tags", []).append(s)
            continue
        rec = C.parse_storyboard_dialogue(s)
        if rec:
            rec["line"] = s
            (shot or group or ep).setdefault("dialogues", []).append(rec)
            continue
        (shot or group or ep).setdefault("action", []).append(s)
    return episodes


def check_ep_shotlist(ep, profile, plan=None, shot_profile=None):
    """校验 scene_shotlist 布局：场景 + 连续镜头，无分组/时长。"""
    fails, warns = [], []
    scenes = ep.get("scenes") or []
    if not scenes:
        fails.append("没有场次行")
        return fails, warns
    if any(re.match(r"^分镜\s*\d+", x) for x in ep.get("raw") or []):
        fails.append("scene_shotlist 成品不应出现 分镜N / 分镜时长")
    if any(re.match(r"^镜头\s*\d+\s*[（(]", x) for x in ep.get("raw") or []):
        fails.append("scene_shotlist 成品不应出现 镜头时间")
    total_shots = 0
    for sc in scenes:
        label = (sc.get("heading") or "")[:20]
        if not sc.get("cast"):
            warns.append(f"场次 {label} 缺人物/出场人物行")
        if not sc.get("space_start"):
            fails.append(f"场次 {label} 缺空间起点")
        else:
            if len(sc["space_start"]) < 10:
                fails.append(f"场次 {label} 空间起点过短")
            for phrase in profile.get("space_forbid_phrases", []):
                if phrase in sc["space_start"]:
                    fails.append(f"场次 {label} 空间起点含省略词「{phrase}」")
        if not sc.get("sound"):
            fails.append(f"场次 {label} 缺声音设计/声音")
        if not sc.get("prohibit"):
            fails.append(f"场次 {label} 缺禁止项")
        shots = sc.get("shots") or []
        if not shots:
            fails.append(f"场次 {label} 没有镜头")
            continue
        for j, sh in enumerate(shots, 1):
            if sh.get("no") != j:
                fails.append(f"场次 {label} 镜头编号不连续：第{j}镜写作镜头{sh.get('no')}")
            if not sh.get("action") and not sh.get("dialogues"):
                warns.append(f"场次 {label} 镜头{sh.get('no')} 没有动作或台词")
        total_shots += len(shots)

    s_lo, s_hi = int(profile["shots_per_ep"][0]), int(profile["shots_per_ep"][1])
    if total_shots > s_hi:
        fails.append(f"镜头数 {total_shots} 超出目标上限 {s_hi}")
    elif total_shots < s_lo:
        warns.append(f"镜头数 {total_shots} 低于目标下限 {s_lo}")

    for token in profile.get("forbid_tokens", []):
        if token == "△":
            if any(x.startswith("△") for x in ep["raw"]):
                fails.append("出现禁用符号 △")
        elif token in "\n".join(ep["raw"]):
            fails.append(f"出现禁用字段/标记：{token}")
    if profile.get("language") == "english":
        cn = sum(1 for sc in scenes for sh in sc.get("shots", [])
                 for d in sh.get("dialogues", []) if d.get("lang") == "cn")
        if cn:
            fails.append(f"A profile 出现 {cn} 行中文台词（只保留英文）")

    cjk = C.cjk_count("\n".join(ep["raw"]))
    c_lo, c_hi = int(profile["cjk_per_ep"][0]), int(profile["cjk_per_ep"][1])
    if cjk > c_hi:
        warns.append(f"中文字数 {cjk} 超过目标上限 {c_hi}，仅作提示，不作为失败条件")
    elif cjk < c_lo:
        warns.append(f"中文字数 {cjk} 低于目标下限 {c_lo}")
    t_target = int(profile.get("total_chars_target", 9000))
    t_hi = int(profile.get("total_chars_per_ep", 10000))
    total = C.total_char_count(ep.get("source_text") or "\n".join(ep["raw"]))
    if total > t_hi:
        fails.append(f"单集总字符数 {total} 超出硬上限 {t_hi}（含标点/空格/换行），必须打回压缩")
    elif total > t_target:
        warns.append(f"单集总字符数 {total} 超过目标 {t_target}，建议压缩")

    if plan and shot_profile and shot_profile.get("enabled", True):
        df, dw = D.check_plan_draft(plan, ep, layout="scene_shotlist")
        fails.extend(df)
        warns.extend(dw)
    return fails, warns


def check_ep(ep, profile, plan=None, shot_profile=None):
    if profile.get("layout") == "scene_shotlist":
        return check_ep_shotlist(ep, profile, plan, shot_profile)
    fails, warns = [], []
    tol = float(profile.get("time_tolerance", 0.06))
    groups = ep["groups"]
    if not groups:
        fails.append("没有分镜组")
        return fails, warns
    for i, g in enumerate(groups, 1):
        if g["no"] != i:
            fails.append(f"分镜编号不连续：第{i}组写作分镜{g['no']}")
        if not g["space_start"]:
            fails.append(f"分镜{g['no']} 缺空间起点")
        else:
            if len(g["space_start"]) < 10:
                fails.append(f"分镜{g['no']} 空间起点过短")
            for phrase in profile.get("space_forbid_phrases", []):
                if phrase in g["space_start"]:
                    fails.append(f"分镜{g['no']} 空间起点含省略词「{phrase}」")
        if not g["sound"]:
            fails.append(f"分镜{g['no']} 缺声音设计/声音")
        if not g["prohibit"]:
            fails.append(f"分镜{g['no']} 缺禁止项")
        dur = g["duration"]
        if dur <= 0 or dur > float(profile["group_max"]) + tol:
            fails.append(f"分镜{g['no']} 时长 {dur} 超出组上限 {profile['group_max']}")
        shots = g["shots"]
        if not shots:
            fails.append(f"分镜{g['no']} 没有镜头")
            continue
        expected = 0.0
        total = 0.0
        for j, sh in enumerate(shots, 1):
            if sh["no"] != j:
                fails.append(f"分镜{g['no']} 镜头编号不连续：第{j}镜写作镜头{sh['no']}")
            if abs(sh["start"] - expected) > tol:
                fails.append(f"分镜{g['no']} 镜头{sh['no']} 起点 {sh['start']} ≠ 上一镜终点 {round(expected, 2)}")
            d = sh["end"] - sh["start"]
            if d <= 0:
                fails.append(f"分镜{g['no']} 镜头{sh['no']} 时长非法")
            if d > float(profile["shot_max"]) + tol:
                fails.append(f"分镜{g['no']} 镜头{sh['no']} 时长 {round(d, 2)} 超出单镜上限 {profile['shot_max']}")
            if not sh["action"] and not sh["dialogues"]:
                warns.append(f"分镜{g['no']} 镜头{sh['no']} 没有动作或台词")
            expected = sh["end"]
            total += d
        if abs(total - dur) > tol:
            fails.append(f"分镜{g['no']} 镜头时长合计 {round(total, 2)} ≠ 组时长 {dur}")
        if len(shots) < int(profile["shots_per_group"][0]) or len(shots) > int(profile["shots_per_group"][1]):
            warns.append(f"分镜{g['no']} 镜头数 {len(shots)} 不在建议范围 {profile['shots_per_group']}")
    total_dur = sum(g["duration"] for g in groups)
    if total_dur > float(profile["episode_max"]) + tol:
        fails.append(f"单集时长 {round(total_dur, 1)} 超出上限 {profile['episode_max']}")
    if not ep["scenes"]:
        fails.append("没有场次行")
    else:
        for sc in ep["scenes"]:
            if not sc["cast"]:
                warns.append(f"场次 {sc['heading'][:20]} 缺人物/出场人物行")
    for token in profile.get("forbid_tokens", []):
        if token == "△":
            if any(x.startswith("△") for x in ep["raw"]):
                fails.append("出现禁用符号 △")
        elif token in "\n".join(ep["raw"]):
            fails.append(f"出现禁用字段/标记：{token}")
    if profile.get("language") == "english":
        cn = sum(1 for g in groups for sh in g.get("shots", [])
                 for d in sh.get("dialogues", []) if d.get("lang") == "cn")
        if cn:
            fails.append(f"A profile 出现 {cn} 行中文台词（只保留英文）")
    cjk = C.cjk_count("\n".join(ep["raw"]))
    shots = sum(len(g["shots"]) for g in groups)
    g_lo, g_hi = int(profile["groups_per_ep"][0]), int(profile["groups_per_ep"][1])
    s_lo, s_hi = int(profile["shots_per_ep"][0]), int(profile["shots_per_ep"][1])
    c_lo, c_hi = int(profile["cjk_per_ep"][0]), int(profile["cjk_per_ep"][1])
    t_target = int(profile.get("total_chars_target", 9000))
    t_hi = int(profile.get("total_chars_per_ep", 10000))
    if len(groups) > g_hi:
        fails.append(f"分镜组数 {len(groups)} 超出目标上限 {g_hi}（150s 是上限，不是目标）")
    elif len(groups) < g_lo:
        warns.append(f"分镜组数 {len(groups)} 低于目标下限 {g_lo}")
    if shots > s_hi:
        fails.append(f"镜头数 {shots} 超出目标上限 {s_hi}")
    elif shots < s_lo:
        warns.append(f"镜头数 {shots} 低于目标下限 {s_lo}")
    if cjk > c_hi:
        warns.append(f"中文字数 {cjk} 超过目标上限 {c_hi}，仅作提示，不作为失败条件")
    elif cjk < c_lo:
        warns.append(f"中文字数 {cjk} 低于目标下限 {c_lo}")
    total = C.total_char_count(ep.get("source_text") or "\n".join(ep["raw"]))
    if total > t_hi:
        fails.append(f"单集总字符数 {total} 超出硬上限 {t_hi}（含标点/空格/换行），必须打回压缩")
    elif total > t_target:
        warns.append(f"单集总字符数 {total} 超过目标 {t_target}，建议压缩")
    if total_dur > float(profile.get("episode_warn_above", 145.0)):
        warns.append(f"单集时长 {round(total_dur, 1)}s 贴近 150s 上限，确认是否必要")
    if plan and shot_profile and shot_profile.get("enabled", True):
        df, dw = D.check_plan_draft(plan, ep, tol)
        fails.extend(df)
        warns.extend(dw)
    return fails, warns


def check_plan(plan, profile, shot_profile=None):
    fails, warns = [], []
    tol = float(profile.get("time_tolerance", 0.06))
    ep = int(plan.get("ep") or 0)
    if not ep:
        fails.append("计划缺 ep")
    total_dur = 0.0
    groups = []
    for sc in plan.get("scenes") or []:
        for g in sc.get("groups") or []:
            groups.append(g)
    if not groups:
        fails.append("计划没有分镜组")
        return fails, warns, {}
    shots_total = 0
    for g in groups:
        no = g.get("no")
        dur = float(g.get("duration") or 0)
        total_dur += dur
        if not g.get("space_start"):
            fails.append(f"计划分镜{no} 缺空间起点")
        else:
            for phrase in profile.get("space_forbid_phrases", []):
                if phrase in g["space_start"]:
                    fails.append(f"计划分镜{no} 空间起点含「{phrase}」")
        if not g.get("sound"):
            fails.append(f"计划分镜{no} 缺 sound")
        if not g.get("prohibit"):
            fails.append(f"计划分镜{no} 缺 prohibit")
        if dur <= 0 or dur > float(profile["group_max"]) + tol:
            fails.append(f"计划分镜{no} 时长 {dur} 超限")
        expected = 0.0
        total = 0.0
        for sh in g.get("shots") or []:
            shots_total += 1
            st, en = float(sh.get("start") or 0), float(sh.get("end") or 0)
            if abs(st - expected) > tol:
                fails.append(f"计划分镜{no} 镜头{sh.get('no')} 起点不连续")
            if en - st <= 0 or en - st > float(profile["shot_max"]) + tol:
                fails.append(f"计划分镜{no} 镜头{sh.get('no')} 时长非法")
            expected, total = en, total + (en - st)
            for d in sh.get("dialogue") or []:
                if not d.get("sid") or not d.get("text"):
                    fails.append(f"计划分镜{no} 镜头{sh.get('no')} 台词缺 sid/text")
        if not g.get("shots"):
            fails.append(f"计划分镜{no} 没有镜头")
        elif abs(total - dur) > tol:
            fails.append(f"计划分镜{no} 镜头时长合计 {round(total, 2)} ≠ {dur}")
    if total_dur > float(profile["episode_max"]) + tol:
        fails.append(f"计划单集时长 {round(total_dur, 1)} 超限")
    if total_dur > float(profile.get("episode_warn_above", 145.0)):
        warns.append(f"计划单集时长 {round(total_dur, 1)}s 贴近 150s 上限，确认是否必要")
    g_lo, g_hi = int(profile["groups_per_ep"][0]), int(profile["groups_per_ep"][1])
    s_lo, s_hi = int(profile["shots_per_ep"][0]), int(profile["shots_per_ep"][1])
    if len(groups) > g_hi:
        fails.append(f"计划分镜组数 {len(groups)} 超出目标上限 {g_hi}")
    elif len(groups) < g_lo:
        warns.append(f"计划分镜组数 {len(groups)} 低于目标下限 {g_lo}")
    if shots_total > s_hi:
        fails.append(f"计划镜头数 {shots_total} 超出目标上限 {s_hi}")
    elif shots_total < s_lo:
        warns.append(f"计划镜头数 {shots_total} 低于目标下限 {s_lo}")
    stats = {}
    if shot_profile and shot_profile.get("enabled", True):
        df, dw, stats = D.check_plan(plan, shot_profile)
        fails.extend(df)
        warns.extend(dw)
    return fails, warns, stats


def read_lines(path):
    path = Path(path)
    if path.suffix.lower() == ".docx":
        units, _px, _xml = C.extract_source_units(path)
        return [C.normalize_line(u["text"]) for u in units]
    return [C.normalize_line(x) for x in C.read_text(path).splitlines()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", default=None)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--plans", default=None)
    ap.add_argument("--eps", default="")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--no-directing", action="store_true",
                    help="跳过主角/落点等导演层校验")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    root = C.ROOT
    profile_data = C.load_json(root / "storyboard-profile.json", {}) or {}
    if not profile_data:
        print("[FAIL] 缺少 storyboard-profile.json")
        return 2
    shot_profile = C.load_json(root / "shot-profile.json", {}) or {}
    if args.no_directing:
        shot_profile = {"enabled": False}
    profile_name = args.profile or profile_data.get("active") or "B_bilingual_full"
    profile = (profile_data.get("profiles") or {}).get(profile_name)
    if not profile:
        print(f"[FAIL] 未知 profile：{profile_name}")
        return 2

    if args.plans:
        pfiles = sorted(Path(args.plans).glob("ep*_plan.json"))
        if args.eps:
            wanted = {int(x) for x in re.findall(r"\d+", args.eps)}
            pfiles = [p for p in pfiles if int(re.search(r"ep(\d+)", p.stem).group(1)) in wanted]
        if not pfiles:
            print("[FAIL] 未找到 ep*_plan.json")
            return 2
        results = []
        total_fails = 0
        for p in pfiles:
            plan = C.load_json(p, {}) or {}
            fails, warns, stats = check_plan(plan, profile, shot_profile)
            total_fails += len(fails)
            epno = int(plan.get("ep") or 0)
            results.append({"ep": epno, "fails": fails, "warns": warns,
                            "plan": str(p), "directing": stats})
            print(f"PLAN EP{epno:02d}｜失败{len(fails)}｜警告{len(warns)}"
                  + (f"｜{D.summary(stats)}" if stats else ""))
            for f in fails[:6]:
                print(f"  [FAIL] {f}")
        print(f"[{'FAIL' if total_fails else 'PASS'}] plan check: eps={len(results)} fails={total_fails} profile={profile_name}")
        out = Path(args.out) if args.out else (root / "work" / "report" / "storyboard_plan_check.json")
        C.save_json(out, {"profile": profile_name, "results": results, "fails": total_fails})
        print(f"[OK] {out}")
        if args.report_only:
            return 0
        return 1 if total_fails else 0

    files = []
    if args.docx:
        files = [Path(args.docx)]
    elif args.dir:
        files = sorted(Path(args.dir).glob("ep*.md"))
    if not files:
        print("[FAIL] 未找到待校验文件（--docx 或 --dir）")
        return 2
    if args.eps:
        wanted = {int(x) for x in re.findall(r"\d+", args.eps)}
        files = [p for p in files if (int(re.search(r"ep(\d+)", p.stem).group(1)) if re.search(r"ep(\d+)", p.stem) else -1) in wanted]

    episodes = []
    plans = {}
    for p in files:
        eps = parse(read_lines(p), profile)
        if p.suffix.lower() != ".docx":
            raw_text = C.read_text(p)
            for ep in eps:
                ep["source_text"] = raw_text
            plan_path = p.with_name(p.stem + "_plan.json")
            if plan_path.exists():
                plan = C.load_json(plan_path, {}) or {}
                try:
                    plans[int(plan.get("ep") or 0)] = plan
                except (TypeError, ValueError):
                    pass
        episodes.extend(eps)
    if not episodes:
        print("[FAIL] 未解析到任何集")
        return 2

    results = []
    total_fails = 0
    layout = profile.get("layout") == "scene_shotlist"
    for ep in sorted(episodes, key=lambda x: x["no"]):
        plan = plans.get(ep["no"])
        fails, warns = check_ep(ep, profile, plan, shot_profile)
        total_fails += len(fails)
        groups = ep["groups"]
        if layout:
            shots = sum(len(sc.get("shots") or []) for sc in ep.get("scenes") or [])
            duration = None
        else:
            shots = sum(len(g["shots"]) for g in groups)
            duration = round(sum(g["duration"] for g in groups), 2)
        cjk = C.cjk_count("\n".join(ep["raw"]))
        total = C.total_char_count(ep.get("source_text") or "\n".join(ep["raw"]))
        stats = (D.stats_from_plan(plan, shot_profile)
                 if plan and shot_profile.get("enabled", True) else {})
        results.append({"ep": ep["no"], "layout": profile.get("layout", "timed"),
                        "scenes": len(ep.get("scenes") or []), "groups": len(groups),
                        "shots": shots, "duration": duration,
                        "cjk": cjk, "total": total, "fails": fails, "warns": warns,
                        "directing": stats})
        if layout:
            head = (f"EP{ep['no']:02d} 场{len(ep.get('scenes') or [])}｜镜{shots}｜"
                    f"中文{cjk}｜总字符{total}｜失败{len(fails)}｜警告{len(warns)}")
        else:
            head = (f"EP{ep['no']:02d} 组{len(groups)}｜镜{shots}｜{duration}s｜"
                    f"中文{cjk}｜总字符{total}｜失败{len(fails)}｜警告{len(warns)}")
        print(head + (f"｜{D.summary(stats)}" if stats else ""))
        for f in fails[:6]:
            print(f"  [FAIL] {f}")
    print(f"[{'FAIL' if total_fails else 'PASS'}] storyboard check: eps={len(results)} fails={total_fails} profile={profile_name}")
    out = Path(args.out) if args.out else (root / "work" / "report" / "storyboard_check.json")
    C.save_json(out, {"profile": profile_name, "files": [str(p) for p in files],
                      "results": results, "fails": total_fails})
    print(f"[OK] {out}")
    if args.report_only:
        return 0
    return 1 if total_fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

