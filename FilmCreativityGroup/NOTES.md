# 影视创意组首页 开发笔记

## 2026-03-10 16:30 开发记录

### 本次目标
- 优化影视创意组首页（`FilmCreativityGroup/index.html`）的布局与交互。
- 整合 AI 动画制作流程至 AI 短剧模块。
- 精细化调整项目橱窗与 AI 模块的视觉表现。

### 主要改动
- **模块整合与重构**：
  - **AI 制作流程并入**：将原有的独立“AI 动画制作流程”横向流程图完整嵌入到“AI 短剧流程”卡片内部，并移除原独立章节。
  - **导航栏清理**：移除了导航栏中的“制作管线”链接。
  - **布局紧凑化**：减少了各模块间的上下间距，使整体视觉更紧凑。

- **AI 短剧流程模块优化**：
  - **视频背景调整**：视频宽度缩减至 30%，高度设为 100% 顶满卡片，定位在右侧 10% 处。
  - **层级修复**：确保卡片内的文字、图标、流程图滑条等所有内容均在视频背景之上（`z-index: 1`）。
  - **动态交互**：保留悬停播放、灰度转彩色、2秒平滑过渡及边缘融入背景的阴影效果。

- **项目橱窗（Bento Grid）重绘**：
  - **图标升级**：所有项目图标（火炬之光、RO、心动小镇、伊瑟、香肠派对、麦芬）均进行了尺寸放大与位置微调，忽略透明边框，以主体视觉撑满。
  - **排版重组**：每张卡片现在包含：项目图标（左上）、“最新案例”列表（左下）、“细分入口”按钮组（底部横排）。
  - **悬停特效**：卡片悬停缩放倍数提升至 1.5 倍，且向网页中央方向放大。
  - **色彩处理**：仅“伊瑟”保留白色反转滤镜，RO 与香肠派对恢复原色。

- **导航与 Hero 区域**：
  - **品牌升级**：导航栏左侧及 Hero 区域上方均替换为最新的“发行商Logo”与“发行商Logo_心动”。
  - **新增功能**：导航栏新增“联系我们”链接，点击平滑滚动至页脚。
  - **更名**：原“能力展示”更名为“支撑品类”。

### 影响范围
- **页面/功能**：`FilmCreativityGroup/index.html` 整体视觉与交互。
- **交互/样式**：AI 模块的视频背景逻辑、项目卡片的缩放逻辑、全局间距控制。

### 关键决策（Why）
- **流程并入**：为了减少页面冗余，将工具属性的“流程图”归属于具体的“AI 短剧”业务模块下，提高信息聚合度。
- **视频缩窄与顶满**：解决因卡片内容增多（加入流程图后）导致 1:1 视频比例过大遮挡文字的问题，同时保持纵向视觉的完整性。
- **1.5倍缩放**：增强沉浸感，使选中的项目在视觉上具有绝对统治力。

### 文件清单
- `FilmCreativityGroup/index.html`：核心页面逻辑与样式修改。
- `w_work.html`：更新工程路径与首页链接。

### 待办（TODO）
- [ ] 检查流程图在不同屏幕宽度下的横向滚动体验。
- [ ] 确认“最新案例”内容的真实性（目前为占位符）。
- [ ] 验证移动端适配情况（当前主要针对 PC 端大屏优化）。

### 风险与回归点
- **层级冲突**：由于大量使用了 `position: absolute` 和 `z-index`，后续新增内容需注意不要被视频遮挡。
- **性能开销**：项目橱窗 1.5 倍缩放结合背景视频播放，在低配机型上可能存在掉帧风险。

---

## 2026-03-18 20:15 开发记录

### 本次目标
- 泡面番第三集上线、文件整理迁移、作品集数据更新与变更追踪功能。

### 主要改动
- **泡面番第三集上线**：
  - 在策划页 EP.03 关联视频 `XDTown_SER01_ep03_001_a.mp4`，状态从"制作中"改为可播放。
  - EP.04 设为新的"制作中"占位。

- **文件目录整理**：
  - 将根目录 `story/` 下所有文件（分镜、食篇文案、场景库、RO 四个方案、流程图等）全部迁移至 `FilmCreativityGroup/story/`。
  - `w_work.html` 中所有链接和工程路径从 `story/` 更新为 `FilmCreativityGroup/story/`（泡面番策划、分镜、食篇、场景库、流程图、RO 方案一~四，共 14 处链接）。
  - 修复泡面番策划页中视频和资产库的相对路径（`../` → `../../`，共 4 处）。
  - 删除根目录 `story/` 和 `dist/story/` 旧文件。

