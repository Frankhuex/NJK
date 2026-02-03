from typing import Any, Dict, List, Tuple
from configs.pgdb import pgdb
from models.message import Message
from models.user import User
from models.group import Group
from models.topic import Topic
from models.word import Word
from models.msg_topic import MsgTopic
from models.msg_word import MsgWord
from models.at_user import AtUser
from datetime import datetime
from services.ai_client import ai_client
import re
import jieba
from peewee import fn
from peewee import fn, SQL, JOIN
from datetime import date, datetime, timedelta, time as dt_time
import asyncio

reserved_words = ['你居垦','【新】']
banned_words = ['@','[face]']
banned_regex = [r'@\S+\s',r'\[[^\]]*\]']

class MsgAnalyzer:
    def __init__(self):
        for w in reserved_words:
            jieba.add_word(w)
    
    async def analyze_given_msgs(self, messages: List[Message], concurrency: int = 10) -> int:
        """
        针对提供的消息列表进行并发分析
        :param messages: 需要分析的 Message 对象列表
        :param concurrency: 最大并发数
        """
        if not messages:
            return 0

        # 1. 过滤：只分析尚未关联 Topic 或 Word 的消息
        # 先获取传入消息的 ID 集合
        msg_ids = [m.message_id for m in messages]
        
        # 查询这些 ID 中，已经存在于 MsgTopic 或 MsgWord 中的 ID
        # 使用 EXISTS 子查询来过滤
        sub_topic = MsgTopic.select().where(MsgTopic.message == Message.message_id)
        sub_word = MsgWord.select().where(MsgWord.message == Message.message_id)
        
        analyzed_query = (Message
                        .select(Message.message_id)
                        .where(
                            (Message.message_id << msg_ids) & 
                            (fn.EXISTS(sub_topic) | fn.EXISTS(sub_word))
                        ))
        
        analyzed_ids = {m.message_id for m in analyzed_query}
        
        # 真正需要分析的消息
        to_analyze = [m for m in messages if m.message_id not in analyzed_ids]
        
        total = len(to_analyze)
        if total == 0:
            # print("所有指定消息均已分析过。")
            return 0

        success = 0
        count = 0
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def worker(msg):
            nonlocal success, count
            async with sem:
                try:
                    # 调用你的消息分析逻辑（提取词汇和话题并存入数据库）
                    words, topics = await self.analyze_msg(msg)
                    async with lock:
                        if words or topics:
                            success += 1
                        count += 1
                        # 进度打印（可选）
                        if count % 10 == 0 or count == total:
                            print(f"Report Analysis Progress: {count}/{total} new messages processed")
                except Exception as e:
                    print(f"Error analyzing message {msg.message_id} in report flow: {e}")

        # 2. 并发执行
        tasks = [worker(msg) for msg in to_analyze]
        await asyncio.gather(*tasks)

        return success

    async def analyze_msg(self, msg: Message) -> Tuple[List[str],List[str]]:
        if msg.text is None or str(msg.text).strip() == "":
            return [],[]

        analyzed: bool = MsgTopic.select().where(MsgTopic.message == msg).exists() or MsgWord.select().where(MsgWord.message == msg).exists()
        if not analyzed:
            words: List[str] = self.segment_words_jieba(str(msg.text))
            print(f"Words segmented for message {msg.message_id}: {words}")
            for word in words:
                if len(word)>1:
                    word_obj: Word = Word.get_or_create(name=word, group=msg.group)[0]
                    MsgWord.create(message=msg, word=word_obj)
            

            topics: List[str] = await self.extract_topics(str(msg.text))
            print(f"Topics extracted for message {msg.message_id}: {topics}")
            for topic in topics:
                topic_obj: Topic = Topic.get_or_create(name=topic, group=msg.group)[0]
                MsgTopic.create(message=msg, topic=topic_obj)

            if words or topics:
                print(f"Message {msg.message_id} analyzed into {len(words)} words and {len(topics)} topics")
                return words, topics
            return [],[]
        return [],[]

    async def extract_topics(self, text: str) -> List[str]:
        saved_topics: List[MsgTopic] = MsgTopic.select()
        print(f"有{len(saved_topics)}个现成话题")
        prompt: str = f"""
        这是现成的话题列表：\n{saved_topics}\n
        接下来我需要你分析一段文本涉及的话题（至多5个，意思互不重叠），优先从话题列表中选取，列表中没有的话题可以补充，将所有分析出的话题输出为用空格分割的字符串，禁止输出多余的内容
        以下是文本原文：\n{text}
        """
        response: str|None = await ai_client.summary(prompt)
        print(f"Topic extraction response: {response}")
        if response is None or len(response) > 30:
            return []
        try:
            topics: List[str] = response.split()
        except:
            print(f"Topic extraction error: {response}")
            return []
        return topics

    async def segment_words_ai(self, text: str) -> List[str]:
        prompt: str = f"""请进行文本分词工作，能组成多于一个字的词的尽量组成多字词。
        分词结果不能包含标点、空格等特殊字符（但可以参考它们来进行分词）。
        以下词不应拆开：{reserved_words}。
        分割成词后，需要抛弃其中一些词，其余的保留。
        以下词应当抛弃的词有：{banned_words}以及常见标点。
        将分割出的词们输出为用空格分割的字符串。
        如果剩余的词已经没有了，则直接返回空字符串。
        禁止输出多余的内容。
        规则讲述完毕。以下是文本原文：\n“{text}”
        """
        response: str|None = await ai_client.summary(prompt)
        if response is None or len(response) > 30:
            return []
        try:
            words: List[str] = response.split()
        except:
            print(f"Word segmentation error: {response}")
            return []
        return words

    def segment_words_jieba(self, text: str) -> List[str]:
        # 1. 给保留词两端加空格
        for w in reserved_words:
            text = text.replace(w, f" {w} ")
        # 2. 将屏蔽词替换为空格
        for r in banned_regex:
            text = re.sub(r, ' ', text)
        # 3. 切词
        words = jieba.cut(text)
        # 4. 去除标点
        words = [re.sub(r'[^\w\s]', '', w) for w in words]
        # 5. 去除空白词
        words = [w for w in words if w.strip()]
        # 6. 去除屏蔽词
        words = [w for w in words if w not in banned_words]
        return words

    def get_group_comprehensive_stats(self, group: Group, daynum: int, n: int = 5) -> Dict[str, Any]:
        # 1. 时间边界
        now = datetime.now()
        today_5am = datetime.combine(now.date(), dt_time(5, 0))
        start_bound = today_5am - timedelta(days=daynum)
        
        # 2. 统计 SQL 表达式
        # 偏移5小时后的日期标签（5am-5am为一天）
        day_expr = (Message.time - SQL("interval '5 hours'")).cast('date')
        # 偏移5小时后的时间部分（用于衡量“晚度”）
        time_expr = (Message.time - SQL("interval '5 hours'")).cast('time')

        # --- A. 消息总量与活跃天统计 ---
        all_daily_stats = (Message
                        .select(day_expr.alias('day'), fn.COUNT(Message.message_id).alias('count'))
                        .where((Message.group == group), (Message.time >= start_bound))
                        .group_by(SQL('day'))
                        .order_by(SQL('count DESC')))
        
        daily_results_full = list(all_daily_stats)
        total_msg_count = sum(d.count for d in daily_results_full)
        top_chatted_dates = [{"date": str(d.day), "count": d.count} for d in daily_results_full[:n]]

        # --- B. 熬夜排行榜 (修复后的 DISTINCT ON 写法) ---
        # 在 Postgres 中使用 DISTINCT ON 时，order_by 的第一个字段必须和 distinct 中的字段一致
        night_owl_query = (Message
                        .select(Message, User, time_expr.alias('offset_time'))
                        .join(User, JOIN.LEFT_OUTER, on=(Message.sender == User.user_id))
                        .where((Message.group == group), (Message.time >= start_bound))
                        .distinct(day_expr) # 👈 关键：每一天只取一行
                        .order_by(day_expr, time_expr.desc())) # 👈 必须先按天排，再按时间降序

        # 将各日冠军拿出来，按“晚度”进行总排名，取前 n
        night_owls = sorted(list(night_owl_query), key=lambda x: x.offset_time, reverse=True)[:n]
        
        latest_chatted_dates = [
            {
                "full_time": m.time.strftime("%Y-%m-%d %H:%M:%S"),
                "sender": m.card if m.card else (m.sender.nickname if m.sender else "Unknown")
            } for m in night_owls
        ]

        # --- C. 高频词 (使用 .dicts() 确保数据干净) ---
        top_words_query = (MsgWord
                    .select(Word.name, fn.COUNT(MsgWord.id).alias('count'))
                    .join(Word).switch(MsgWord).join(Message)
                    .where((Message.group == group), (Word.group == group), (Message.time >= start_bound))
                    .group_by(Word.name).order_by(SQL('count DESC')).limit(n))
        
        top_words = [{"name": w.word.name, "count": w.count} for w in top_words_query]

        # --- D. 热门话题 ---
        top_topics_query = (MsgTopic
                    .select(Topic.name, fn.COUNT(MsgTopic.id).alias('count'))
                    .join(Topic).switch(MsgTopic).join(Message)
                    .where((Message.group == group), (Topic.group == group), (Message.time >= start_bound))
                    .group_by(Topic.name).order_by(SQL('count DESC')).limit(n))
        
        top_topics = [{"name": t.topic.name, "count": t.count} for t in top_topics_query]

        # --- E. 被 @ 排名 ---
        top_atted_query = (AtUser
                    .select(User.nickname, User.user_id, fn.COUNT(AtUser.id).alias('count'))
                    .join(User, on=(AtUser.user == User.user_id)).switch(AtUser).join(Message)
                    .where((Message.group == group), (Message.time >= start_bound))
                    .group_by(User.user_id, User.nickname).order_by(SQL('count DESC')).limit(n))

        top_atted_users = [{"user": f"{u.user.nickname}({u.user.user_id})", "count": u.count} for u in top_atted_query]

        return {
            "msg_count": total_msg_count,
            "avg_daily_msgs": round(total_msg_count / daynum, 2) if daynum > 0 else 0,
            "top_chatted_dates": top_chatted_dates,
            "latest_chatted_dates": latest_chatted_dates,
            "top_words": top_words,
            "top_topics": top_topics,
            "top_atted_users": top_atted_users,
            "start_date": start_bound.strftime("%Y-%m-%d %H:%M"),
            "end_date": now.strftime("%Y-%m-%d %H:%M"),
            "group_name": group.group_name
        }
    def format_stats_report(self, ans: dict) -> str:
        """
        格式化输出报告，括号内显示计数
        """
        if not ans or ans["msg_count"] == 0:
            return f"📊 【{ans.get('group_name', '未知群聊')}】暂无消息统计数据。"

        lines = [
            f"📊 【{ans['group_name']}】全方位数据报告",
            f"⏳ 统计时段：{ans['start_date']} 至 {ans['end_date']}",
            "-" * 30,
            f"📈 概况：总计消息({ans['msg_count']}条)，日均({ans['avg_daily_msgs']}条)",
            ""
        ]

        # 1. 活跃天
        if ans["top_chatted_dates"]:
            lines.append("🔥 【最活跃的日期】")
            for i, item in enumerate(ans["top_chatted_dates"], 1):
                lines.append(f" {i}. {item['date']} ({item['count']}条)")
            lines.append("")

        # 2. 熬夜榜
        if ans["latest_chatted_dates"]:
            lines.append("🌙 【熬夜之巅 (最晚发言)】")
            for i, item in enumerate(ans["latest_chatted_dates"], 1):
                lines.append(f" {i}. {item['full_time']} - {item['sender']}")
            lines.append("   (注：按凌晨5点结算，越接近5:00排名越靠前)")
            lines.append("")

        # 3. 内容关键词
        if ans["top_topics"] or ans["top_words"]:
            lines.append("🏷️ 【内容特征统计】")
            if ans["top_topics"]:
                t_str = "、".join([f"#{t['name']}#({t['count']}次)" for t in ans["top_topics"]])
                lines.append(f" ▪️ 热门话题：{t_str}")
            if ans["top_words"]:
                w_str = "、".join([f"{w['name']}({w['count']}次)" for w in ans["top_words"]])
                lines.append(f" ▪️ 高频词汇：{w_str}")
            lines.append("")

        # 4. 社交互动
        if ans["top_atted_users"]:
            lines.append("📢 【社交核心 (被@最多)】")
            for i, item in enumerate(ans["top_atted_users"], 1):
                lines.append(f" {i}. {item['user']} ({item['count']}次)")
            lines.append("")

        lines.append("-" * 30)
        lines.append("💡 自动统计报告生成完毕")
        
        return "\n".join(lines)
    async def get_group_report_with_auto_analyze(self, group: Group, daynum: int, n: int = 5) -> str:
        # 1. 先选出该时段内的所有消息对象
        now = datetime.now()
        start_bound = datetime.combine(now.date(), dt_time(5, 0)) - timedelta(days=daynum)
        
        relevant_messages = list(Message.select().where(
            (Message.group == group), 
            (Message.time >= start_bound)
        ))

        # 2. 自动分析这批消息中尚未处理的部分（确保统计数据完整）
        if relevant_messages:
            await self.analyze_given_msgs(relevant_messages, concurrency=15)

        # 3. 调用之前的统计函数（此时数据库里已经补全了 Word 和 Topic 记录）
        stats_dict = self.get_group_comprehensive_stats(group, daynum, n)
        
        # 4. 转化为字符串
        ans = self.format_stats_report(stats_dict)
        print(ans)
        return ans





msg_analyzer: MsgAnalyzer = MsgAnalyzer()





