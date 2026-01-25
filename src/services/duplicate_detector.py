import io
from typing import Any, Dict, List
import requests
from PIL import Image
import imagehash
from pymongo import collection

# 对于64位哈希，距离<=5通常意味着高度相似。你可以根据需要调整（0-10是合理范围）。
hamming_threshold = 5

class DuplicateDetector:
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
            image = Image.open(io.BytesIO(image_data))
            # 使用imagehash库计算pHash
            hash_value = imagehash.phash(image)
            # 返回十六进制字符串，方便存储和比较
            return str(hash_value)
        except Exception as e:
            print(f"计算哈希失败: {e}")
            return None

    def is_duplicate_image(self, collection: collection.Collection, new_hash_str: str) -> bool:
        """检查指定群中是否存在相似图片"""
        # 1. 从数据库获取该群所有已有的哈希值
        existing_records = collection.find(
            {},
            {"image_hash": 1, "_id": 0}
        )

        # 2. 遍历并计算汉明距离
        for record in existing_records:
            existing_hash_str = record["image_hash"]
            # 将十六进制字符串转换为整数以便计算汉明距离
            hamming_dist = self.hamming_distance(new_hash_str, existing_hash_str)
            if hamming_dist <= hamming_threshold:
                return True
        return False

    def hamming_distance(self, hash1_hex: str, hash2_hex: str) -> int:
        """计算两个十六进制哈希字符串之间的汉明距离"""
        n1 = int(hash1_hex, 16)
        n2 = int(hash2_hex, 16)
        return bin(n1 ^ n2).count("1")

    def process_new_image(self, collection: collection.Collection, image_url: str, message_id: int):
        # 1. 下载图片
        image_data = self.download_image(image_url)
        if not image_data:
            return False

        # 2. 计算感知哈希
        new_hash = self.calculate_phash(image_data)
        if not new_hash:
            return False

        print(f"计算得到哈希: {new_hash}")

        # 3. 检查是否重复
        is_duplicate = self.is_duplicate_image(collection,new_hash)
        if is_duplicate:
            return True

        # 4. 如果是新图，存入数据库
        new_document = {
            "image_hash": new_hash,
            "message_id": message_id,
        }
        collection.insert_one(new_document)
        return False

    def handle_detect(self, event: Dict[str, Any], collection: collection.Collection) -> Dict[str,Any]|None:
        raw_message = event["raw_message"]
        group_id = event["group_id"]
        message_id = event["message_id"]

        urls = []
        message_list = event.get('message', [])

        for msg_segment in message_list:
            # 检查是否是图片消息段
            if (isinstance(msg_segment, dict) and 
                msg_segment.get('type') == 'image' and 
                msg_segment.get('data') and 
                msg_segment['data'].get('url')):

                data = msg_segment['data']

                is_emoji = (
                    data.get('emoji_id') or 
                    data.get('emoji_package_id') or 
                    data.get('key') or 
                    data.get('sub_type') == 1 or
                    '[动画表情]' in data.get('summary', '')
                )
                if is_emoji:
                    print("跳过表情包")
                    continue
                urls.append(msg_segment['data']['url'])

        if urls:
            is_duplicate = False
            for image_url in urls:
                if self.process_new_image(collection,image_url,message_id):
                    is_duplicate = True
            if is_duplicate:
                response = {
                    "action": "send_group_msg",
                    "params": {
                        "group_id": group_id,
                        "message": f"[CQ:reply,id={message_id}]" + "🇫🇷了。"
                    }
                }
                return response

        return