- **作品集数据更新与变更追踪**：
  - `tools/fetch-portfolio.mjs`：
    - 新增 `updateLogs` 字段，每次运行自动对比上次数据，记录具体的新增项目、移除项目、新增/更新封面、字段变更。
    - 新增 `_coverTokens` 字段，存储每张封面的飞书 `file_token`，解决"飞书上换了封面但本地不更新"的问题。
    - `downloadFile()` 新增 `force` 参数，token 变化时强制覆盖下载。
    - 保留最近 20 条更新历史。
  - `portfolio/index.html`：页面顶部新增"上次更新内容"模块。
  - `portfolio/portfolio.js`：新增 `renderUpdateLog()` 渲染更新日志，展示统计概览 + 具体变更明细。
  - `portfolio/portfolio.css`：更新日志模块样式（分类色彩标记：绿色新增、粉色移除、橙色封面、青色变更）。

- **AI 短剧流程模块**：
  - AI 动画制作流程并入 AI 短剧流程卡片，移除独立 section 和导航栏"制作管线"链接。
  - 视频背景宽度 30%、高度 100%，内容元素 z-index 提升至视频之上。

### 影响范围
- **页面/功能**：`FilmCreativityGroup/story/noodle-anime-plan.html`、`FilmCreativityGroup/index.html`、`w_work.html`、`portfolio/index.html`。
- **数据/脚本**：`tools/fetch-portfolio.mjs`、`portfolio/portfolio-db.json`。

### 关键决策（Why）
- **文件整理到 FilmCreativityGroup**：统一管理，避免根目录 `story/` 与 `FilmCreativityGroup/story/` 并存的混乱。
- **封面 token 对比**：之前只判断"本地文件是否存在"导致飞书上换了封面检测不到，改为对比 `file_token` 彻底解决。
- **具体变更记录**：统计数字（如"127条"）无法体现实际内容变化，改为 diff 对比记录每条具体的新增/修改/删除。

### 文件清单
- `FilmCreativityGroup/story/noodle-anime-plan.html`：EP.03 上线 + 路径修复。
- `FilmCreativityGroup/index.html`：AI 流程合并 + 视频背景调整。
- `w_work.html`：14 处路径更新。
- `tools/fetch-portfolio.mjs`：变更追踪 + 封面 token 对比。
- `portfolio/index.html`：新增更新日志 HTML 容器。
- `portfolio/portfolio.js`：新增 `renderUpdateLog()` 函数。
- `portfolio/portfolio.css`：更新日志样式。

### 待办（TODO）
- [ ] **每次更新作品集数据后检查**：运行 `node tools/fetch-portfolio.mjs --skip-video` 后，打开作品集页面核对"上次更新内容"模块，确认变更明细正确。
- [ ] **泡面番封面验证**：在飞书上确认泡面番封面是否已修改，再次运行抓取脚本验证能否正确检测到封面变化并重新下载。
- [ ] 确认第三集视频在策划页中可正常播放。

### 风险与回归点
- **相对路径**：文件迁移后所有相对路径（`../` vs `../../`）需要仔细核对，遗漏会导致资源 404。
- **旧文件残留**：如果有其他页面引用了根目录 `story/` 下的文件，迁移后会断链。

---

## 2026-03-18 20:40 开发记录

### 本次目标
- 修复作品集封面更新检测、解决缓存问题、优化更新日志模块。

### 主要改动
- **封面更新检测增强**：
  - 原有 token 对比机制无法覆盖"飞书替换附件但 token 不变"的情况。
  - 新增**文件大小对比**：比较飞书返回的 `size` 和本地文件 `statSync().size`，不一致则强制重下载。
  - 三级检测：文件不存在 → 新下载；token 变了 → 重下载；大小变了 → 重下载。

- **更新日志模块优化**：
  - 去掉统计概览行（总记录/项目数/视频匹配），只保留标题 + 时间 + 具体变更明细。
  - 新增**复制按钮**：点击后格式化为纯文本（`影视作品集更新（时间）\n变更类型：项目1、项目2`），方便发送给同事。

