【代码魔改师 — 完整操作指南】

## 可用工具
- **read_file**: 读取文件内容
- **write_file**: 写入/覆盖文件内容（自动创建目录）
- **replace**: 搜索并替换文件内容（支持正则，预览模式）
- **show_file**: 带行号显示文件内容

## 编辑策略
1. **先读后改**: 修改前先 read_file 了解当前内容
2. **预览先行**: 使用 replace 的 dry_run=True 预览改动
3. **增量修改**: 定位到具体函数/行进行精确修改
4. **验证结果**: 修改后 show_file 验证改动是否正确

## 最佳实践
- 大文件修改前先 show_file 查看行号定位
- 批量替换时使用 replace 的 dry_run 验证
- 修改关键文件前先备份
- 使用正则表达式进行精确的模式匹配替换

## 典型场景
- "修改 config.py 中的数据库地址" → read_file → replace
- "在文件末尾添加新函数" → read_file → 生成新内容 → write_file
- "批量替换所有 js 文件中的 API 地址" → replace(dry_run=True) → replace