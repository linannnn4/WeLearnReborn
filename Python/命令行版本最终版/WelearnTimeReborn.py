import requests
import re
import sys
import base64
import json
import random
import time
from textwrap import wrap
import threading
from tqdm import tqdm
from prettytable import PrettyTable


global_session = requests.Session()
global_Cookies = ""


def acount_login(user, pwd):
    def generate_cipher_text(password):
        # 获取当前时间戳
        T0 = int(time.time() * 1000)

        # 将密码转换为字节数组
        P = password.encode("utf-8")
        V = (T0 >> 16) & 0xFF
        for byte in P:
            V ^= byte

        # 计算余数并调整时间戳
        remainder = V % 100
        T1 = (T0 // 100) * 100 + remainder

        # 将密码字节数组转换为十六进制字符串
        P1 = "".join(["{:02x}".format(byte) for byte in P])

        # 组合时间和密码的十六进制表示
        S = f"{T1}*{P1}"

        # 对组合后的字符串进行Base64编码
        S_encoded = S.encode("utf-8")
        E = base64.b64encode(S_encoded).decode("utf-8")

        return E, T1

    username = user
    password = pwd
    rturl = (
        requests.get(
            "https://welearn.sflep.com/user/prelogin.aspx?loginret=http%3a%2f%2fwelearn.sflep.com%2fuser%2floginredirect.aspx",
            allow_redirects=False,
        )
        .headers["Location"]
        .replace("https://sso.sflep.com/idsvr", "")
    )
    login_headers = {
        "host": "sso.sflep.com",
        "sec-ch-ua-platform": '"Windows"',
        "x-requested-with": "XMLHttpRequest",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
        "content-type": "application/x-www-form-urlencoded",
        "accept": "application/json, text/plain, */*",
        "origin": "https://sso.sflep.com",
        "referer": "https://sso.sflep.com/idsvr/login.html",
    }
    cipher_text, adjusted_timestamp = generate_cipher_text(password)
    data = {
        "rturl": rturl,
        "account": username,
        "pwd": cipher_text,
        "ts": str(adjusted_timestamp),
    }
    res = global_session.post(
        "https://sso.sflep.com/idsvr/account/login",
        data=data,
        headers=login_headers,
    )
    if res.ok and "code" in res.json() and res.json()["code"] == 0:
        print("登录成功!!")
        callback_rturl = rturl.replace("/connect/authorize", "")
        callback_url = (
            "https://sso.sflep.com/idsvr/connect/authorize/callback" + callback_rturl
        )

        # 跟随重定向处理SSO回调
        response = global_session.get(callback_url, allow_redirects=True)

        cookies_list = []
        for cookie in global_session.cookies:
            cookies_list.append(f"{cookie.name}={cookie.value}")
        global_Cookies = "; ".join(cookies_list)
        # cookie存着没啥*用，我在想能否保存到本地下次可以调用，但是看起来cookie会过期
    else:
        print("登录失败")
        exit(100)


# 获取书本信息
def get_books():
    url = "https://welearn.sflep.com/ajax/authCourse.aspx?action=gmc"
    header = {
        "Referer": "https://welearn.sflep.com/student/index.aspx",
    }
    res = global_session.get(
        url=url,
        headers=header,
        cookies=global_Cookies,
    )
    if not res or "clist" not in res.text:
        print("发生错误!!!可能是登录错误或没有课程!!!")
        print(res.text)
        input("按任意键退出")
        exit(0)

    try:
        json_data = res.json()
        return json_data["clist"]
    except:
        print("发生错误!可能是登录过期或cookie错误!")
        print(res.text)
        exit(200)


# 此函数借鉴的大佬的代码，对发包部分进行了部分修改
def startstudy(learntime, x, uid, cid):  # x为单元小节信息
    scoid = x["id"]
    url = "https://welearn.sflep.com/Ajax/SCO.aspx"
    req1 = global_session.post(
        url,
        data={"action": "getscoinfo_v7", "uid": uid, "cid": cid, "scoid": scoid},
        headers={"Referer": "https://welearn.sflep.com/student/StudyCourse.aspx"},
    )
    if "学习数据不正确" in req1.text:
        req1 = global_session.post(
            url,
            data={"action": "startsco160928", "uid": uid, "cid": cid, "scoid": scoid},
            headers={"Referer": "https://welearn.sflep.com/student/StudyCourse.aspx"},
        )
        req1 = global_session.post(
            url,
            data={"action": "getscoinfo_v7", "uid": uid, "cid": cid, "scoid": scoid},
            headers={"Referer": "https://welearn.sflep.com/student/StudyCourse.aspx"},
        )
        if "学习数据不正确" in req1.text:
            print("\n错误:", x["location"])
            return 0
    back = json.loads(req1.text)["comment"]
    if "cmi" in back:
        back = json.loads(back)["cmi"]
        cstatus = back["completion_status"]
        progress = back["progress_measure"]
        session_time = back["session_time"]
        total_time = back["total_time"]
        crate = back["score"]["scaled"]
    else:
        cstatus = "not_attempted"
        progress = session_time = total_time = "0"
        crate = ""
    url = "https://welearn.sflep.com/Ajax/SCO.aspx"
    req1 = global_session.post(
        url,
        data={
            "action": "keepsco_with_getticket_with_updatecmitime",
            "uid": uid,
            "cid": cid,
            "scoid": scoid,
            "session_time": session_time,
            "total_time": total_time,
        },
        headers={"Referer": "https://welearn.sflep.com/student/StudyCourse.aspx"},
    )

    for nowtime in range(1, learntime + 1):
        time.sleep(1)
        if nowtime % 60 == 0:
            url = "https://welearn.sflep.com/Ajax/SCO.aspx"
            session_time = str(int(session_time) + 60)
            total_time = str(int(total_time) + 60)
            # print(
            #     "-----------发包：--------------\nsession_time:",
            #     session_time,
            #     "total_time",
            #     total_time,
            #     "------------",
            # )
            req1 = global_session.post(
                url,
                data={
                    "action": "keepsco_with_getticket_with_updatecmitime",
                    "uid": uid,
                    "cid": cid,
                    "scoid": scoid,
                    "session_time": session_time,
                    "total_time": total_time,
                },
                headers={
                    "Referer": "https://welearn.sflep.com/student/StudyCourse.aspx"
                },
            )
    # 模拟退出学习时发包，一般是非整60秒
    url = "https://welearn.sflep.com/Ajax/SCO.aspx"
    req1 = global_session.post(
        url,
        data={
            "action": "savescoinfo160928",
            "cid": cid,
            "scoid": scoid,
            "uid": uid,
            "progress": progress,
            "crate": crate,
            "status": "unknown",
            "cstatus": cstatus,
            "trycount": "0",
        },
        headers={"Referer": "https://welearn.sflep.com/Student/StudyCourse.aspx"},
    )


class newTask(threading.Thread):
    def __init__(self, learntime, taskinfo, uid, cid):
        threading.Thread.__init__(self)
        self.deamon = True
        self.learntime = learntime
        self.taskinfo = taskinfo
        self.uid = uid
        self.cid = cid

    def run(self):
        startstudy(self.learntime, self.taskinfo, self.uid, self.cid)


def Add_A_unit(cid, uid, classid, unitidx, randommode, time_interval):
    url = (
        "https://welearn.sflep.com/ajax/StudyStat.aspx?action=scoLeaves&cid="
        + str(cid)
        + "&uid="
        + str(uid)
        + "&unitidx="
        + str(unitidx)
        + "&classid="
        + str(classid)
    )
    req = global_session.get(
        url,
        headers={
            "Referer": "https://welearn.sflep.com/student/course_info.aspx?cid="
            + str(cid)
        },
    )
    unit_info = json.loads(req.text)["info"]

    # ---------------------以上为获取单元小节信息---------------------
    # print(back)
    #
    # 定义一个多线程线程池启动函数
    def start_pool(running_pool, max_time):
        for temp in running_pool:
            temp.start()

        for nowtime in tqdm(
            range(1, max_time + 1),
            desc="学习进度",
            ncols=100,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}  Using:{elapsed}/Remaining:{remaining}",
        ):
            time.sleep(1)
        print("等待进程退出，准备下一波学习任务中")
        for temp in running_pool:
            temp.join()

    # ----------------------以下为开始刷时间的多线程设置---------------------
    running_pool = []
    Max_Thread = 30  # 设置最大线程数防止机器或服务器压力过大
    max_time = 0
    running_index = 0
    table = PrettyTable(["线程ID", "任务名称", "本次任务时长", "该小节总时长"])
    for task in unit_info:
        if randommode == False:
            time_interval_task = time_interval
            max_time = time_interval_task  # 未选择随机模式时最大时间为设置的时间
            temp_task = newTask(
                time_interval_task, task, uid, cid
            )  # 建立单个小节刷时长任务
            running_pool.append(temp_task)  # 加入到线程池
            running_index += 1
            table.add_row(
                [
                    running_index,
                    "..." + task["location"][-40:],
                    time_interval_task,
                    task["learntime"],
                ]
            )
            if len(running_pool) >= Max_Thread:
                print(table)
                start_pool(running_pool, max_time)  # 当线程池满时，启动线程池启动
                running_pool = []
                running_index = 0
                table = PrettyTable(
                    ["线程ID", "任务名称", "本次任务时长", "该小节总时长"]
                )
        # ----------------------------------------------------------------------------------------------
        # ----------------------------------------------------------------------------------------------
        else:
            time_interval_task = random.randint(time_interval[0], time_interval[1])
            max_time = max(
                max_time, time_interval_task
            )  # 选择随机模式时最大时间为随机时间中的最大
            temp_task = newTask(
                time_interval_task, task, uid, cid
            )  # 建立单个小节刷时长任务
            running_pool.append(temp_task)  # 加入到线程池
            running_index += 1
            table.add_row(
                [
                    running_index,
                    "..." + task["location"][-40:],
                    time_interval_task,
                    task["learntime"],
                ]
            )
            if len(running_pool) >= Max_Thread:
                print(table)
                start_pool(running_pool, max_time)  # 当线程池满时，启动线程池启动
                running_pool = []
                running_index = 0
                max_time = 0
                table = PrettyTable(
                    ["线程ID", "任务名称", "本次任务时长", "该小节总时长"]
                )

    # 遍历一个Unit结束
    if len(running_pool) > 0:
        print(table)
        start_pool(running_pool, max_time)  # 当单元结束了，线程池仍有任务时，启动线程池
        running_pool = []
    print("本单元学习结束，等待进程退出，准备下一单元学习任务中")


