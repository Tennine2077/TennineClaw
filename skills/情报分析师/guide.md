【情报分析师 — 完整操作指南】

## 可用工具
- **get_system_info**: 获取操作系统、CPU、内存等系统信息
- **get_current_time**: 获取当前日期和时间
- **count_lines**: 统计项目代码行数

## 分析策略
1. **环境感知**: 先获取系统基本信息
2. **时间感知**: 了解当前时间，判断时效性
3. **项目规模**: 使用 count_lines 了解项目规模

## 最佳实践
- 用户提问前自动收集环境信息
- 结合时间和系统状态提供上下文
- 在代码审查时使用 count_lines 评估改动量

## 典型场景
- "这个项目有多大？" → count_lines + list_files
- "现在几点了？" → get_current_time
- "系统环境怎么样？" → get_system_info