- **缓存问题彻底解决**：
  - 发现 HTTP 服务器是 nginx，不发 `Cache-Control` 头，HTML meta 标签无效。
  - JS/CSS 改用 `Date.now()` 动态时间戳加载，每次打开页面生成不同 URL 绕过缓存。
  - 删除了手动版本号机制和脚本自动更新版本号逻辑。

### 影响范围
- **页面/功能**：`portfolio/index.html` 更新日志模块展示 + 缓存策略。
- **数据/脚本**：`tools/fetch-portfolio.mjs` 封面检测逻辑。

### 关键决策（Why）
- **三级封面检测**：飞书的附件替换行为不可预测（token 可能变也可能不变），同时比 token 和 size 是最稳妥的方案。
- **动态时间戳替代版本号**：nginx 服务器我们无法配置，用客户端 `Date.now()` 是不依赖服务端的唯一可靠方案。
- **去掉统计概览**：用户反馈只需要具体变更内容，统计数字没有实际价值。

### 文件清单
- `tools/fetch-portfolio.mjs`：新增 `statSync` 大小对比 + 移除版本号自动更新。
- `portfolio/index.html`：JS/CSS 改为动态加载 + 添加 no-cache meta。
- `portfolio/portfolio.js`：更新日志去掉统计行 + 新增复制按钮。
- `portfolio/portfolio.css`：复制按钮样式（`.update-log-copy`）。
- `.cursor/rules/portfolio-update-workflow.mdc`：作品集更新流程规则文件。

### 待办（TODO）
- [ ] 确认同事 `Ctrl+Shift+R` 后能看到最新页面。
- [ ] 考虑将 `.m4v` 加入本地视频扫描格式列表（目前 `香肠-电竞派对新皮肤.m4v` 未匹配）。

### 风险与回归点
- **`Date.now()` 加载**：每次打开页面都会请求新文件，不走缓存，会增加 nginx 负载。对于当前访问量级无影响。
- **首次强刷**：同事需要做一次 `Ctrl+Shift+R` 拿到最新 HTML，之后就不再需要了。

---

## 2026-03-20 影视创意组首页 · 架构与修改指南

> **目的**：给同事在 Cursor 中修改本项目时提供全局上下文，减少翻代码的时间。

---

### 一、项目概况