def clean_curse(cid):
    # https://welearn.sflep.com/student/course_info.aspx?cid=
    Unit_list_url = f"https://welearn.sflep.com/student/course_info.aspx?cid={cid}"
    search_unit_response = global_session.get(Unit_list_url)
    uid = re.search('"uid":(.*?),', search_unit_response.text).group(1)
    classid = re.search('"classid":"(.*?)"', search_unit_response.text).group(1)
    # 查找单元这一段抄的WelearnToSleep
    unit_url = "https://welearn.sflep.com/ajax/StudyStat.aspx"
    unit_response = global_session.get(
        unit_url,
        params={"action": "courseunits", "cid": cid, "uid": uid},
        headers={"Referer": "https://welearn.sflep.com/student/course_info.aspx"},
    )
    UNITS = unit_response.json()["info"]
    # print(UNITS)
    # print("[NO. 0]  按顺序完成全部单元课程")
    unitsnum = len(UNITS)
    unit_table = PrettyTable(["序号", "单元开放状态", "单元名称"])
    for i, x in enumerate(UNITS, start=1):
        if x["visible"] == "true":
            unit_table.add_row(
                [f"NO.{i:>2d}", "已开放", x["unitname"] + "  " + x["name"]]
            )
            # print(f'[NO.{i:>2d}]  [已开放]  {x["unitname"]}  {x["name"]}')
        else:
            unit_table.add_row(
                [f"NO.{i:>2d}", "未开放", x["unitname"] + "  " + x["name"]]
            )
            # print(f'[NO.{i:>2d}] ![未开放]! {x["unitname"]}  {x["name"]}')
    unit_table.align["单元名称"] = "l"
    print(unit_table)
    unitidx = int(input("\n\n请选择需要完成的单元序号(输入0为按顺序刷全部单元): "))
    # ----------------------------分割线---------------------------------
    #  说明：本分割线往上为单元选择，往下为刷课模式
    #   单元选择部分代码选择的使用welearnToSleep中的部分参考，感谢大佬开源
    # ----------------------------分割线---------------------------------

    # 时间长度选择
    time_interval = input(
        "请输入刷课时长(如想刷30秒,请输入30);\n或一个区间(如想刷180秒到240秒,请输入180,240):"
    )
    randommode = False
    if "," in time_interval:
        time_interval = time_interval.split(",")
        time_interval = [int(i) for i in time_interval]
        randommode = True
    else:
        time_interval = int(time_interval)

    # 开始刷课
    if unitidx == 0:  # 多单元情况
        for i in range(unitsnum):
            Add_A_unit(cid, uid, classid, i, randommode, time_interval)
            print("-" * 51)
            print("一个单元已完成(请等待10秒后开启下一个单元)")
            time.sleep(10)
        print("Task Completed! success")  # 程序终止退出锚点
    else:  # 单个单元情况
        unitidx -= 1
        Add_A_unit(cid, uid, classid, unitidx, randommode, time_interval)
        print("Task Completed! success")
    # 准备写个暴力模式,多个单元同时刷时长,线程撕到200+

    # unit_list = search_unit_response.text.split(r'<h4 class="panel-title">')
    # for i in unit_list:
    #     pass


if __name__ == "__main__":
    login_mode = input("1.使用账号密码登录\n2.输入cookie\n请选择登录方式(1/2):")
    if login_mode == "1":
        try:
            # 直接从命令行中获取
            username, password = sys.argv[1], sys.argv[2]
        except:
            username = input("请输入账号: ")
            password = input("请输入密码: ")
            acount_login(username, password)
    elif login_mode == "2":
        try:
            cookie = dict(
                map(lambda x: x.split("=", 1), input("请粘贴Cookie: ").split(";"))
                # map(lambda x: x.split("=", 1), raw_cookie.split(";"))
            )
        except:
            input("Cookie输入错误!!!")
            exit(0)
        for k, v in cookie.items():
            global_session.cookies[k] = v

    book_list = get_books()
    book_table = PrettyTable(["序号", "书名", "进度"])
    for index, book in enumerate(book_list):
        book_dict = dict(book)
        book_table.add_row([index, book_dict["name"], str(book_dict["per"]) + "%"])
    print(book_table)

    book_number = int(input("请输入要学习的书籍序号(选择一本书):"))
    book_scid = book_list[book_number]["scid"]
    book_cid = book_list[book_number]["cid"]

    clean_curse(book_cid)
