# PDF 文本识别器 - 完整打包说明

## 概述
这是一个高精度的 PDF 文本识别工具，支持：
- ✅ **字体识别** - 自动检测并分类不同的字体和字号
- ✅ **复制功能** - 一键复制提取的文本到剪贴板
- ✅ **学术论文优化** - 针对学术论文的特殊优化（公式保护、分栏检测等）
- ✅ **智能排版** - 自动修复断词、段落判定、页眉页脚过滤

## 项目文件结构

```
d:\code\Pdf_to_text\
├── dist_exe/
│   └── PDF文本识别器.exe          ← 独立可执行程序（无需Python环境）
├── Pdf_to_text.py                  ← 核心识别引擎
├── app_gui.py                       ← GUI 应用程序入口
├── build_exe.py                     ← PyInstaller 打包脚本
└── README.md                        ← 本文件
```

## 快速开始

### 方式 1：使用独立 EXE（推荐）
直接运行生成的 `dist_exe/PDF文本识别器.exe` 文件：
- **无需安装 Python**
- **无需安装任何依赖**
- 解压后即可使用

#### 使用步骤：
1. 双击 `PDF文本识别器.exe` 打开应用
2. 点击 "选择文件" 按钮选择 PDF 文件
3. 点击按钮执行所需操作：
   - **提取文本** - 提取纯文本（自动修复排版）
   - **提取并保留字体** - 显示字体和字号信息
   - **字体统计** - 显示 PDF 中使用的所有字体统计
   - **复制到剪贴板** - 将当前文本复制（Ctrl+C 也可以）
   - **保存为文本** - 导出为 .txt 文件

### 方式 2：使用 Python 源代码
如果需要集成到其他程序或自定义功能：

```python
from Pdf_to_text import AcademicPDFRecognizer

# 创建识别器
rec = AcademicPDFRecognizer("paper.pdf")

# 提取纯文本（自动排版修复）
text = rec.extract_text(join_paragraphs=True, fix_hyphenation=True)
print(text)

# 提取带字体信息的文本
spans = rec.extract(store=True)
formatted = rec.format_with_fonts()
print(formatted)

# 获取字体统计
stats = rec.get_font_statistics()
print(f"使用的字体: {stats['fonts']}")
print(f"字号分布: {stats['sizes']}")
```

## 主要功能详解

### 1. 高精度文本提取
- 使用 `pdfplumber` 进行字符级别的精确提取
- 自动检测空格和制表符
- 支持国际字符（中文、日文、符号等）

### 2. 字体识别
- 自动识别每个字符的字体名称
- 检测加粗（Bold）和斜体（Italic）
- 精确记录字号（pt 为单位）
- 生成带格式标记的输出

### 3. 学术论文优化
#### 智能排版修复：
- **分栏检测** - 自动识别单栏/双栏布局
- **断词修复** - 自动拼接行尾连字符
- **段落判定** - 智能判定段落边界
- **页眉页脚过滤** - 自动识别和移除重复的页眉页脚
  - 使用位置 + 字体 + 相似度模糊匹配
  - 支持 Levenshtein 距离算法
- **公式保护** - 特殊处理包含数学符号的行
  - 不拆碎公式
  - 允许更松的行对齐

#### 区域化处理：
- 将页面分为 Top/Middle/Bottom 三个区域
- 在每个区域独立检测分栏
- 实现更精确的多栏识别

### 4. 连字符智能拼接
```python
# 例如：
Input:  "information-\nretrieval"
Output: "information retrieval"  (错误)
        或 "informationretrieval" (需配置词典)

# 使用词典提高准确性：
word_dict = {"information", "retrieval", ...}
rec = AcademicPDFRecognizer(english_word_set=word_dict)
```

## 配置参数