- **定位**：影视创意组的部门门户网站，对内展示项目橱窗、AI 制作管线、排期动态、近期作品视频
- **技术栈**：纯静态 HTML / CSS / JS，**单文件 `index.html`（~3160行）**，无框架、无构建工具
- **图标库**：[Phosphor Icons](https://phosphoricons.com/)（通过 unpkg CDN 引入），class 名格式 `ph ph-xxx` / `ph-fill ph-xxx` / `ph-duotone ph-xxx`
- **部署方式**：nginx 静态文件服务，访问地址 `http://172.26.166.131:8080/FilmCreativityGroup/index.html`
- **工程路径**：`Y:\tmp\WuYiXiang\wuyixiang\FilmCreativityGroup\`

---

### 二、文件结构

```
FilmCreativityGroup/
├── index.html              ← 主页面（所有 HTML/CSS/JS 都在这一个文件里）
├── NOTES.md                ← 本文件，开发笔记
├── assets/
│   ├── logo/               ← 各游戏的 Logo 和 App 图标 PNG
│   │   ├── 发行商Logo.png         （导航栏左上角）
│   │   ├── 发行商Logo_心动.png     （Hero 区域）
│   │   ├── 火炬之光_app图标.png    （导航下拉菜单）
│   │   ├── 火炬之光logo_trimmed.png（项目橱窗卡片）
│   │   ├── 小镇_app图标.png / 小镇logo（透明底）.png
│   │   ├── 伊瑟_app图标.png / 伊瑟logo（透明底）.png
│   │   ├── 香肠派对_app图标.png / 香肠派对logo（透明底）.png
│   │   ├── 麦芬_app图标.png / 麦芬logo_trimmed.png
│   │   └── RO_app图标.png / RO_Logo2_CN.png
│   ├── ui/                 ← UI 素材（目前只有 1 个 NPC 头像）
│   ├── video/              ← 项目 Logo 动画视频 + 封面图
│   │   ├── 混剪.mp4               （Hero 背景视频）
│   │   ├── ai-drama-preview.mp4   （AI短剧模块背景视频）
│   │   ├── 火炬之光logo.mp4 / 心动小镇logo.mp4 / ...（各项目卡片悬停视频）
│   │   └── *.jpg / *.png          （视频封面/缩略图）
│   └── 寻鲸季素材/          ← 寻鲸季 CG 参考素材
└── story/                  ← 策划/分镜/文案子页面（不属于首页，但首页有链接指向这里）
    ├── noodle-anime-plan.html       （泡面番策划）
    ├── food-ep01~10-*.html          （食篇分镜 10 集）
    ├── scene-library/index.html     （场景库）
    ├── sea-cg/index.html            （寻鲸季 CG）
    └── episode-workflow-*.html      （制作流程图）
```

---

### 三、页面模块地图（从上到下）

| # | 模块 | 行号范围 | id / class | 说明 |
|---|------|----------|-----------|------|
| 0 | **顶部导航栏** | ~2422-2466 | `#topNav`, `.top-nav` | 固定导航，滚过 Hero 后显示；含品牌 Logo + 导航链接 + 进度条 |
| 1 | **Hero Section** | ~2472-2489 | `.hero` | 全屏背景视频（`混剪.mp4`）+ 标题 + 简介 + Scroll 提示 |
| 2 | **项目橱窗** | ~2491-2648 | `#sec-projects`, `.bento-section` | 6 张项目卡片（火炬/小镇/伊瑟/香肠/麦芬/RO），每张有 Logo + 最新案例 + 入口按钮，悬停播放视频 |
| 3 | **AI 短剧流程** | ~2651-2750 | `#sec-capability`, `.capability-section` | 单张大卡片，含 AI 流程标签 + 描述 + 8 步横向流程图（可滚动），背景视频悬停播放 |
| 4 | **排期与资源** | ~2752-2837 | `#sec-schedule`, `.info-section` | 左右两栏：左栏排期链接，右栏最新动态时间线 |
| 5 | **近期作品展示** | ~2839-2907 | `#sec-gallery`, `.gallery-section` | 横向滚动视频画廊（5 个视频卡片），悬停预览 + 点击弹窗播放 |
| 6 | **Footer** | ~2910-2919 | `#site-footer`, `.site-footer` | Slogan + 联系方式 + 版权 |
| - | **浮动按钮** | ~2923-2931 | `#backTopBtn`, `#muteBtn` | 回到顶部 + 静音/取消静音 |
| - | **视频弹窗** | ~2933-2940 | `#videoModal` | 全屏视频播放器 |
| - | **JS 逻辑** | ~2943-3159 | `<script>` | IntersectionObserver 动效 / 导航高亮 / 视频控制 / 鼠标跟随高亮 |

---

### 四、样式体系

- **全局配色**（CSS 变量，`:root` 第 10~21 行）：
  - `--bg-dark: #000` 纯黑背景
  - `--bg-card / --bg-card-hover` 半透明卡片背景
  - `--accent-1: #00e5ff` 青色（导航高亮/流程图）
  - `--accent-2: #ff00ea` 品红色（AI 模块/NEW 徽章）
  - `--accent-3: #ffb800` 金色（备用强调）
- **背景氛围光**（`.ambient-light`，第 44~75 行）：两个 `600px/500px` 的彩色模糊圆，`fixed` 定位，`float` 动画缓慢漂浮
- **卡片系统**（`.bento-card`，第 239~500 行）：圆角 + 半透明背景 + 悬停 1.5× 缩放 + 鼠标跟随 `radial-gradient` 高亮边框
- **动效**（`.fade-in`，第 2389~2397 行）：`IntersectionObserver` 触发 `translateY(40px) → 0` 入场动画
- **响应式断点**：`1024px`（2列）→ `768px`（1列 + 导航精简）

---

### 五、常见修改场景

#### 5.1 修改/新增项目卡片
在 `#sec-projects` 的 `.project-grid` 内复制一个 `<div class="bento-card project-card-uniform ...">` 块，替换：
- `<video src="assets/video/xxx.mp4">` — 卡片背景视频
- `<img src="assets/logo/xxx.png">` — 项目 Logo（注意调 `style` 里的 height/margin 让 Logo 主体撑满）
- `.proj-case-item` — 最新案例文字
- `.proj-entry` — 底部入口按钮

#### 5.2 更新"最新动态"时间线
在 `#sec-schedule` 右栏的 `.info-rows` 内修改 `.news-item`：
- `dot-done` / `dot-pending` — 完成/待办状态
- `st-updated` / `st-pending` — 状态标签
- 日期、标题、描述直接改文字

#### 5.3 更新"近期作品展示"视频
在 `#sec-gallery` 的 `.gallery-grid` 内修改/新增 `.video-card`：
- `onclick="openVideoModal('视频URL')"` — 弹窗播放地址
- `<video src="..." poster="...">` — 缩略图视频和封面
- `.video-title` / `.video-meta` — 标题和标签

#### 5.4 修改 AI 流程图步骤
在 `#sec-capability` 的 `.pipeline` 内，每一步是 `.pipe-col > .pipe-step > .pipe-box`：
- `<span class="pipe-num">N</span>` — 步骤编号
- `<i class="ph ph-xxx"></i>` — 步骤图标
- 文字直接改

Gate（审批节点）是 `.pipe-gate > .pipe-diamond`，箭头是 `.pipe-arrow`。

#### 5.5 修改导航栏
导航链接在 `.nav-links` 内：
- 普通链接：`<a href="#sec-xxx" class="nav-link" data-nav>`
- 下拉菜单：`.nav-dropdown-wrap` 包裹
- JS 会自动根据滚动位置高亮对应链接（参见 `updateNav()` 函数）
- 如果新增了 section，需要在 JS 的 `sections` 选择器中加上对应 `#id`（第 2970 行）

#### 5.6 新增 assets
- Logo 放 `assets/logo/`，命名规范：`{游戏名}logo（透明底）.png`（卡片用）+ `{游戏名}_app图标.png`（导航下拉用）
- 视频放 `assets/video/`，命名规范：`{游戏名}logo.mp4`（卡片背景视频）
- 近期作品的视频源在 `http://172.26.166.131:5174/local-videos/` 下，按游戏名文件夹组织

---

### 六、注意事项

- **单文件架构**：整个页面（HTML + CSS + JS）都在 `index.html` 一个文件里，共 ~3160 行。修改前建议用 Cursor 的 `Ctrl+Shift+O` 按 id/class 跳转定位
- **z-index 层级**：背景光晕(0) < 主内容(1) < 导航栏(1000) < 视频弹窗(9999)，新增浮动元素注意层级
- **视频性能**：页面同时存在 Hero 背景视频 + 6 个项目卡片视频 + AI 模块视频 + 5 个作品展示视频，全部设了 `preload="metadata"` 减少初始加载，悬停才 `play()`
- **伊瑟 Logo 特殊处理**：`class="invert-logo"`，悬停时取消白色反转（第 318 行 CSS），其他 Logo 不需要
- **项目橱窗卡片缩放方向**：通过 CSS `transform-origin` 控制向中央放大（第 279~313 行），左上/右上/左下/右下各不同
- **缓存问题**：nginx 无 Cache-Control 头，如果改了 JS/CSS 文件同事看不到更新，需要 `Ctrl+Shift+R` 强刷一次

---

### 七、相关页面与工具

| 页面 | 路径 | 说明 |
|------|------|------|
| 工作展示中心 | `Y:\tmp\WuYiXiang\wuyixiang\w_work.html` | 所有项目网页的索引页 |
| 影视作品集 | `Y:\tmp\WuYiXiang\wuyixiang\portfolio\index.html` | 作品集展示，数据来自飞书 |
| 泡面番策划 | `FilmCreativityGroup/story/noodle-anime-plan.html` | AI短剧模块的"查看项目案例"链接指向这里 |
| 数据更新脚本 | `Y:\tmp\WuYiXiang\wuyixiang\tools\fetch-portfolio.mjs` | 从飞书拉取作品集数据 |
| nginx 配置 | 本地 nginx，根目录 `Y:\tmp\WuYiXiang\wuyixiang\dist\` | 同事访问走这里 |

---

### 八、快速上手

```bash
# 1. 本地预览（直接浏览器打开）
start FilmCreativityGroup/index.html

# 2. 通过 nginx 预览（需要先复制到 dist）
Copy-Item FilmCreativityGroup -Destination dist/FilmCreativityGroup -Recurse -Force

# 3. 同事访问
http://172.26.166.131:8080/FilmCreativityGroup/index.html
```
