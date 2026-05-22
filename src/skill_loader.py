# -*- coding: utf-8 -*-
"""
技能文件加载器 — 从 skills/ 目录读取技能定义
每个技能以文件夹形式存放，包含 skill.json、description.md、guide.md

目录结构：
skills/
├── 文件搜索大师/
│   ├── skill.json       # 元数据（ID/名称/标签/工具列表等）
│   ├── description.md   # 简短描述（1句话，用于 prompt）
│   └── guide.md         # 完整操作指南（按需加载，不进 prompt）
└── ...

skills_custom/          # 用户自定义技能（与内置分开存储）
└── ...
"""

import os
import json
from typing import Optional

# 项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")
CUSTOM_SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills_custom")


def _ensure_dir(directory: str):
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)


def _list_skill_directories() -> list:
    """扫描所有技能目录（内置+自定义）"""
    dirs = []
    for base_dir, is_builtin in [(SKILLS_DIR, True), (CUSTOM_SKILLS_DIR, False)]:
        if not os.path.isdir(base_dir):
            continue
        for name in os.listdir(base_dir):
            skill_dir = os.path.join(base_dir, name)
            meta_file = os.path.join(skill_dir, "skill.json")
            if os.path.isdir(skill_dir) and os.path.isfile(meta_file):
                dirs.append((skill_dir, name, is_builtin))
    return dirs


def scan_all_skills() -> dict:
    """
    扫描所有技能目录，返回 {skill_id: metadata_dict}
    从 skill.json 读取元数据
    """
    skills = {}
    for skill_dir, name, is_builtin in _list_skill_directories():
        meta_file = os.path.join(skill_dir, "skill.json")
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            meta["is_builtin"] = is_builtin
            meta["_dir"] = skill_dir
            skill_id = meta.get("id", name)
            skills[skill_id] = meta
        except (json.JSONDecodeError, IOError) as e:
            print(f"[skill_loader] ⚠️ 读取 {name}/skill.json 失败: {e}")
    return skills


def load_skill_metadata(skill_id_or_name: str) -> dict | None:
    """
    按 ID 或名称查找技能的元数据
    1. 优先按 skill_id 匹配
    2. 其次按 name 匹配
    """
    all_skills = scan_all_skills()
    # 精确 ID 匹配
    if skill_id_or_name in all_skills:
        return all_skills[skill_id_or_name]
    # 名称匹配
    for sk_id, meta in all_skills.items():
        if meta.get("name") == skill_id_or_name:
            return meta
    return None


def load_skill_guide(skill_id_or_name: str) -> str | None:
    """
    加载技能的 guide.md（完整操作指南，按需加载）
    """
    meta = load_skill_metadata(skill_id_or_name)
    if not meta:
        return None
    guide_path = os.path.join(meta["_dir"], "guide.md")
    if not os.path.isfile(guide_path):
        return None
    try:
        with open(guide_path, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError:
        return None


def generate_skill_id(name: str) -> str:
    """从技能名生成唯一 ID（英文+数字+下划线）"""
    import re
    base = re.sub(r'[^\w]', '_', name).strip('_').lower()
    if not base:
        base = "skill"
    # 确保唯一
    existing = scan_all_skills()
    if base not in existing:
        return base
    counter = 1
    while f"{base}_{counter}" in existing:
        counter += 1
    return f"{base}_{counter}"


def save_custom_skill(name: str, metadata: dict, description: str = "", guide: str = "") -> str:
    """
    保存自定义技能到 skills_custom/ 目录
    返回 skill_id
    """
    _ensure_dir(CUSTOM_SKILLS_DIR)
    skill_dir = os.path.join(CUSTOM_SKILLS_DIR, name)
    os.makedirs(skill_dir, exist_ok=True)
    
    # 生成 ID
    skill_id = metadata.get("id", generate_skill_id(name))
    metadata["id"] = skill_id
    metadata["name"] = name
    metadata["is_builtin"] = False
    
    # 写 skill.json
    with open(os.path.join(skill_dir, "skill.json"), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 写 description.md
    with open(os.path.join(skill_dir, "description.md"), 'w', encoding='utf-8') as f:
        f.write(description if description else metadata.get("short_description", ""))
    
    # 写 guide.md
    with open(os.path.join(skill_dir, "guide.md"), 'w', encoding='utf-8') as f:
        f.write(guide if guide else metadata.get("detail_content", ""))
    
    return skill_id


def delete_custom_skill(skill_id_or_name: str) -> bool:
    """删除自定义技能文件夹"""
    meta = load_skill_metadata(skill_id_or_name)
    if not meta or meta.get("is_builtin", True):
        return False
    import shutil
    skill_dir = meta["_dir"]
    if os.path.isdir(skill_dir):
        shutil.rmtree(skill_dir)
        return True
    return False


def load_skill_description(skill_id_or_name: str) -> Optional[str]:
    """
    读取技能的 description.md 文件内容。
    先搜 skills_custom/，再搜 skills/。
    """
    # skills_custom 优先
    for base, name in [(CUSTOM_SKILLS_DIR, skill_id_or_name), (SKILLS_DIR, skill_id_or_name)]:
        desc_file = os.path.join(base, name, "description.md")
        if os.path.isfile(desc_file):
            try:
                with open(desc_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return None

