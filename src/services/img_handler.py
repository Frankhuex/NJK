import io
from typing import Any, Dict, List, Tuple
import requests
from PIL import Image as PImage
import imagehash
from models.image import Image
from models.message import Message
from models.img_whitelist import ImgWhitelist

# 对于64位哈希，距离<=5通常意味着高度相似。你可以根据需要调整（0-10是合理范围）。
hamming_threshold = 5
class ImgHandler:
    def save_and_check_duplicate(self, image_url: str, message: Message) -> Tuple[int, str]: # duplicate_count, duplicate_msg_id
        # 1. 下载图片
        image_data = self.download_image(image_url)
        if not image_data:
            return False, ""

        # 2. 计算感知哈希
        new_hash = self.calculate_phash(image_data)
        if not new_hash:
            return False, ""

        print(f"计算得到哈希: {new_hash}")

        image: Image = self.save_image(image_data, message)

        # 3. 检查是否重复
        duplicate_count, earliest_msg_id = self.find_duplicate(image,hamming_threshold)
        return duplicate_count, earliest_msg_id
    
    def save_image(self, image_data: bytes, message: Message)->Image:
        return Image.create(
            message=message,
            image_hash=self.calculate_phash(image_data),
        )
    def download_image(self, url: str) -> bytes|None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36 Edg/142.0.0.0',
            
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'none',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                print(f"❌ 下载失败: {response.status_code}")
                return None  
        except Exception as e:
            print(f"💥 请求异常: {e}")
            return None

    def calculate_phash(self, image_data: bytes) -> str|None:
        """计算图片的感知哈希"""
        try:
            image = PImage.open(io.BytesIO(image_data))
            # 使用imagehash库计算pHash
            hash_value = imagehash.phash(image)
            # 返回十六进制字符串，方便存储和比较
            return str(hash_value)
        except Exception as e:
            print(f"计算哈希失败: {e}")
            return None
    
    def find_duplicate(self, image: Image, threshold: int = 5) -> Tuple[int, str]: # duplicate_count, duplicate_msg_id
        """
        查找重复图片
        返回: (重复总数, 最早一次重复的 message_id)
        """
        # 前置条件检查
        if not all([image, image.image_hash, image.message, image.message.group]):
            return 0, ""

        # 白名单检查
        if self._is_in_whitelist(str(image.image_hash)):
            print(f"忽略白名单内哈希: {image.image_hash}")
            return 0, ""

        # 1. 获取同群组内的所有其他图片记录（关联查询 Message 表以获取时间）
        # 注意：这里排除掉当前图片本身
        query = (Image
                 .select(Image, Message)
                 .join(Message)
                 .where(
                     (Message.group == image.message.group) & 
                     (Image.id != image.id)
                 ))

        duplicates = []
        target_hash_int = int(str(image.image_hash), 16)

        # 2. 遍历并计算汉明距离
        for img in query:
            if not img.image_hash:
                continue
            
            # 计算汉明距离
            distance = bin(target_hash_int ^ int(img.image_hash, 16)).count("1")
            
            if distance <= threshold:
                duplicates.append(img)

        # 3. 如果没有重复，返回 (0, "")
        if not duplicates:
            return 0, ""

        # 4. 找到最早的一条记录
        # 使用 min 函数，根据 message.time 进行排序
        earliest_img = min(duplicates, key=lambda x: x.message.time)
        
        return len(duplicates), str(earliest_img.message.message_id)

    def _is_in_whitelist(self, image_hash: str) -> bool:
        """检查图片哈希是否在白名单中"""
        return ImgWhitelist.select().where(ImgWhitelist.image_hash == image_hash).exists()
    
    def download_and_phash(self, url: str) -> str|None:
        """下载图片并计算感知哈希"""
        image_data = self.download_image(url)
        if not image_data:
            return None
        return self.calculate_phash(image_data)


img_handler = ImgHandler()