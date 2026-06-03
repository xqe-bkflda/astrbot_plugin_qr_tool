# 二维码/条码工具箱 for AstrBot

一个支持二维码/条码生成与识别的 AstrBot 插件，额外支持带Logo二维码、动态二维码和多种条形码。

## 指令

- /qrcode <内容>               生成标准黑白二维码
- /qrcode <内容> -c             生成彩虹渐变彩色二维码
- /qrcode <内容> -logo <图片>    生成带Logo二维码（支持本地路径或URL）
- /qrcode <内容> -animated <GIF> 生成动态二维码（背景为GIF）
- /barcode <类型> <内容>        生成条形码（支持约100种类型）
- /barcode_supported           列出所有支持的条形码类型
- /scan_qr                      识别图片中的二维码或条码（引用图片或直接发送）

## 安装

方法一:
1. 将压缩包解压并放入 AstrBot 的 plugins 目录
2. 安装 Python 依赖：pip install -r requirements.txt
3. （可选）如需使用 treepoem 后端（支持超多种条码），请安装 Ghostscript：
   - Linux: sudo apt-get install ghostscript
   - Windows: 下载安装 Ghostscript 并添加到 PATH
   - pip install treepoem>=3.23.0
4. 重启 AstrBot

方法二: 
1. 在astrbot插件市场搜索: astrbot_plugin_qr_tool并下载
2.  （可选）如需使用 treepoem 后端（支持超多种条码），请安装 Ghostscript：
   - Linux: sudo apt-get install ghostscript
   - Windows: 下载安装 Ghostscript 并添加到 PATH
   - pip install treepoem>=3.23.0

## 依赖库列表与用处

- qrcode[pil] - 标准二维码生成
- Pillow - 图像处理
- aiohttp - 异步网络请求
- pyrxing - 二维码/条码识别（无系统依赖）
- MyQR - 带Logo和动态二维码生成
- treepoem(可选) - 条形码生成（约100种格式，需要 Ghostscript）
- python-barcode - 条形码生成（纯 Python，支持常见条码）

## 条形码后端自动切换

插件会优先尝试使用 treepoem（功能更强），如果未安装或不可用，则自动降级使用 python-barcode。你只需安装其中一个

## 使用示例

生成标准二维码：
/qrcode https://astrbot.app

生成彩虹渐变二维码：
/qrcode https://astrbot.app -c

生成带Logo二维码：
/qrcode https://astrbot.app -logo https://example.com/logo.png

生成动态二维码：
/qrcode https://astrbot.app -animated https://example.com/bg.gif

生成条形码（Code 128）：
/barcode code128 1234567890

生成条形码（EAN-13）：
/barcode ean13 690123456789

生成 PDF417 二维条码：
/barcode pdf417 HelloWorld

查看所有支持的条码类型：
/barcode_supported

识别二维码/条码：
- 发送一张带码的图片，并附上 /scan_qr 命令
- 或引用他人发送的图片消息，发送 /scan_qr

## 支持的部分条形码类型（treepoem）

| 类型 | 说明 |
|------|------|
| code39 | Code 39 - 字母数字条码 |
| code128 | Code 128 - 高密度条码 |
| ean13 | EAN-13 - 国际商品条码 |
| ean8 | EAN-8 - 国际商品条码（短码） |
| upca | UPC-A - 美国商品条码 |
| upce | UPC-E - 美国商品条码（短码） |
| itf14 | ITF-14 - 物流包装条码 |
| pdf417 | PDF417 - 二维堆叠式条码 |
| datamatrix | Data Matrix - 二维矩阵条码 |
| qrcode | QR Code - 二维码 |
| azteccode | Aztec Code - 二维条码 |
| pharmacode | PharmaCode - 制药行业条码 |
| codabar | Codabar - 图书馆/快递条码 |
| gs1-128 | GS1-128 - 供应链条码 |

完整列表请使用 /barcode_supported 命令查看。

## 注意事项

- 动态二维码背景GIF建议尺寸适中，过大可能导致生成缓慢
- 带Logo二维码对二维码识别有一定影响，建议Logo图片不遮盖过多区域
- EAN-13 条形码内容必须是 12 或 13 位数字
- 如果无法安装 Ghostscript，只需安装 python-barcode 即可使用常见条码（code39, code128, ean13, ean8, upca 等）

## 更新日志

v1.8.0
- 增加对 python-barcode 后备支持，自动在 treepoem 不可用时降级
- 优化条形码生成的参数解析和错误提示

v1.7.0
- 修复了一些已知问题

v1.6.0
- 更换条形码生成库为 treepoem，支持约100种条码格式
- 新增 /barcode_supported 命令

v1.5.0
- 新增 -logo 参数支持生成图片二维码
- 新增 -animated 参数支持生成动态二维码

v1.4.0
- 修复二维码内容包含指令名
- 优化 -c 参数的表现

v1.3.0
- 修复了一些已知问题

v1.2.0
- 修复Linux依赖问题

v1.1.0
- 修复了一些已知问题

v1.0.0
- 原始版本