### 核心参数
```python
AcademicPDFRecognizer(
    # 行对齐判定（0-1）
    line_overlap_ratio=0.55,
    
    # 空格判定
    gap_factor=0.28,           # gap >= max(font_size * gap_factor, min_word_gap)
    min_word_gap=1.2,
    
    # 分栏检测
    enable_two_column_detect=True,
    min_gutter_ratio=0.035,    # 空白列宽度占页面宽度的比例
    
    # 页边界忽略
    ignore_header_ratio=0.06,  # 顶部 6% 的区域
    ignore_footer_ratio=0.06,  # 底部 6% 的区域
    
    # 区域化分割（0-1，占页面高度）
    region_splits=(0.28, 0.72),  # 0-0.28: Top, 0.28-0.72: Middle, 0.72-1: Bottom
    
    # 页眉页脚检测
    repeated_header_footer_min_count=3,      # 最少出现次数
    header_zone_ratio=0.12,                  # 页眉区域占页面高度
    footer_zone_ratio=0.12,                  # 页脚区域占页面高度
    header_footer_sim_threshold=0.90,        # 相似度阈值（Levenshtein）
    header_footer_font_size_tol=0.6,         # 字体大小容忍（pt）
    header_footer_y_tol_ratio=0.015,         # 位置容忍（占页面高度）
    
    # 公式保护
    enable_formula_protect=True,
    formula_symbol_ratio=0.24,               # 符号占比 > 24% 认定为公式
    formula_italic_ratio=0.35,               # 斜体占比 > 35% 认定为公式
    formula_line_overlap_relax=0.22,         # 公式模式下额外放宽比例
    
    # 连字符拼接词典
    english_word_set=None,  # 传入 set 对象，全部小写
    hyphen_min_word_len=4,  # 拼接后最小长度
)
```

## 输出示例

### 1. 提取纯文本
```
This paper presents a novel approach to PDF text extraction 
using advanced character-level analysis...
```

### 2. 保留字体信息
```
=== TEXT WITH FONT INFORMATION ===

--- Page 1 ---

[Font: Helvetica | Size: 14.0pt]
Title of the Paper

[Font: Times New Roman | Size: 12.0pt]
This is the main body text...
```

### 3. 字体统计
```
=== Font Statistics ===

Total characters: 15234

Fonts used:
  Times New Roman: 12456 characters
  Helvetica: 1567 characters
  Symbol: 211 characters

Font sizes:
  12.0pt: 12456 characters
  14.0pt: 1500 characters
  10.0pt: 278 characters
```

## 系统要求

### EXE 版本
- Windows 7 或更高版本
- 无需安装任何额外软件
- 硬盘空间：约 50-100 MB

### 源代码版本
- Python 3.7+
- 依赖包：
  - `pdfplumber` - PDF 提取引擎
  - `pyperclip` - 剪贴板操作
  - `pillow` - 图像处理（pdfplumber 依赖）

## 重新打包说明

如果需要修改代码后重新生成 exe：

```bash
# 1. 编辑源文件（如修改 Pdf_to_text.py 或 app_gui.py）

# 2. 重新打包
python build_exe.py

# 3. 新的 exe 会生成在 dist_exe/ 目录
```

## 常见问题

### Q: exe 文件太大，能否压缩？
**A:** 可以用压缩工具（如 7-Zip）压缩，文件本身已优化。大小主要来自 Python 运行时和依赖库。

### Q: 能否在 Mac/Linux 使用？
**A:** 可以，运行 `app_gui.py` 即可（需要 Python 环境）。PyInstaller 也支持跨平台打包。

### Q: 复制功能无效？
**A:** 检查是否有其他程序占用剪贴板。如果持续无效，尝试手动 Ctrl+C 复制文本框内容。

### Q: 提取文本有乱码？
**A:** 通常是 PDF 使用了特殊编码。尝试调整 `ignore_header_ratio` 和 `gap_factor` 参数。

### Q: 双栏识别不准确？
**A:** 调整 `min_gutter_ratio` 参数（默认 0.035）。对于特殊布局，可设置 `enable_two_column_detect=False`。

## 许可证
本项目仅供学习和研究使用。

## 联系方式
如有问题或建议，请检查源代码注释或修改配置参数。
