# 阶段3最终定稿交付

主文档：[C题最终方案_阶段3定稿.md](C:/Users/25293/Desktop/数模/C题最终方案_阶段3定稿.md)。最终实现约定优先于旧v1及组员v2提案。

- `stage3_final_config.json`：首轮固定参数、修订模型、分层实验和降级规则，是设计配置，尚无完整求解器实现。
- `time_mapping_final.csv`：144段唯一映射，保留源模板标签，明确生成副本的规范标签和数据位置。
- `source_manifest.json`：本次读取的组员意见、旧设计、复核证据及最终文档指纹。
- `prepare_final_materials.py`：可重复生成配置、映射与源指纹；仅读取原始附件，写入本目录。
- `validate_final_design.py`及`final_design_validation.json`：设计一致性和人工公式检查；不是附件优化/年度策略结果。

从项目目录执行：

```powershell
$env:PYTHONIOENCODING='utf-8'
& 'C:\Users\25293\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C题工作区\阶段3_最终定稿\prepare_final_materials.py'
& 'C:\Users\25293\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C题工作区\阶段3_最终定稿\validate_final_design.py'
```

生成映射需要openpyxl；人工公式验证使用Python标准库。使用现有环境，不安装依赖。原始Excel及组员文件不修改。时间端点和合同解释仍为披露的建模假设，不因配置冻结而变成官方释义。
