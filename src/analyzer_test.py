from services.msg_analyzer import msg_analyzer
from models.group import Group
import asyncio

if __name__ == '__main__':
    asyncio.run(msg_analyzer.analyze_all())
    msg_analyzer.get_group_comprehensive_stats(
        Group.get(Group.group_id == '1050660050'),30,5)