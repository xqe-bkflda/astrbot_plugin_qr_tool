import os
import asyncio
import time
import re
import shutil
import aiohttp
from pathlib import Path
from typing import Optional, List

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image, Plain, Reply
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

#二维码生成（qrcode）
try:
    import qrcode
    from PIL import Image as PILImage
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

#高级二维码（MyQR）
try:
    from MyQR import myqr
    HAS_MYQR = True
except ImportError:
    HAS_MYQR = False

#条形码生成（treepoem，需要 Ghostscript）
try:
    import treepoem
    from PIL import Image as PILImage
    HAS_TREEPOEM = True
except ImportError:
    HAS_TREEPOEM = False

#条形码生成（python-barcode）
try:
    import barcode
    from barcode.writer import ImageWriter
    HAS_PYTHON_BARCODE = True
except ImportError:
    HAS_PYTHON_BARCODE = False

#二维码/条码识别
try:
    from pyrxing import read_barcode
    HAS_PYRXING = True
except ImportError:
    HAS_PYRXING = False


@register("astrbot_plugin_qr_tool",
          "xqe-bkflda",
          "二维码/条码生成与识别工具",
          "1.8.0",
          "https://github.com/xqe-bkflda/astrbot_plugin_qr_tool")
class QrToolPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "qr_tool"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.data_dir / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        #构建支持的条码类型列表（优先 treepoem，否则用 python-barcode）
        self.supported_barcode_types: List[str] = []
        self.barcode_backend = None  # 'treepoem' or 'python-barcode'

        if HAS_TREEPOEM:
            try:
                if hasattr(treepoem, 'barcode_types'):
                    self.supported_barcode_types = list(treepoem.barcode_types.keys())
                else:
                    #备用常见类型
                    self.supported_barcode_types = [
                        'code39', 'code128', 'ean13', 'ean8', 'upca', 'upce',
                        'itf14', 'isbn13', 'issn', 'pdf417', 'datamatrix', 'qrcode',
                        'azteccode', 'pharmacode', 'codabar', 'gs1-128', 'gs1-datamatrix'
                    ]
                self.barcode_backend = 'treepoem'
                logger.info(f"条形码使用 treepoem，支持 {len(self.supported_barcode_types)} 种类型")
            except Exception as e:
                logger.error(f"获取 treepoem 条码类型失败: {e}")
                self.supported_barcode_types = []

        if not self.supported_barcode_types and HAS_PYTHON_BARCODE:
            try:
                self.supported_barcode_types = barcode.PROVIDED_BARCODES
                self.barcode_backend = 'python-barcode'
                logger.info(f"条形码使用 python-barcode，支持 {len(self.supported_barcode_types)} 种类型")
            except Exception as e:
                logger.error(f"获取 python-barcode 条码类型失败: {e}")

        if not self.supported_barcode_types:
            logger.warning("未找到可用的条形码生成库")

    #辅助函数
    async def _download_file(self, url: str, suffix: str = ".tmp") -> Optional[Path]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        fname = f"temp_{int(time.time())}_{hash(url)}{suffix}"
                        fpath = self.temp_dir / fname
                        fpath.write_bytes(data)
                        return fpath
                    else:
                        logger.error(f"下载失败 HTTP {resp.status}: {url}")
                        return None
        except Exception as e:
            logger.error(f"下载异常 {url}: {e}")
            return None

    async def _get_image_bytes_from_url(self, url: str) -> Optional[bytes]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    return None
        except Exception:
            return None

    def _get_plain_text(self, event: AstrMessageEvent) -> str:
        msg_obj = event.message_obj
        if hasattr(msg_obj, 'message_str'):
            return msg_obj.message_str or ""
        if hasattr(msg_obj, 'message'):
            texts = [c.text for c in msg_obj.message if isinstance(c, Plain)]
            return " ".join(texts)
        return str(msg_obj)

    def _get_image_from_event(self, event: AstrMessageEvent) -> Optional[str]:
        for comp in event.message_obj.message:
            if isinstance(comp, Image):
                return comp.url or getattr(comp, 'file', None)
        return None

    #二维码生成（普通/彩色）
    def _generate_standard_qr(self, content: str, fill_color: str = "black", back_color: str = "white") -> Optional[Path]:
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(content)
            qr.make(fit=True)
            img = qr.make_image(fill_color=fill_color, back_color=back_color)
            temp_path = self.temp_dir / f"qrcode_{int(time.time())}.png"
            img.save(temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            return None

    def _generate_hsl_rainbow_qr(self, content: str) -> Optional[Path]:
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(content)
            qr.make(fit=True)
            base_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            pixels = base_img.load()
            width, height = base_img.size

            for y in range(height):
                for x in range(width):
                    if pixels[x, y] != (255, 255, 255):
                        hue = (x / width) * 360
                        s = 1.0
                        l = 0.5
                        c = (1 - abs(2*l - 1)) * s
                        h_prime = hue / 60
                        xc = c * (1 - abs(h_prime % 2 - 1))
                        if h_prime < 1: r,g,b = c, xc, 0
                        elif h_prime < 2: r,g,b = xc, c, 0
                        elif h_prime < 3: r,g,b = 0, c, xc
                        elif h_prime < 4: r,g,b = 0, xc, c
                        elif h_prime < 5: r,g,b = xc, 0, c
                        else: r,g,b = c, 0, xc
                        m = l - c/2
                        pixels[x, y] = (int((r+m)*255), int((g+m)*255), int((b+m)*255))

            temp_path = self.temp_dir / f"qr_rainbow_{int(time.time())}.png"
            base_img.save(temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            return None

    #高级二维码
    def _generate_myqr(self, words: str, picture: Optional[str] = None, colorized: bool = False, save_name: str = None) -> Optional[Path]:
        if not HAS_MYQR:
            return None
        if save_name is None:
            ext = ".gif" if picture and picture.lower().endswith('.gif') else ".png"
            save_name = f"myqr_{int(time.time())}{ext}"
        if not save_name.endswith(('.png', '.jpg', '.gif')):
            save_name += '.png'
        save_path = self.temp_dir / save_name
        try:
            myqr.run(
                words=words,
                picture=picture,
                colorized=colorized,
                save_name=save_name,
                save_dir=str(self.temp_dir)
            )
            return save_path if save_path.exists() else None
        except Exception as e:
            logger.error(f"MyQR 生成失败: {e}")
            return None

    #条形码生成（自动选择后端）
    def _generate_barcode(self, code_type: str, code_content: str, scale: int = 2) -> Optional[Path]:
        if not self.supported_barcode_types or self.barcode_backend is None:
            logger.error("没有可用的条形码生成库")
            return None

        if self.barcode_backend == 'treepoem':
            try:
                image = treepoem.generate_barcode(
                    barcode_type=code_type,
                    data=code_content,
                    scale=scale
                )
                if image.mode != '1':
                    image = image.convert('1')
                temp_path = self.temp_dir / f"barcode_{code_type}_{int(time.time())}.png"
                image.save(temp_path)
                return temp_path
            except Exception as e:
                logger.error(f"treepoem 生成条形码失败 {code_type}: {e}")
                return None

        elif self.barcode_backend == 'python-barcode':
            try:
                barcode_class = barcode.get_barcode_class(code_type)
                # 对于 EAN13 等，自动补全校验位
                if code_type == 'ean13' and len(code_content) == 12:
                    code_content = barcode_class.calculate_checksum(code_content)
                writer = ImageWriter()
                writer.set_options({'module_width': 0.2, 'module_height': 5.0, 'quiet_zone': 2.5})
                barcode_instance = barcode_class(code_content, writer=writer)
                temp_path = self.temp_dir / f"barcode_{code_type}_{int(time.time())}.png"
                barcode_instance.save(str(temp_path))
                return temp_path
            except Exception as e:
                logger.error(f"python-barcode 生成条形码失败 {code_type}: {e}")
                return None

        return None

    #二维码生成命令
    @filter.command("qrcode", alias=["qr"])
    async def generate_qrcode(self, event: AstrMessageEvent):
        if not HAS_QRCODE and not HAS_MYQR:
            yield event.plain_result("缺少二维码库，请执行: pip install qrcode[pil] MyQR Pillow")
            return

        raw_text = self._get_plain_text(event).strip()
        for prefix in ["/qrcode", "/qr"]:
            if raw_text.startswith(prefix):
                raw_text = raw_text[len(prefix):].strip()
                break

        if not raw_text:
            yield event.plain_result("用法: /qrcode <内容> [选项]\n选项: -c (彩虹渐变)  -logo <图片>  -animated <GIF>")
            return

        parts = raw_text.split()
        content_parts = []
        colorized = False
        logo_path = None
        animated_path = None

        i = 0
        while i < len(parts):
            p = parts[i]
            if p == "-c":
                colorized = True
            elif p == "-logo" and i + 1 < len(parts):
                logo_path = parts[i+1]
                i += 1
            elif p == "-animated" and i + 1 < len(parts):
                animated_path = parts[i+1]
                i += 1
            else:
                content_parts.append(p)
            i += 1
        content = " ".join(content_parts).strip()

        if not content:
            yield event.plain_result("二维码内容不能为空")
            return
        if len(content) > 1000:
            yield event.plain_result("内容过长（超过1000字符）")
            return

        #处理动态二维码
        if animated_path:
            if animated_path.startswith(("http://", "https://")):
                dl_path = await self._download_file(animated_path, ".gif")
                if not dl_path:
                    yield event.plain_result("下载动图背景失败")
                    return
                animated_path = str(dl_path)
            if not os.path.exists(animated_path):
                yield event.plain_result(f"找不到文件: {animated_path}")
                return
            if not HAS_MYQR:
                yield event.plain_result("生成动态二维码需要安装 MyQR: pip install MyQR")
                return
            qr_path = self._generate_myqr(words=content, picture=animated_path, colorized=colorized)
            if qr_path:
                yield event.chain_result([Image.fromFileSystem(str(qr_path))])
            else:
                yield event.plain_result("动态二维码生成失败")
            return

        #处理带 Logo 二维码
        if logo_path:
            if logo_path.startswith(("http://", "https://")):
                dl_path = await self._download_file(logo_path, ".png")
                if not dl_path:
                    yield event.plain_result("下载Logo图片失败")
                    return
                logo_path = str(dl_path)
            if not os.path.exists(logo_path):
                yield event.plain_result(f"找不到Logo文件: {logo_path}")
                return
            if not HAS_MYQR:
                yield event.plain_result("生成此类型二维码需要安装 MyQR: pip install MyQR")
                return
            qr_path = self._generate_myqr(words=content, picture=logo_path, colorized=colorized)
            if qr_path:
                yield event.chain_result([Image.fromFileSystem(str(qr_path))])
            else:
                yield event.plain_result("带Logo二维码生成失败")
            return

        #普通二维码
        if colorized and HAS_QRCODE:
            qr_path = self._generate_hsl_rainbow_qr(content)
        elif HAS_QRCODE:
            qr_path = self._generate_standard_qr(content)
        elif HAS_MYQR:
            qr_path = self._generate_myqr(words=content, colorized=colorized)
        else:
            yield event.plain_result("没有可用的二维码生成库")
            return

        if qr_path:
            yield event.chain_result([Image.fromFileSystem(str(qr_path))])
        else:
            yield event.plain_result("二维码生成失败")

    #命令：条形码生成
    @filter.command("barcode", alias=["bc"])
    async def generate_barcode_cmd(self, event: AstrMessageEvent, code_type: str = "", content: str = ""):
        """生成条形码。用法：/barcode code128 1234567890"""
        if not self.supported_barcode_types or self.barcode_backend is None:
            yield event.plain_result("未安装条形码生成库，请执行: pip install python-barcode Pillow  或   pip install treepoem (需要 Ghostscript)")
            return

        if not code_type or not content:
            yield event.plain_result("用法: /barcode <类型> <内容>\n示例: /barcode code128 1234567890")
            return

        code_type = code_type.lower()
        if code_type not in self.supported_barcode_types:
            sample = ', '.join(self.supported_barcode_types[:20]) if self.supported_barcode_types else "无法获取列表"
            yield event.plain_result(f"不支持的条码类型: {code_type}\n支持的类型: {sample}\n可使用 /barcode_supported 查看完整列表")
            return

        barcode_path = self._generate_barcode(code_type, content)
        if barcode_path:
            yield event.chain_result([Image.fromFileSystem(str(barcode_path))])
        else:
            yield event.plain_result(f"生成条形码失败。请检查内容是否符合 {code_type} 格式要求")

    #命令：列出支持的条形码类型
    @filter.command("barcode_supported", alias=["barcode_types", "barcode-list"])
    async def list_supported_barcodes(self, event: AstrMessageEvent):
        if not self.supported_barcode_types or self.barcode_backend is None:
            yield event.plain_result("未安装条形码生成库，请执行: pip install python-barcode Pillow 或 pip install treepoem")
            return

        backend_name = "treepoem" if self.barcode_backend == 'treepoem' else "python-barcode"
        types_per_page = 50
        total = len(self.supported_barcode_types)
        pages = (total + types_per_page - 1) // types_per_page

        result = f"条形码后端: {backend_name} (共 {total} 种类型)\n\n"
        if backend_name == "treepoem":
            result += "常用类型示例: code39, code128, ean13, pdf417, datamatrix, qrcode, azteccode\n\n"
        else:
            result += "常用类型: code39, code128, ean13, ean8, upca, upce, isbn13, issn, itf, gs1-128\n\n"
        result += "完整列表:\n"

        for i, t in enumerate(self.supported_barcode_types):
            result += f"- {t}\n"
            if (i + 1) % types_per_page == 0 and (i + 1) != total:
                result += f"\n[第 {i//types_per_page + 1}/{pages} 页，输入 /barcode_supported 继续查看]\n"
                yield event.plain_result(result)
                result = ""
                await asyncio.sleep(0.2)

        if result:
            yield event.plain_result(result)

    #命令：扫描二维码/条码
    @filter.command("scan_qr", alias=["scan"])
    async def scan_qr(self, event: AstrMessageEvent):
        if not HAS_PYRXING:
            yield event.plain_result("缺少 pyrxing 库，请执行: pip install pyrxing")
            return

        image_url = self._get_image_from_event(event)
        if not image_url:
            for comp in event.message_obj.message:
                if isinstance(comp, Reply):
                    try:
                        reply_msg = await event.bot.call_action("get_msg", message_id=int(comp.id))
                        if reply_msg and reply_msg.get("message"):
                            for seg in reply_msg.get("message", []):
                                if seg.get("type") == "image":
                                    image_url = seg.get("data", {}).get("url") or seg.get("data", {}).get("file")
                                    break
                    except Exception as e:
                        logger.error(f"获取引用消息失败: {e}")
                    break

        if not image_url:
            yield event.plain_result("请引用一张包含二维码或条码的图片，或直接发送图片消息并带上 /scan_qr 命令")
            return

        img_bytes = await self._get_image_bytes_from_url(image_url)
        if not img_bytes:
            yield event.plain_result("图片下载失败")
            return

        temp_path = self.temp_dir / f"scan_{int(time.time())}.png"
        with open(temp_path, "wb") as f:
            f.write(img_bytes)

        try:
            result = read_barcode(str(temp_path))
            if result and hasattr(result, 'text') and result.text:
                decoded_text = result.text.strip()
                yield event.plain_result(f"识别结果: {decoded_text}")
            else:
                yield event.plain_result("未在图片中识别到二维码或条码")
        except Exception as e:
            logger.error(f"识别失败: {e}")
            yield event.plain_result(f"识别失败: {e}")
        finally:
            if temp_path.exists():
                os.remove(temp_path)

    async def terminate(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        logger.info("QR Tool 插件已卸载")
