import requests
import re
import sys
import base64
import time
from textwrap import wrap
from random import randint


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


# 饶恕小的实在是在一坨js里面找不到请求的url，这个函数中大部分url是借鉴WelearnCurriculumFinsh QWQ
def clean_A_unit(cid, uid, classid, unitidx, randommode, mycrate):
    way1Succeed, way2Succeed, way1Failed, way2Failed = 0, 0, 0, 0
    ajaxUrl = "https://welearn.sflep.com/Ajax/SCO.aspx"
    infoHeaders = {
        "Referer": f"https://welearn.sflep.com/student/course_info.aspx?cid={cid}",
    }
    response = global_session.get(
        f"https://welearn.sflep.com/ajax/StudyStat.aspx?action=scoLeaves&cid={cid}&uid={uid}&unitidx={unitidx}&classid={classid}",
        headers=infoHeaders,
    )
    total_count = len(response.json()["info"])
    cnt_idx = 0
    for course in response.json()["info"]:
        if course["isvisible"] == "false":  # 跳过未开放课程
            print(f'[!!跳过!!]    {course["location"]}')
            cnt_idx += 1
        elif "未" in course["iscomplete"]:  # 章节未完成
            print(f'[即将完成]    {course["location"]}')
            if randommode is True:
                crate = str(randint(mycrate[0], mycrate[1]))
            else:
                crate = str(mycrate)
            data = (
                '{"cmi":{"completion_status":"completed","interactions":[],"launch_data":"","progress_measure":"1","score":{"scaled":"'
                + crate
                + '","raw":"100"},"session_time":"0","success_status":"unknown","total_time":"0","mode":"normal"},"adl":{"data":[]},"cci":{"data":[],"service":{"dictionary":{"headword":"","short_cuts":""},"new_words":[],"notes":[],"writing_marking":[],"record":{"files":[]},"play":{"offline_media_id":"9999"}},"retry_count":"0","submit_time":""}}[INTERACTIONINFO]'
            )

            id = course["id"]
            global_session.post(
                ajaxUrl,
                data={
                    "action": "startsco160928",
                    "cid": cid,
                    "scoid": id,
                    "uid": uid,
                },
                headers={
                    "Referer": f"https://welearn.sflep.com/Student/StudyCourse.aspx?cid={cid}&classid={classid}&sco={id}"
                },
            )
            response = global_session.post(
                ajaxUrl,
                data={
                    "action": "setscoinfo",
                    "cid": cid,
                    "scoid": id,
                    "uid": uid,
                    "data": data,
                    "isend": "False",
                },
                headers={
                    "Referer": f"https://welearn.sflep.com/Student/StudyCourse.aspx?cid={cid}&classid={classid}&sco={id}"
                },
            )
            print(f">>>>>>>>>>>>>>正确率:{crate:>3}%", end="  ")
            if '"ret":0' in response.text:
                print("way1:success!", end="  ")
                way1Succeed += 1
            else:
                print("way1:failed!", end="  ")
                way1Failed += 1

            response = global_session.post(
                ajaxUrl,
                data={
                    "action": "savescoinfo160928",
                    "cid": cid,
                    "scoid": id,
                    "uid": uid,
                    "progress": "100",
                    "crate": crate,
                    "status": "unknown",
                    "cstatus": "completed",
                    "trycount": "0",
                },
                headers={
                    "Referer": f"https://welearn.sflep.com/Student/StudyCourse.aspx?cid={cid}&classid={classid}&sco={id}"
                },
            )
            #                sleep(1) # 延迟1秒防止服务器压力过大
            if '"ret":0' in response.text:
                print("way2:success!")
                way2Succeed += 1
            else:
                print("way1:failed!")
                way2Failed += 1

            cnt_idx += 1
            percent = cnt_idx / total_count * 100
            print(f"已完成{percent:.2f}%:  ", end="")
            print("◆" * int(percent / 2.5), end="")
            print("◇" * (40 - int(percent / 2.5)))

        else:  # 章节已完成
            print(f'[ 已完成 ]    {course["location"]}')
            cnt_idx += 1


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
    print(UNITS)
    print("[NO. 0]  按顺序完成全部单元课程")
    unitsnum = len(UNITS)
    for i, x in enumerate(UNITS, start=1):
        if x["visible"] == "true":
            print(f'[NO.{i:>2d}]  [已开放]  {x["unitname"]}  {x["name"]}')
        else:
            print(f'[NO.{i:>2d}] ![未开放]! {x["unitname"]}  {x["name"]}')
    unitidx = int(
        input(
            "\n\n请选择需要完成的单元序号（上方[]内的数字，输入0为按顺序刷全部单元）： "
        )
    )
    # ----------------------------分割线---------------------------------
    #  说明：本分割线往上为单元选择，往下为刷课模式
    #   单元选择部分代码选择的使用welearnToSleep中的部分参考，感谢大佬开源
    # ----------------------------分割线---------------------------------

    # 正确率选择
    accuracy = input("请输入刷课正确率(0-100)或一个区间,如80,100:")
    randommode = False
    if "," in accuracy:
        accuracy = accuracy.split(",")
        accuracy = [int(i) for i in accuracy]
        randommode = True
    else:
        accuracy = int(accuracy)
    # 开始刷课
    if unitidx == 0:
        for i in range(unitsnum):
            clean_A_unit(cid, uid, classid, i, randommode, accuracy)
            print("-" * 51)
            print("一个单元已完成(请等待10秒后开启下一个单元)")
            time.sleep(1)
        print("Task Completed! success")  # 程序终止退出锚点
    else:
        unitidx -= 1
        clean_A_unit(cid, uid, classid, unitidx, randommode, accuracy)
        print("Task Completed! success")

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
            # raw_cookie = r"_ga=GA1.2.127515000.1711857002; _gid=GA1.2.1617536274.1731552469; area=dbB; acw_tc=1a0c639117316472740112005e00e5d3bb5a4b7d483a43af996140cebad40f; ASP.NET_SessionId=muill3jpb4ewyaszdoh5yf32; .AspNet.Cookies=ONi4iFy3VMrRlxU_novtJSusswKAK88mNZ8WwdT2zK0kwcIaBjWofqxY5F1GpwnMJp2E-E4V-__TbquTjOGRK_hWZl2j8hRRjklxF_7Nkxh5t7vLgShJFxeGOMhosroqfqHD3D7Kc6bf7rHYSaABabgyKXON5-luBGZWGyoGR93xyLxXCzaQ1fd6F38s2LOUgnvTRuPChVw99GsuXP6-lnqQEffq2wk8MqmlWyAQ7ZIbHh381xYvc0JD7aGyCaOaZFMJgWvsdySoXyeg39fuCgrM2xRn7a9hQalBIAm8WSp5I1gae8h9T5wJ8nsSwCKJ4F65TYA1-PvW4oQ-6wxlmK0HXoLS90tExJ0OxQacq1z8lm0uZiQP6aWlL4mKV7I5hw2ehVON1qOCDxxM4EaPV74mebwnj1jdoWwFdEWjf0_DBvwxOEomTMgqppdKvaik0GN_ixuOgOlxEyz1B9Nb2Up0uQVgRHjrwn1FfPB4ifYZrKiMKR96dZO_yKgY1ZIUyLOnujBCg5h2v2DvnIUKlMuiKydGTea4P2AiDTTL6l_U2HtM3XKrmKAeby2MBCm9iVc1QGhQCVnbh5cI_t4H71eHsCQPGH7Z5d7RVLO92XMlfPLujzVmM59Ql-ROXLkJ7RB2mtBj9XaIxj3Esny8cJu6ybuV-iPCM4a4AuNciA_IJkfsT2i-CTO6P1WlpLGJP9pMG1FPFupM-jAZ_wdOdBDGeLQU0FvhGG29bOnkPDvxdkEHznHXjJdP5NVThjKyCYs47_Y8C0lERu-Nv1nK6wMPNRdDU2gbv636tcqrzeLWc1PosQetHDUwJH1sHdc_YA9Vr03dmzRU-zquYhzw-SC6w1ZZ0e2S0w9voKA1DD6OZwJbZ0P1muTmsv_GZ_x1MkBpzIBT8DpgHG05ImKFR5jJOe2dKeA-X45h9iACnOs6IuvxJJAWGdqqzQMsZat2v-q6jgPvzkwqYXZZ6zFnwJQfdItqMap1LecrfLMwe7ynePn0ohN9MXJ7N8Thodl6XjV3fVWj9IuisYzS_Sm9znzgc8byja4v36WNYPU1LeAdlueuSDBBIGQIH9j4WPytsjZN76H6Hwdk5Ppw64gJPbyrwmCkE0Lhn_1XrmvLf7xKMurvlnVafMkRb7UPikZnz1-Ab0vD3gQg1fC69__-4BK_pmtimumGPcqGkVYMIN_THywYOKHp6UUUWkK6QpMX8XsYywUqTEySl_AFcNkDQWFV7uq_IzFnFuF9macG79QF56W07U5_jHfpe0G1SyMXMx8bvdlYBf0DrblOR_woLm2WvmE5kpFdiEWisoI10UvZmwNMnDukoPHDwI1CP2r0qJ9CKL-CGPZR9du_sF7ELgf7iL6BQvI8ev0mtebVU47IZgLvQMKaVQgM4e22JLmOXxk2z14sVDDQSMZsTp_7QJ8XgFS8aattjKvEnk86J3LkJAZ9-X53FnmZtTCXodfUlTkYNDt1Z9_ngSNwrmKBQNMnzzV-sBia0sKeFQg_pt0EImh7-hEo9fFlGDoHF8hDvDHuXZBiuq8ipv0ZopbmBCD_MBuGLAyj7VFgKQlEfYMgemXKgnHl6miaXqVLywNp905f6T-s6h3H7L56LAp8rY-iqx2gW-kSjn4w6M4AkdvsL73k5fzkYAFPtxGUsNgjbWX8PYT9C8aLeiquKjeLkQlCvkVXbhonXL9MNGOIC6JWXZEgcxeOW7vYSIfTH6g8jk05jLeDMk9psDx4W0qTBu_IKkUo0VGmkuMBRAf07MN0B13nA1XNmLDIFaBYRdGRk8X9BVNMK1_DwFfXt3L37WS3uwKnNHPswpsOx3gL-nlX32o2V7JzQbshBApcrfICT5YVjlDsKlmIokY28aMhF2w6R7c_orgnKS6jIIIhHdiYbBFC9cwB-58650Dhylw8x7cxreUNyHK2qXZYupd5z0e44NW1nuH26ThLYWOtXOWuxosvW3FqCVL40vIQhVoNGhh_YsrnI9JwWcbY9oaDvpciuV4Ukd4qpr2cu8fXRX1Vm7FMYBwRidLBojcFf_YlazDHmFFH6QIFu99XuH-QKSj7WZ8oswh9016GDzheDcLotIpyIOZCNAzFZ0PIBEyaT51rLeV0PPuqYijFleaQygKS4XURNqFZLf8M6KG3XLQy63uzubuDOSWE963E91za7_gf1QryrH0Hl7vLQJGGCR4pG-9LdcFDzTETVm2qmWInUebk5x4JslpZv1xscldjRBSVktYq6rWjT3MqiR_SXt0HA8CLDB-ORBxRbHjmI3ytSwJiQwY1RuCobAA6zkjoyntYEwBXKgrLxbYP_yq4nTXtUKcqomYtUzN73P6mT8oemmx6UuA2wIMdEdkReZtRqg1yytSdQ6Pr2PxtkPhsYD-iGltJ6edQsucBg8O6Ig7u6w2bz2crhO_eZvMfFqIoRRSG6YXsJ7UBgqLiQ3EnvkRTmpaOy49tO8Gz2QFa7ikzmivlF_koVvfBFoPLqInjXPD2Oi2ZypAZ_MpQtUFTiUpD3UYLGj_62nOdBmzF-dYyMF8UFsJstUJ1aoq-tErEpeq7eHE-5TThJaU00METVu8b5ocl4ixwRmTkBGcQwwa-4LXqOBGNdBDWg-UldDEMVH180NXm6FipxkdBQFNo0gqtGf-EHmybI9Qa6yCqGEUakZzGZr0EH3R5PArPRszM8uvmXu-dRH4KcdVI3SfonupcGzzIF2Yu5FhwEsw1bmXE5MqPZHciM2KLZUfWEaGRgN_WXT83d1RaQHtNZ0qd5e-uHaVyqt5KYK_J12CaS8s; _ga_PNJRS2N8S4=GS1.2.1731647271.36.0.1731647271.0.0.0"
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

    for index, book in enumerate(book_list):
        book_dict = dict(book)
        print(f"[{index}] {book_dict['name']} 已完成: {book_dict['per']}%")

    book_number = int(input("请输入要学习的书籍序号(选择一本书):"))
    book_scid = book_list[book_number]["scid"]
    book_cid = book_list[book_number]["cid"]

    clean_curse(book_cid)
