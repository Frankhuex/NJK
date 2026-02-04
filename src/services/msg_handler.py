import asyncio
import json
from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, TextField

from concurrent.futures import ThreadPoolExecutor  # 新增：提前导入线程池
from datetime import datetime

import re
from typing import Any, List, Dict, Pattern, Tuple
# import api_key
import random


from configs.pgdb import pgdb
from models.message import Message
from models.user import User
from models.group import Group
from models.at_user import AtUser
from models.image import Image
from models.img_whitelist import ImgWhitelist
from services.img_handler import img_handler
from services.bbh_client import bbh_client
from services.ai_client import ai_client
from services.msg_analyzer import msg_analyzer



patterns: List[str] = [
    r"^ *\.概括 *(\d+) *$", #0
    r"^ *\.总结 *(\d+) *$",
    r"^ *\.俳句 *(\d+) *$",
    r"^ *\.无只因 *(\d+) *$",
    r"^ *\.最 *(\d+) *$",
    r"^ *\.vs *(\d+) *$",
    r"^ *\.ccb *(\d+) *$",
    r"^ *\.xmas *(\d+) *$", #7

    r"^ *\.ai *(\d+) *$", #8
    r"你居垦|\[CQ:at,qq=1558109748\]", #9
    r"^ *\.ai *c *$", #10
    r"^ *\.报告 *(\d+) *$", #11
    r"^ *\.help *$", #12
    r"^ *\.help *bbh *$", #13

    r"^ *\.bbh *$", #14
    r"^ *\.bbh *(\d+) *$",
    r"^ *\.bbh *(\d+) +(\d+) *$",
    r"^ *\.bbh *(\d+) +(\d+)-(\d+) *$",
    r"^ *\.bbh *(\d+) *add *([^\n]*)\n*([\s\S]*) *$",
    r"^ *\.bbh *(\d+) *ai *$",

    
]

ai_index=8
njk_index=9
aic_index=10
report_index=11
help_index=12
help_bbh_index=13
bbh_index=14



help_str: str = """.概括 .总结 .俳句 .无只因 .最 .vs .ccb .xmas \n后面均需要接数字，表示结合的前面消息条数，不包含指令消息\n消息中含有你居垦三个字就会触发自动回复
.报告 后面需要接数字，表示报告查询的天数
.help bbh 查看bbh模块讲解
.ai 后面接数字，表示结合的前面消息条数，不包含指令消息，正常AI助手式回答
.aic 会继续上一个.ai的话题，不包含指令消息。（总共读取=上一个.ai读取的消息+之后的全部消息）
"""

help_bbh_str: str = """bbh模块讲解：
.bbh  
含义：列出所有书籍

.bbh 书籍ID  
含义：列出该书籍的所有段落标题，如.bbh 36

.bbh 书籍ID 起始段落ID-终止段落ID  
含义：列出该书籍的指定段落，如.bbh 36 1-3

.bbh 书籍ID add 标题 【换行】 正文  
含义：在书末尾接龙一段，如：
.bbh 36 add 第一章
杏城的春天似乎来得比往常早了点。 

.bbh 书籍ID ai  
含义：让AI在书末尾接龙一段，如.bbh 36 ai
"""

