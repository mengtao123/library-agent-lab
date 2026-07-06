# -*- coding: utf-8 -*-
"""图书馆业务数据模拟"""

# 读者数据
READERS = {
    "R001": {
        "reader_id": "R001",
        "name": "张三",
        "department": "计算机系",
        "max_borrow": 5,
        "borrowed_count": 2,
        "is_valid": True,
        "fees": 0.0
    },
    "R002": {
        "reader_id": "R002",
        "name": "李四",
        "department": "数学系",
        "max_borrow": 5,
        "borrowed_count": 5,
        "is_valid": False,
        "fees": 15.5
    },
    "R003": {
        "reader_id": "R003",
        "name": "王五",
        "department": "物理系",
        "max_borrow": 5,
        "borrowed_count": 1,
        "is_valid": True,
        "fees": 0.0
    },
}

# 书籍数据
BOOKS = {
    "B001": {
        "book_id": "B001",
        "title": "三体",
        "author": "刘慈欣",
        "isbn": "978-7-5366-9293-0",
        "status": "在馆",
        "location": "3楼A区"
    },
    "B002": {
        "book_id": "B002",
        "title": "百年孤独",
        "author": "马尔克斯",
        "isbn": "978-7-5442-5500-5",
        "status": "已借出",
        "location": "2楼B区"
    },
    "B003": {
        "book_id": "B003",
        "title": "算法导论",
        "author": "CLRS",
        "isbn": "978-7-111-40701-0",
        "status": "在馆",
        "location": "4楼C区"
    },
    "B004": {
        "book_id": "B004",
        "title": "人类简史",
        "author": "赫拉利",
        "isbn": "978-7-5086-5847-3",
        "status": "在馆",
        "location": "3楼B区"
    },
}

# 借阅记录
BORROW_RECORDS = {
    "BR001": {
        "record_id": "BR001",
        "reader_id": "R001",
        "book_id": "B002",
        "borrow_date": "2026-06-01",
        "due_date": "2026-06-15",
        "return_date": None,
        "status": "借出中"
    },
    "BR002": {
        "record_id": "BR002",
        "reader_id": "R002",
        "book_id": "B001",
        "borrow_date": "2026-05-20",
        "due_date": "2026-06-03",
        "return_date": None,
        "status": "已逾期"
    },
}
# ============================================================
# RAG 知识库：图书馆政策/规则
# ============================================================

POLICIES = {
    "借阅规则": "每位读者最多可借5本书，借阅期限为14天，可续借1次（续借7天）。",
    "逾期政策": "图书逾期未还将按每本每天0.5元收取逾期费，超过30天未还将暂停借阅资格。",
    "丢失赔偿": "图书丢失需按原价赔偿，若图书已绝版则按原价3倍赔偿。",
    "借阅资格": "读者需持有效校园卡方可借书，欠费超过10元或逾期图书超过2本将暂停借阅资格。",
    "预约规则": "当图书全部借出时，读者可在线预约，预约成功后图书归还时优先通知。",
}