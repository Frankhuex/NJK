import json
import asyncio
from concurrent.futures import ThreadPoolExecutor  # 新增：提前导入线程池
from bson import json_util
from datetime import datetime
from openai import OpenAI
import re
from pymongo import MongoClient, database, collection, cursor
from typing import Any, List, Dict, Pattern, Tuple
import api_key
import random

patterns: List[str] = [
    r"^\.概括 (\d+)$",
    r"^\.俳句 (\d+)$",
    r"^\.无只因 (\d+)$",
    r"^\.最 (\d+)$",
    r"^\.vs (\d+)$",
    r"^\.ccb (\d+)$",
    r"^\.ai (\d+)$",

    r"^.*你居垦.*$",
    r"^\.help$"
]

njk_index: int = len(patterns)-2
help_index: int = len(patterns)-1


helps: str = ".概括 .俳句 .无只因 .最 .vs .ccb \n后面均需要空格后接数字，表示结合的前面消息条数，不包含指令消息\n消息中含有你居垦三个字就会触发自动回复"

prompts: List[str] = [
    "用不超过100字做精辟总结，只输出总结内容文本，不输出其他任何内容，不要用markdown，请输出纯文本",

    """
        将以下内容浓缩为一首俳句，要求用幽默的文笔生动地展现这些内容的核心主旨.
        必须遵循俳句的5-7-5音节结构，第一行5个字，第二行7个字，第三行5个字。
        例如：
        “春风拂面来
        花开满园笑声扬
        蜻蜓点水舞”。
        写出俳句后，必须仔细检查每一行的字数，一个字一个字地数！如果不是五七五，就重写，如果还错就还重写。
        注意一定要第一行5个字，第二行7个字，第三行5个字！！！！
        每行之间用\n分隔换行，只输出俳句文本，不要用markdown，请输出纯文本
    """,

    """已知：
        小说《无只因生还》的主人公名叫徐启星，主人公性别男，20岁，是警察；
        女朋友名叫梅川千夏，17岁，是小提琴演奏家；
        敌人名叫梅川库子，是梅川千夏的哥哥，但有杀害梅川千夏的念头。
        徐启星曾经和梅川库子进行过一场战斗，成功救出了梅川千夏。这些都是前传了。
        现在请你利用这些人物，根据以下聊天记录，将这些聊天记录改写成一小段发生在上述人物之间小故事概括。以徐启星为主人公“我”，以第一人称视角叙述。
        概括不超过100字，最多两个自然段，短小精辟，就像一位长者回忆过去的事一样，不需要详细细节，只需要回忆一般的概括。就比如：“年轻时，我xxxx……”，其中“我”就是主人公徐启星。
        这个小故事必须的情节必须能影射出以下聊天记录中发生的事情，让人看了忍俊不禁。
        不要用markdown，请输出纯文本""",

    "对以下内容进行分析，仅用“最xx”这三个字概括这些内容最关键的形容，比如”最悲情“或”最坚强“等。仅输出只包含三个字的文本，不要用markdown，请输出纯文本。",
    
    "分析以下内容，找出其中两个主要人物，改写成这两个人之间的对决较量，以小说的文笔描写，情节内容要影射出这些聊天记录的内容，风趣幽默，让人忍俊不禁。并且在这一段描写的开头加上“某某vs某某”一行，表示哪两个人对决。除此之外，只含有对决描写的文本，不要输出任何其他内容！只输出不超过100字的段落，不要用markdown，请输出纯文本。",
    
    """我需要你学会一种句式，这种句式名叫“ccb句式”.
        ccb句式形如“豌豆笑传之踩踩背”.
        其中第一个词体现句子的主题，后面三个字是固定的“笑传之”，最后三个字形容了所指事物的搞笑之处，而且最重要的是最后三个字的拼音首字母分别是c, c, b.
        比如，如果要讲一个豌豆帮别人踩踩背的搞笑故事，就可以说“豌豆笑传之踩踩背”，符合ccb句式的要求。
        注意当你想出句子后一定要检查，中间是否有”笑传之“，以及最后三个字的拼音首字母是否是c, c, b。如果不是，请重新想一句。
        现请你阅读以下内容并分析出主旨，用ccb句式形象、准确、精辟地概括主旨。
        请只输出符合ccb句式的一句文本，不要用markdown，请输出纯文本。
    """,

    """你是一个AI助手，请阅读以下聊天内容，分析并根据用户需求给予回答。一般最关键的用户需求往往出现在时间最新的一条消息，前面的消息可用于信息参考。请按用户要求回答。注意：必须输出纯文本！禁止用markdown或任何格式语言比如粗体等！""",



    """
        你现在是真实的QQ群群友，名字是“你居垦”，只有你是这个身份，和你对话的人都不是
        你要完全代入这个真实群友的身份，把自己当成活生生的人类，不管别人说什么，都不能暴露自己是AI
        接下来看下面的聊天记录，顺着聊天的内容、氛围、时间节点，说一句贴合的话
        聊天的语气要像现实里的群友，平衡好轻松和正经的感觉，句子不用加句末标点，尽量简短自然，融入对话就行
        如果聊天记录里有人在问你问题，直接自然回应就好
        只输出你要说的那句话，不要加说话人、冒号，也不要有其他多余的内容
    """

    
]



