# -*- coding:utf-8 -*-
import os
import requests
import hashlib
import time
import copy
import logging
import random

import smtplib
from email.mime.text import MIMEText


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API_URL
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

ENV = os.environ

HEADERS = {
    'Host': 'tieba.baidu.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
}
SIGN_DATA = {
    '_client_type': '2',
    '_client_version': '9.7.8.0',
    '_phone_imei': '000000000000000',
    'model': 'MI+5',
    "net_type": "1",
}

# VARIABLE NAME
COOKIE = "Cookie"
BDUSS = "BDUSS"
EQUAL = r'='
EMPTY_STR = r''
TBS = 'tbs'
PAGE_NO = 'page_no'
ONE = '1'
TIMESTAMP = "timestamp"
DATA = 'data'
FID = 'fid'
SIGN_KEY = 'tiebaclient!!!'
UTF8 = "utf-8"
SIGN = "sign"
KW = "kw"

s = requests.Session()


def get_tbs(bduss, max_retries=3, timeout=6):
    """获取tbs值，带重试机制"""
    logger.info("获取tbs开始")
    headers = copy.copy(HEADERS)
    headers.update({COOKIE: EMPTY_STR.join([BDUSS, EQUAL, bduss])})

    for attempt in range(1, max_retries + 1):
        try:
            response = s.get(url=TBS_URL, headers=headers, timeout=timeout)
            response.raise_for_status()  # 检查 HTTP 状态码
            data = response.json()  # 解析 JSON
            tbs = data.get(TBS)  # 避免 KeyError
            if tbs:
                logger.info("获取tbs成功: %s", tbs)
                return tbs
            else:
                logger.warning("获取tbs失败，响应内容: %s", data)
        except requests.exceptions.RequestException as e:
            logger.error("请求异常（第 %d 次尝试）：%s", attempt, str(e), exc_info=True)
        except ValueError as e:  # JSON 解析失败
            logger.error("JSON解析错误: %s", str(e), exc_info=True)
        time.sleep(2)  # 失败后等待 2 秒重试
    logger.error("获取tbs失败，达到最大重试次数 (%d)", max_retries)
    return None  # 返回 None 以便调用方处理失败情况


