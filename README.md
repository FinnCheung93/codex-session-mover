<div align="center">

## Codex 会话搬家

把 Codex Desktop / CLI 的会话记录迁移到新的项目目录下。  
适合在项目重命名、目录迁移或历史会话归档时使用。

<sub>Audit · Backup · Move · Verify</sub>

<br>

<p>
  <img src="https://img.shields.io/badge/Codex-Skill-2563eb?style=flat&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Version-v1.0.0-14b8a6?style=flat&logo=github&logoColor=white" />
  <img src="https://img.shields.io/badge/Language-中文-f59e0b?style=flat&logo=markdown&logoColor=white" />
  <img src="https://img.shields.io/badge/Focus-Session%20Migration-7c3aed?style=flat" />
</p>

</div>

```text
Codex 会话搬家用于维护本地 Codex 会话归属关系。
它会先审计候选会话，再备份并更新 session metadata、session_index.jsonl 和相关 workspace 映射。
```

## ✨ 它能帮你做什么

- 找出属于旧项目目录的 Codex 会话
- 把指定会话迁移到新的项目目录
- 更新会话 metadata 中记录的工作目录
- 更新 Codex 本地索引和 workspace 映射
- 在写入前先预览，写入时自动备份

## 🧭 适用场景

- 项目目录改名后，希望历史会话跟着迁移
- 把一个会话从临时目录归到正式项目目录
- 整理 Codex Desktop / CLI 中的项目归属
- 合并或迁移本地项目时，需要保留会话历史
- 想先审计哪些会话会被移动，再决定是否执行

## 🧩 工作方式

这个 Skill 修改的是本地 Codex 状态，不会修改项目源代码。

- 默认先审计，不直接写入
- 移动前创建备份
- 优先使用精确 session JSONL 路径
- 遇到重复 session id 时，不做模糊迁移
- 应用后报告备份位置、移动文件和更新范围

## 🚦 边界

- 不默认批量迁移所有会话
- 不删除旧映射，除非用户明确要求
- 不在候选会话不明确时强行移动
- 不修改项目代码文件
- 不保证 Codex UI 立即刷新，必要时需要切换项目或重启应用

## 📦 使用方式

把本目录作为 Codex skill 安装或放入你的 skills 目录中，由 Codex 在会话迁移、目录搬家或历史归档任务中自动触发。

```text
SKILL.md
```

<sub>未提供开源许可证，默认保留所有权利。</sub>
