# 黄金多维度分析实时平台

基于黄金深度研究报告构建的实时分析平台，支持自动更新市场数据，可一键部署到 Github Pages 对外发布。



***

## 一、部署到 Github Pages 步骤

你现在已经在 Github 的创建仓库页面，按照以下步骤完成部署：

### 1. 完成仓库创建

在当前的创建仓库页面：



* **仓库名称**：可以填写 `gold-analysis-platform`（或者你喜欢的名字）

* **描述**：可以填写 `黄金多维度实时分析平台`

* **可见性**：选择 `Public`（公共仓库，这样 Github Pages 可以正常访问）

* 其他选项保持默认即可，然后点击 `Create repository` 创建仓库

### 2. 上传项目文件

仓库创建完成后，你会看到仓库的快速开始页面，按照以下步骤上传我们的文件：



1. 点击页面中的 `uploading an existing file` 链接

2. 把我们准备好的两个文件：`index.html` 和 `README.md` 拖拽到上传区域

3. 拉到页面底部，点击 `Commit changes` 提交文件

### 3. 开启 Github Pages

文件上传完成后，开启 Pages 服务：



1. 进入仓库的 **Settings** 选项卡（在仓库页面的顶部导航栏）

2. 往下滚动找到 **Pages** 选项（在左侧的 Code and automation 区域）

3. 在 **Build and deployment** 部分：

* Source 选择 `Deploy from a branch`

* Branch 选择 `main` 分支，文件夹选择 `/ (root)`

1. 点击 Save 保存

2. 等待 1-2 分钟，Github 就会自动部署你的网站，部署完成后你会得到一个链接：`https://你的用户名.``github.io/``仓库名/`，这个就是你对外发布的网站地址了！



***

## 二、对接实时数据源（AllTick/StockTV/MetalAPI）

默认情况下网站使用模拟数据，你可以按照以下步骤对接真实的实时 API，实现数据自动更新：

### 方式 1：对接 StockTV API（推荐新手，有免费套餐）

StockTV 提供免费的试用套餐，适合个人使用，步骤如下：



1. 访问 [StockTV 官网](https://stocktv.top/) 注册账号

2. 注册后在个人中心获取你的 `API Key`

3. 下载我们的 `index.html` 文件，找到代码中的这部分：



```
async function fetchGoldData() {

&#x20;   const apiKey = 'YOUR\_API\_KEY'; // 把这里替换成你自己的API Key

&#x20;   // ... 其他代码

}
```



1. 把 `YOUR_API_KEY` 替换成你拿到的真实 API Key

2. 把修改后的 `index.html` 重新上传到你的 Github 仓库，覆盖原来的文件即可

StockTV 的 API 已经内置在代码中，替换 Key 后，网站就会每分钟自动拉取最新的黄金价格、美元指数等真实数据了！

### 方式 2：对接 MetalAPI（专业贵金属数据）

如果你需要更专业的贵金属数据，可以选择 MetalAPI：



1. 访问 [MetalAPI 官网](https://metalapi.com/) 注册账号

2. 获取你的 API Key

3. 修改代码中的数据拉取部分，替换为 MetalAPI 的接口：



```
async function fetchGoldData() {

&#x20;   const apiKey = 'YOUR\_METALAPI\_KEY';

&#x20;   const response = await fetch(\`https://api.metalapi.com/v1/latest?base=USD\&symbols=XAU\&access\_key=\${apiKey}\`);

&#x20;   const data = await response.json();

&#x20;   document.getElementById('gold-price').innerText = data.rates.XAU.toFixed(2);

}
```

### 方式 3：对接 AllTick API（机构级数据）

如果需要机构级的高精度数据，可以选择 AllTick：



1. 访问 [AllTick 官网](https://www.alltick.io/) 申请 API 服务

2. 获取你的接口地址和认证信息

3. 按照 AllTick 的文档，修改代码中的 WebSocket 部分，实现毫秒级的实时数据推送



***

## 三、后续维护



* 网站部署完成后，你不需要服务器，Github Pages 会免费托管你的网站

* 数据更新完全由前端自动完成，对接 API 后会自动拉取最新数据

* 如果你需要更新分析框架的内容，只需要修改 index.html 文件，重新上传到仓库即可，Github 会自动重新部署

完成以上步骤后，你就拥有了一个可以随时查看、对外发布的黄金实时分析平台了！

> （注：文档部分内容可能由 AI 生成）