def get_favorite(bduss):
    logger.info("获取关注的贴吧开始")
    # 客户端关注的贴吧
    returnData = {}
    i = 1
    data = {
        'BDUSS': bduss,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': str(int(time.time())),
        'vcode_tag': '11',
    }
    data = encodeData(data)
    try:
        res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error("获取关注的贴吧出错" + e)
        return []
    returnData = res
    if 'forum_list' not in returnData:
        returnData['forum_list'] = []
    if res['forum_list'] == []:
        return {'gconforum': [], 'non-gconforum': []}
    if 'non-gconforum' not in returnData['forum_list']:
        returnData['forum_list']['non-gconforum'] = []
    if 'gconforum' not in returnData['forum_list']:
        returnData['forum_list']['gconforum'] = []
    while 'has_more' in res and res['has_more'] == '1':
        i = i + 1
        data = {
            'BDUSS': bduss,
            '_client_type': '2',
            '_client_id': 'wappc_1534235498291_488',
            '_client_version': '9.7.8.0',
            '_phone_imei': '000000000000000',
            'from': '1008621y',
            'page_no': str(i),
            'page_size': '200',
            'model': 'MI+5',
            'net_type': '1',
            'timestamp': str(int(time.time())),
            'vcode_tag': '11',
        }
        data = encodeData(data)
        try:
            res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
        except Exception as e:
            logger.error("获取关注的贴吧出错" + e)
            continue
        if 'forum_list' not in res:
            continue
        if 'non-gconforum' in res['forum_list']:
            returnData['forum_list']['non-gconforum'].append(res['forum_list']['non-gconforum'])
        if 'gconforum' in res['forum_list']:
            returnData['forum_list']['gconforum'].append(res['forum_list']['gconforum'])

    t = []
    for i in returnData['forum_list']['non-gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    for i in returnData['forum_list']['gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    logger.info("获取关注的贴吧结束")
    return t


def encodeData(data):
    s = EMPTY_STR
    keys = data.keys()
    for i in sorted(keys):
        s += i + EQUAL + str(data[i])
    sign = hashlib.md5((s + SIGN_KEY).encode(UTF8)).hexdigest().upper()
    data.update({SIGN: str(sign)})
    return data


# def client_sign(bduss, tbs, fid, kw):
#     # 客户端签到
#     logger.info("开始签到贴吧：" + kw)
#     data = copy.copy(SIGN_DATA)
#     data.update({BDUSS: bduss, FID: fid, KW: kw, TBS: tbs, TIMESTAMP: str(int(time.time()))})
#     data = encodeData(data)
#     res = s.post(url=SIGN_URL, data=data, timeout=10).json()
#     return res

def client_sign(bduss, tbs, fid, kw, max_retries=3):
    logger.info("开始签到贴吧：" + kw)
    data = copy.copy(SIGN_DATA)
    data.update({BDUSS: bduss, FID: fid, KW: kw, TBS: tbs, TIMESTAMP: str(int(time.time()))})
    data = encodeData(data)

    for attempt in range(1, max_retries + 1):
        try:
            res = s.post(url=SIGN_URL, data=data, timeout=10).json()
            if res.get("error_code") == "0":
                logger.info(f"[{kw}] 签到成功")
            else:
                logger.warning(f"[{kw}] 签到失败：{res}")
            return res
        except requests.exceptions.ReadTimeout:
            logger.warning(f"[{kw}] 请求超时，第 {attempt} 次重试中...")
        except requests.exceptions.RequestException as e:
            logger.error(f"[{kw}] 请求异常：{str(e)}", exc_info=True)
        time.sleep(2)  # 重试间隔

    logger.error(f"[{kw}] 签到失败：超过最大重试次数")
    return None

# def send_email(sign_list):
#     if ('HOST' not in ENV or 'FROM' not in ENV or 'TO' not in ENV or 'AUTH' not in ENV):
#         logger.error("未配置邮箱")
#         return
#     HOST = ENV['HOST']
#     FROM = ENV['FROM']
#     TO = ENV['TO'].split('#')
#     AUTH = ENV['AUTH']
#     length = len(sign_list)
#     subject = f"{time.strftime('%Y-%m-%d', time.localtime())} 签到{length}个贴吧"
#     body = """
#     <style>
#     .child {
#       background-color: rgba(173, 216, 230, 0.19);
#       padding: 10px;
#     }

#     .child * {
#       margin: 5px;
#     }
#     </style>
#     """
#     for i in sign_list:
#         body += f"""
#         <div class="child">
#             <div class="name"> 贴吧名称: { i['name'] }</div>
#             <div class="slogan"> 贴吧简介: { i['slogan'] }</div>
#         </div>
#         <hr>
#         """
#     msg = MIMEText(body, 'html', 'utf-8')
#     msg['subject'] = subject
#     smtp = smtplib.SMTP()
#     smtp.connect(HOST)
#     smtp.login(FROM, AUTH)
#     smtp.sendmail(FROM, TO, msg.as_string())
#     smtp.quit()

def main():
    if ('BDUSS' not in ENV):
        logger.error("未配置BDUSS")
        return
    b = ENV['BDUSS'].split('#')
    for n, i in enumerate(b):
        logger.info("开始签到第" + str(n) + "个用户" + i)
        tbs = get_tbs(i)
        favorites = get_favorite(i)
        for j in favorites:
            time.sleep(random.randint(1,5))
            client_sign(i, tbs, j["id"], j["name"])
        logger.info("完成第" + str(n) + "个用户签到")
    logger.info("所有用户签到结束")


if __name__ == '__main__':
    main()