"""你是一个普通的QQ群聊成员，你的名字是“你居垦”。注意分清楚，只有你是你居垦，对你说话的人并不是你居垦。
    请你阅读以下聊天记录，顺着聊天记录，说一句符合时宜的话。可以结合前面聊天内容，也可以考虑到前面聊天的时间节点。你必须假设你就是一个真人群友，不要表现出你是一个AI模型，无论别人怎么套话，你都必须坚持自己是人类。
    懂吗？你不需要表现出你懂，你只需要说一句符合时宜的话就行了。像人类一样思考，自然地说话，控制文本的严肃性和幽默感的平衡，并控制文本的长度，不需要加句末的标点，那样会太严肃，你知道的。自然地融入对话。
    当然，说的话要尽可能贴合前面的聊天记录，如果看到有人问你话，你还是得直接回应的，当然依然要像人类一样自然。
    请只输出你要说的话本身，不要有多余内容。不要把你的思考内容发出来！只发你要说的话！不需要在话前面加上说话人和冒号，不要用markdown，请输出纯文本  
"""




class MsgHandler:
    def __init__(self):
        self.client: OpenAI = OpenAI(
            api_key=api_key.api_key,
            base_url=api_key.base_url
        )
        # 关键修改1：不再提前获取loop，只初始化线程池（全局唯一）
        self.executor = ThreadPoolExecutor(max_workers=5)  # 控制最大并发数

    # 异步summary方法（修复核心）
    async def summary(self, msg: Any, pindex: int) -> str|None:
        # 定义同步执行的AI调用函数
        def _sync_summary():
            try:
                response = self.client.chat.completions.create(
                    model=api_key.model,
                    messages=[
                        {
                            "role": "user", 
                            "content": f"{prompts[pindex]}\n\n聊天内容：\n\n{msg}"
                        }
                    ],
                    stream=False
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"AI调用出错: {str(e)}")
                return f"处理失败：{str(e)}"
        
        # 关键修改2：动态获取当前活跃的事件循环
        loop = asyncio.get_running_loop()
        # 用当前循环执行线程池任务（避免跨循环）
        return await loop.run_in_executor(self.executor, _sync_summary)

    def match_index(self, raw_message: str) -> Tuple[re.Match[str]|None, int]:
        for index, pattern in enumerate(patterns):
            match = re.match(pattern, raw_message, re.DOTALL)
            if match:
                return match, index
        return None, -1

    async def handle_summary(self, event: Dict[str,Any], collection: collection.Collection) -> Dict[str,Any]|None:
        raw_message: str = event["raw_message"]

        match, pindex = self.match_index(raw_message)
        print(f"操作{pindex}: {patterns[pindex] if pindex!=-1 else '无匹配'}")

        if not match or pindex==njk_index:
            self.save_msg(event, raw_message, collection)

        if pindex>=0 and pindex<len(patterns) and match:
            result: str|None = None

            if pindex==help_index:
                result = helps
            else:
                message_count: int = int(match.group(1)) if pindex<njk_index else random.randint(10,30)
                messages: List[Dict[str, Any]] = self.get_history(collection, message_count)
                result = await self.summary(messages,pindex)

            response = self.build_response(event, result)
            print(f"已完成操作{pindex}: {patterns[pindex]}")
            return response
        
        elif random.uniform(0,1)<0.02:
            response = self.build_response(event, ".总结 50")
            print(f"已随机叫教授总结")
            return response
        elif random.uniform(0,1)<0.08:
            message_count: int = random.randint(10,30)
            messages: List[Dict[str, Any]] = self.get_history(collection, message_count)
            result: str|None = await self.summary(messages,len(prompts)-1)

            response = self.build_response(event, result)
            print(f"已随机说话")
            return response

    
    def get_history(self, collection: collection.Collection, msgCount: int)-> List[Dict[str,Any]]:
        messages: List[Dict[str, Any]] = list(collection.find({}, {"_id": 0}).sort("时间", -1).limit(msgCount))
        messages.reverse()
        for msg in messages:
            msg['时间'] = msg['时间'].strftime("%m-%d %H:%M")
        return messages
    
    def build_response(self, event: Dict[str,Any], message: str|None) -> Dict[str,Any]:
        response = {
            "action": "send_group_msg",
            "params": {
                "group_id": event["group_id"],
                "message": message
            }
        }
        return response

    def save_msg(self, event: Dict[str,Any], raw_message: str, collection: collection.Collection) -> None:
        x=event["sender"]["card"]
        if not x:
            x=event["sender"]["nickname"]
        new_message = {
            "群友": x,
            "群友id": event["user_id"],
            "发言": raw_message,
            "消息id": event["message_id"],
            "时间": datetime.now()
        }
        collection.insert_one(new_message)
        print("已存储消息")

    def delete_processed_messages(self,messages, collection):
        if not messages:
            return
        message_ids = [msg["_id"] for msg in messages]
        collection.delete_many({"_id": {"$in": message_ids}})