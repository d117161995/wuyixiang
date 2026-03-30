## 2026-03-25 18:30 开发记录

### 本次目标
- 将 Excalidraw 脑图网页（`ai-era.html`）打包成一个高级感的展示页面，包含数据固化、视觉包装、品牌展示

### 主要改动

- **数据固化（烧录初始状态）**
  - 多次将用户在网页上编辑并同步到 `ai-era-data.json` 的 Excalidraw 数据，烧录为代码中的 `convertedElements` 初始数据
  - 引入 `DATA_VERSION` 版本标记机制，版本不匹配时自动清除旧 localStorage 缓存，确保本地（`file://`）和 HTTP 访问都加载最新数据
  - 最终版本：`v20260325-1809`，100 个元素

- **Excalidraw 区域调整**
  - 容器宽度从 `calc(100% - 500px)` 逐步调整至 `calc(100% - 600px)`
  - 使用 `aspect-ratio: 3262/1834` 固定宽高比，匹配内容边界
  - 缩放固定在 144%（`zoom = 1.44`）
  - 通过 `CONTENT_BOUNDS` 精确控制视口定位，左侧裁剪 300 单位空间
  - 实现 `fitToContent()` 函数：初始化、远程加载、文件恢复后自动适配视口

- **Hero 区域（标题 + 方案对比）**
  - 标题"AI时代的变迁"：72px 大字，紫-蓝-粉渐变流光动画（`titleShimmer`）
  - 方案对比横幅：`Word + Maya + Unreal → Cursor + NanoBanana Pro + SeeDance 2.0`
  - 左侧旧方案灰度半透明，右侧新方案高亮
  - 前缀文案"影视制作方案从"

- **页面装饰元素**
  - 四角 L 型装饰线（`.corner-deco`）
  - 底部紫色 / 顶部蓝色径向光晕（`.glow` / `.glow2`）
  - 右上角品牌标识（心动 Logo + 心动美术支撑 · 影视创意组）

- **底部内容**
  - Excalidraw 下方添加 slogan："但不变的是"（白色半透明）+ "一颗创作的心"（渐变炫彩，与标题同款动画）
  - 底部品牌文字"心动美术支撑 · 影视创意组"（无图标）

- **页面滚动**
  - 从 `overflow:hidden` 改为 `overflow-y:auto`，支持上下滚动查看完整内容

- **"已自动保存"提示**
  - 隐藏（`display:none`），不影响展示页面观感

### 影响范围
- **页面**：`ai-era.html` 整体视觉大改版，从纯工具页变为展示级页面
- **交互**：本地（`file://`）可编辑，HTTP 只读展示；缩放和视口锁定
- **数据**：初始数据固化在代码中，编辑后自动保存 localStorage + 手动同步到服务器

### 关键决策（Why）
- **版本标记清缓存**：每次烧录新数据时更新 `DATA_VERSION`，避免旧 localStorage 覆盖新初始数据，无需用户手动清缓存
- **固定缩放 144%**：用户指定的最佳展示比例，内容不大不小
- **`fitToContent` 居中定位**：通过计算 `CONTENT_BOUNDS` 精确设定 scrollX/scrollY，确保内容填满容器
- **aspect-ratio 固定比例**：容器始终与内容区域等比，避免出现多余空白
- **烧录脚本 `bake.js`**：一键完成数据替换 + 版本号 + 边界 + 比例更新，用完即删

### 文件清单
- `FilmCreativityGroup/ai-era.html`：主页面，所有视觉和逻辑改动
- `FilmCreativityGroup/ai-era-data.json`：Excalidraw 数据存储文件（通过 save-server.js 写入）
- `FilmCreativityGroup/save-server.js`：Node.js 保存服务器（端口 9099）
- `FilmCreativityGroup/assets/logo/nano-banana.png`：NanoBanana Pro Logo
- `FilmCreativityGroup/assets/logo/seeDance2.0.png`：SeeDance 2.0 Logo
- `FilmCreativityGroup/assets/logo/maya.png`：Maya Logo
- `FilmCreativityGroup/assets/logo/unreal.png`：Unreal Engine Logo
- `FilmCreativityGroup/assets/logo/word.png`：Word Logo
- `FilmCreativityGroup/assets/logo/cursor.png`：Cursor Logo
- `FilmCreativityGroup/assets/logo/发行商Logo.png`：心动 Logo

### 待办（TODO）
- [ ] 用户修改 Excalidraw 内容后，重新执行烧录流程（创建 bake.js → node bake.js → 删除 bake.js）
- [ ] 考虑是否需要响应式适配不同屏幕分辨率

### 风险与回归点
- 如果用户在本地编辑后忘记点"同步到HTTP"，`ai-era-data.json` 不会更新，烧录的会是旧数据
- `CONTENT_BOUNDS` 是手动/脚本计算的静态值，如果用户大幅移动元素位置，需要重新计算

---

## 2026-03-26 伊瑟资产库 — 侧边栏选择栏显示逻辑笔记

### 显示内容

侧边栏角色列表的每一项 **只显示中文角色名**（`notes_cn`），如"赫尔基德"。如果 `notes_cn` 为空，才 fallback 显示原始 `id`。不显示剧集标签。

### 状态指示

- 绿点（`.dot`）：该角色有任意资产内容（图片/视频/模型/贴图/绑定）
- 灰点（`.dot.empty`）：该角色无任何资产

### 分组逻辑

按 `notes_role` 字段分为两组：
1. **主角组**（`notes_role === "主角"`）
2. **配角组**（其余所有角色）

每组可折叠/展开，带箭头指示。

### 排序逻辑（`advSort`）

1. 先按 `first_appear` 分集（如 `ss01`、`pv06`），**倒序**（新集在前）
2. 同集内按 `create_time` **倒序**（新创建在前）
3. 同集内按角色 ID 前缀聚合（如 `c016_ShadowHunter` 系列的变体放在一起）

### 搜索

支持对 `id`、`name`、`cn_name`、`notes_episode`、`notes_cn`、`notes_en` 进行模糊搜索（关键词小写匹配）。

### 相关文件

- `EstherCharLib/esther-char-lib.js`：`renderSidebar()` 函数（第77-175行）
- `EstherCharLib/esther-char-db.data.js`：角色数据源
- `EstherCharLib/index.html`：侧边栏 HTML 结构和样式