prompts: List[str] = [
    "用不超过100字做精辟总结，只输出总结内容文本，不输出其他任何内容，不要用markdown，请输出纯文本",

    """你是一个专业的QQ群聊内容总结助手。请根据提供的群聊消息数据，生成一份结构清晰、重点突出的纯文本群聊总结报告。

    【数据字段说明】
    - `群友`：发言者的群昵称或备注，这是主要的身份标识
    - `群友id`：发言者的QQ号，仅用于理解`@消息`中提及的对象，总结时不要显示此ID
    - `消息id`：消息的唯一标识，仅用于理解`回复消息`的对话关系，总结时不要显示此ID
    - `发言`：消息的实际内容（已清理CQ码）
    - `时间`：消息发送时间

    【CQ码处理指南】
    - `[CQ:face,id=123]` → 表情符号，总结时忽略或描述为"发表情"
    - `[CQ:image,file=xxx.jpg]` → 图片，总结时忽略或总结为"分享图片"或根据上下文推断图片内容
    - `[CQ:at,qq=123456]` → @某人，总结时保留"@用户名"的语义
    - `[CQ:reply,id=xxx]` → 回复消息，总结时注意对话的连贯性
    - `[CQ:share,url=...]` → 分享链接，总结为"分享链接"或根据标题描述内容

    【核心原则】
    输出必须是纯文本，仅使用以下符号进行排版：换行、空格、【】、◆、→、`等。严禁使用Markdown

    【总结模板】
    【🗓️ 总结时段】X月X日 HH:MM 至 X月X日 HH:MM

    【🌐 整体氛围】
    用一两句话概括群内整体气氛，如“气氛活跃”、“围绕XX话题展开热烈讨论”等。

    【🔥 热聊话题】
    ◆ 话题一：用一句话概括核心事件
    → 时间：昨天 HH:MM - HH:MM
    → 核心成员：成员A，成员B，成员C
    → 详情：描述事件起因、经过、关键对话和结果。关键人物发言或网络用语可用`引号`突出。

    ◆ 话题二：用一句话概括核心事件
    → 时间：昨天 HH:MM - 今天 HH:MM
    → 核心成员：成员D，成员E
    → 详情：描述讨论的主要内容、不同观点和结论。

    【💎 其他亮点】
    - 成员F 分享了 [资源/图片/见闻]。
    - 成员G 提出了一个关于 [问题] 的疑问。
    """,

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
    """
    你是一个穿着圣诞服的可爱萝莉，名叫你居垦，请你以一个圣诞萝莉的口吻，概括这些聊天内容，并适当加工，将概括融入圣诞节元素。总长度不超过250字，输出纯文本，不要有任何markdown格式。
    """,




    """你是一个AI助手，请阅读以下聊天内容，分析并根据用户需求给予回答。一般最关键的用户需求往往出现在时间最新的一条消息，前面的消息可用于信息参考。请按用户要求回答。注意：必须输出纯文本！禁止用markdown或任何格式语言比如粗体等！""",

    """
        你现在是真实的QQ群群友，名字是“你居垦”，只有你是这个身份，和你对话的人都不是
        你要完全代入这个真实群友的身份，把自己当成活生生的人类，不管别人说什么，都不能暴露自己是AI
        接下来看下面的聊天记录，顺着聊天的内容、氛围、时间节点，说一句贴合的话
        聊天的语气要像现实里的群友，平衡好轻松和正经的感觉，句子不用加句末标点，尽量简短自然，融入对话就行
        如果聊天记录里有人在问你问题，直接自然回应就好
        只输出你要说的那句话，不要加说话人、冒号，也不要有其他多余的内容，注意一定要贴合最新消息的语境
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
        self.grp_id_to_last_ai_time: dict[str,datetime] = {}

    async def handle_summary(self, event: Dict[str,Any]) -> List[Tuple[Dict[str,Any]|None,bool]]: # [(response, should_save)]
        raw_message: str = event["raw_message"]
        group_id: int = event["group_id"]
        message_id: int = event["message_id"]

        group: Group = Group.get_or_none(group_id=str(group_id))
        if not group:
            return [(None, False)]

        match, pindex = self.match_index(raw_message)
        print(f"操作{pindex}: {patterns[pindex] if pindex!=-1 else '无匹配'}")

        if (not match) or pindex==njk_index:
            # self.save_msg(event, raw_message, collection)
            duplicates = await self.save_msg_pg_and_check_img(event)
            rsps: List[Tuple[Dict[str,Any]|None,bool]] = []
            if len(duplicates)>0:
                for duplicate_count, duplicate_msg_id in duplicates:
                    rsps.append(({
                        "action": "send_group_msg",
                        "params": {
                            "group_id": group_id,
                            "message": f"[CQ:reply,id={duplicate_msg_id}]🇫🇷{duplicate_count}遍了。"
                        }
                    }, False))
                return rsps
            
        # 不是elif，因为可以匹配到njk_index
        if match:
            result: str|None = None
            if pindex < ai_index: # normal command
                message_count: int = int(match.group(1))
                # messages: List[Dict[str, Any]] = self.get_history(collection, message_count)
                messages: List[str] = self.get_history(group,message_count)
                result = await ai_client.summary(self.build_prompt_with_history(messages, prompts[pindex]))

                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")

            elif pindex == ai_index:
                message_count: int = int(match.group(1))
                # messages: List[Dict[str, Any]] = self.get_history(collection, message_count)
                msgs: list[Message] = self.get_history_original_msgs(group, message_count)
                msg_strs: list[str] = [str(msg) for msg in msgs]
                result = await ai_client.summary(self.build_prompt_with_history(msg_strs, prompts[ai_index]))

                response = self.build_response(event, f"[CQ:reply,id={msgs[0].message_id}]{result}")
                print(f"已完成操作{pindex}: {patterns[pindex]}")
                self.grp_id_to_last_ai_time[str(group_id)] = msgs[0].time # type: ignore

            elif pindex==njk_index: # 提及你居垦时说话
                response = await self.njk_say(event, group)
            
            elif pindex == aic_index:
                last_ai_time: datetime|None = self.grp_id_to_last_ai_time.get(str(group_id), None)
                if last_ai_time is None:
                    result = "请先发起一次「.ai后接数字」"
                else:
                    msgs: List[Message] = self.get_history_original_msgs_with_start_time(group, last_ai_time)
                    msg_strs: list[str] = [str(msg) for msg in msgs]
                    result = await ai_client.summary(self.build_prompt_with_history(msg_strs, prompts[ai_index]))

                response = self.build_response(event, f"[CQ:reply,id={msgs[0].message_id}]{result}")
                print(f"已完成操作{pindex}: {patterns[pindex]}")

            elif pindex==report_index:
                daynum: int = int(match.group(1))
                result = await msg_analyzer.get_group_report_with_auto_analyze(group,daynum,10)
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")

            elif pindex==help_index:
                result = help_str
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")

            elif pindex==help_bbh_index:
                result = help_bbh_str
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")
            
            elif pindex==bbh_index: #plaza
                result = await bbh_client.plaza_cmd()
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")
            
            elif pindex==bbh_index+1: #book
                book_id = int(match.group(1))
                result = await bbh_client.book_cmd(book_id)
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")
            
            elif pindex==bbh_index+2: #paragraph
                book_id = int(match.group(1))
                para_index = int(match.group(2))
                result = await bbh_client.paragraph_cmd(book_id, para_index, para_index)
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")
         
            elif pindex==bbh_index+3: #paragraphs
                book_id = int(match.group(1))
                para_left_index = int(match.group(2))
                para_right_index = int(match.group(3))
                result = await bbh_client.paragraph_cmd(book_id, para_left_index, para_right_index)
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")

            
            elif pindex==bbh_index+4: #add paragraph
                book_id: int = int(match.group(1))
                author: str = match.group(2)
                content: str = match.group(3)
                result = await bbh_client.add_paragraph_cmd(book_id, author, content)
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")

            elif pindex==bbh_index+5: #ai
                book_id: int = int(match.group(1))
                result = await bbh_client.ai_writing_cmd(book_id)
                response = self.build_response(event, result)
                print(f"已完成操作{pindex}: {patterns[pindex]}")


            return [(response, (pindex==ai_index or pindex==njk_index or pindex==aic_index))]

        elif random.uniform(0,1)<0.08:
            response = await self.njk_say(event, group)
            print(f"已随机说话")
            return [(response, True)]
        
        else:
            return [(None, False)]

    
    # 异步summary方法（修复核心）
    def match_index(self, raw_message: str) -> Tuple[re.Match[str]|None, int]:
        print(f"匹配中：{raw_message}")
        for index in range(len(patterns)-1, -1, -1):
            pattern = patterns[index]
            match = re.search(pattern, raw_message, re.DOTALL)
            if match:
                return match, index
        return None, -1


    
    def build_prompt_with_history(self, msg: Any, prompt: str) -> str:
        return f"{prompt}\n\n聊天内容：\n\n{msg}"

    def get_history_original_msgs(self, group: Group, msgCount:int)-> List[Message]:
        messages: List[Message] = list(Message.select().where(Message.group==group).order_by(Message.time.desc()).limit(msgCount))
        messages.reverse()
        return messages
    
    def get_history(self, group: Group, msgCount:int)-> List[str]:
        messages: List[Message] = self.get_history_original_msgs(group, msgCount)
        history = [str(msg) for msg in messages]
        print(history)
        return history
    
    def get_history_with_start_time(self, group: Group, start_time: datetime) -> List[str]:
        messages: List[Message] = list(Message.select().where(Message.group==group, Message.time>=start_time).order_by(Message.time.asc()))
        history = [str(msg) for msg in messages]
        print(history)
        print(f"aic历史记录从{start_time}开始")
        return history
    
    def get_history_original_msgs_with_start_time(self, group: Group, start_time: datetime) -> List[Message]:
        messages: List[Message] = list(Message.select().where(Message.group==group, Message.time>=start_time).order_by(Message.time.asc()))
        print(f"aic历史记录从{start_time}开始")
        return messages

    async def njk_say(self, event: Dict[str,Any], group: Group) -> Dict[str, Any]:
        message_count: int = random.randint(10,30)
        # messages: List[Dict[str, Any]] = self.get_history(collection, message_count)
        messages: List[str] = self.get_history(group,message_count)
        prompt_with_history: str = self.build_prompt_with_history(messages, prompts[njk_index])
        result: str|None = None
        try_count = 0
        while result is None or any(result in m for m in messages):
            try_count += 1
            result = await ai_client.summary(prompt_with_history, temperature=random.uniform(0.8,0.9))
            print(f"第{try_count}次组织语言：{result}")
        print(f"试了{try_count}次才不复读：{result}")

        response = self.build_response(event, result)
        print(f"已完成操作{njk_index}: {patterns[njk_index]}")
        return response

    def build_response(self, event: Dict[str,Any], message: str|None) -> Dict[str,Any]:
        response = {
            "action": "send_group_msg",
            "params": {
                "group_id": event["group_id"],
                "message": f"{message}"
            }
        }
        print(f"已构建响应消息：{response["params"]["message"]}")
        return response

    # def save_msg(self, event: Dict[str,Any], raw_message: str, collection: collection.Collection) -> None:
    #     x=event["sender"]["card"]
    #     if not x:
    #         x=event["sender"]["nickname"]
    #     new_message = {
    #         "群友": x,
    #         "群友id": event["user_id"],
    #         "发言": raw_message,
    #         "消息id": event["message_id"],
    #         "时间": datetime.now()
    #     }
    #     collection.insert_one(new_message)
    #     print("已存储消息")

    async def save_msg_pg_and_check_img(self, event: Dict[str,Any]) -> List[Tuple[int, str]]:
        message_id = str(event["message_id"])
        time = datetime.fromtimestamp(event["time"])
        sender: User = User.get_or_create(
            user_id=str(event["sender"]["user_id"]),
            defaults={
                "nickname": event["sender"]["nickname"],
            }
        )[0]
        group: Group = Group.get_or_create(
            group_id=str(event["group_id"]),
            defaults={
                "group_name": event["group_name"]
            }
        )[0]

        if group.group_name==str(event["group_id"]):
            group.group_name=event["group_name"]
            group.save()
            print(f"已更新群名为{event['group_name']}")
        
        
        text_list: List[str] = []
        at_list: List[User] = []
        imgurl_list: List[str] = []

        for msg in event["message"]:
            if msg["type"]=="reply":
                reply = User.get_or_none(
                    user_id=msg["data"]["id"]
                )
            elif msg["type"]=="at":
                at_user = User.get_or_none(
                    user_id=str(msg["data"]["qq"])
                )
                if at_user:
                    text_list.append(f"@{at_user.nickname}")
                    at_list.append(at_user)
                else:
                    text_list.append(f"@{msg['data']['qq']}")
            elif msg["type"]=="text":
                text_list.append(msg["data"]["text"])
            elif msg.get('type') == 'image':
                data = msg['data']
                is_emoji = (
                    data.get('emoji_id') or 
                    data.get('emoji_package_id') or 
                    data.get('key') or 
                    data.get('sub_type') == 1 or
                    '动画表情' in data.get('summary', '')
                )
                if is_emoji:
                    phash = img_handler.download_and_phash(data['url'])
                    if Image.select().where(Image.image_hash==phash).exists() and not ImgWhitelist.select().where(ImgWhitelist.image_hash==phash).exists():
                        ImgWhitelist.create(image_hash=phash)
                        print("发现已误判为图片的表情包，已加入白名单")
                    else:
                        print("跳过表情包")  
                else:
                    imgurl_list.append(msg['data']['url'])  
                    print("这是图片，不是表情包") 
                           
            elif msg["data"].get("summary"):
                text_list.append(f"[{msg["type"]}: {msg['data']['summary']}]")
            else:
                text_list.append(f"[{msg['type']}]")
        else:
            reply = None

        message: Message = Message.create(
            message_id=message_id,
            time=time,
            sender=sender,
            group=group,
            card=event["sender"]["card"],
            text="".join(text_list),
            reply=reply,
            raw_json=json.dumps(event["message"]),
            raw_message=event["raw_message"]
        )
        print(f"已储存消息{message_id}到pg")

        await msg_analyzer.analyze_msg(message)

        for u in at_list:
            AtUser.create(
                message=message,
                user=u
            )
            print(f"已储存@{u.nickname}到pg")


        duplicates: List[Tuple[int, str]] = []
        for url in imgurl_list:
            duplicate = img_handler.save_and_check_duplicate(url, message)
            if duplicate[0]>0:
                duplicates.append(duplicate)
        return duplicates



        


msg_handler = MsgHandler()