# Standard Library
import json
import time
import base64
import requests
from typing import *
from pathlib import Path

# Third-Party Library
import numpy as np
import pandas as pd
from tqdm import tqdm
from Crypto.Cipher import AES

# My Library
from utils import red, type_check

def get_timestamp() -> int:
    """
    get_timestamp 获取当前的时间戳
    Returns:
        int: 当前时间戳
    """
    return int(round(time.time() * 1000))

def encrypt_password(key: str, password: str) -> str:
    """
    encrypt_password 根据key对password进行AES加密
    Args:
        key (str): 加密的key
        password (str): 加密的密码
    Returns:
        str: 加密后得到的密码
    """
    type_check(key, str)
    type_check(password, str)
    def _pkcs7padding(text: str) -> str:
        type_check(text, str)
        s_len, b_len = len(text), len(text.encode("utf-8"))
        p_size = s_len if (s_len == b_len) else b_len
        padding = 16 - p_size % 16
        p_text = chr(padding) * padding
        return text + p_text
    padded_password = _pkcs7padding(text=password)
    encrypted_bytes = AES.new(key=key, mode=AES.MODE_ECB).encrypt(padded_password.encode("utf-8"))
    return str(base64.b64encode(encrypted_bytes), encoding="utf-8")


class Ehall:
    captcha_path: Path = Path(__file__).resolve().parent.joinpath("验证码.jpg")
    ehall_url: str = "http://org.xjtu.edu.cn/openplatform/login.html"
    
    def __init__(self, id: str, pwd: str) -> None:
        """
        __init__ Ehall Python接口

        Args:
            id (str): 学生号
            pwd (str): 密码
        """
        self.id = id if type_check(id, str) else None
        self.pwd = pwd if type_check(pwd, str) else None
        self.session = requests.Session()
    
    def _login(self) -> bool:
        """
        _login 利用 requests 模拟登录Ehall
        Returns:
            bool: 登录成功返回 True; 登录失败返回 False
        """
        def _start_authorize() -> bool:
            if not (
                r := self.session.get(
                    url='https://org.xjtu.edu.cn/openplatform/oauth/authorize',
                    data={
                        'appID': '1030',
                        'redirectUri': 'http://ehall.xjtu.edu.cn/amp-auth-adapter/loginSuccess',
                        'scope': 'user_info'
                    }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, start authorization fail!")
                return False
            return True
        
        def _get_captcha() -> bool:
            if not (
                r := self.session.get(
                    url='https://org.xjtu.edu.cn/openplatform/g/admin/getIsShowJcaptchaCode',
                    data={'userName': id, '_': get_timestamp()}
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, get captcha fail!")
                return False
            # base64编码的验证码
            data = r.json()
            if data['data']:
                data = self.session.post(
                    'https://org.xjtu.edu.cn/openplatform/g/admin/getJcaptchaCode',
                    headers={'Content-Type': 'application/json;charset=UTF-8'}
                ).json()
                img = base64.b64decode(data['data'])
                with self.captcha_path.open(mode="wb") as file:
                    file.write(img)
            return True

        def _get_token() -> Union[bool, str]:
            captcha = "" if not self.captcha_path.exists() else input("请输入验证码 (验证码.jpg): ")
            if not (
                r := self.session.post(
                    url="https://org.xjtu.edu.cn/openplatform/g/admin/login",
                    data=json.dumps({
                        'username': self.id,
                        'pwd': encrypt_password(key="0725@pwdorgopenp", password=self.pwd),
                        'loginType': 1,
                        'jcaptchaCode': captcha
                    }),
                    headers={'Content-Type': 'application/json;charset=utf-8'}
                )
            ):
                red(f"{r.status_code}, {r.reason}, get token fail!")
                return False
            # 设置成功登录后服务器返回的cookie
            data = r.json()
            if data["code"] == 0:
                self.session.cookies.set(
                    "open_Platform_User", str(data["data"]["tokenKey"])
                )
                self.session.cookies.set(
                    "memberId", str(data["data"]["orgInfo"]["memberId"])
                )
                return data["data"]["orgInfo"]["memberId"]
            return False
        
        def _enter_home(memberID: str) -> bool:
            if not (
                r := self.session.get(
                    url="https://org.xjtu.edu.cn/openplatform/g/admin/getUserIdentity",
                    params={"memberId": memberID, "_": get_timestamp()}
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter homepage 1 fail!")
                return False
            data = r.json()
            if not (
                r := self.session.get(
                    url="https://org.xjtu.edu.cn/openplatform/oauth/auth/getRedirectUrl",
                    params={"userType": data["data"][0]["userType"], "personNo": data["data"][0]["personNo"], "_": get_timestamp()}
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter homepage 2 fail!")
                return False
            data: dict = r.json()
            if (hp_url := data.get("data", None)) is None:
                return False
            # 进入主页
            if not (
                r := self.session.get(
                    url=hp_url
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter homepage 3 fail!")
                return False
            return True
        
        # 登录 ehall
        self.session.cookies.set(
            'cur_appId_', 'GRt5IN2Ni3M='
        )
        if _start_authorize():
            if _get_captcha():
                if (memberID := _get_token()) is not None:
                    if (source := _enter_home(memberID)):
                        print(source)
                        return True
                    else:
                        red(_enter_home.__name__)
                else:
                    red(_get_captcha.__name__)
            else:
                red(_start_authorize.__name__)
        return False

    def get_course_info(self, cache_path: Optional[Path] = None) -> pd.DataFrame:
        def _enter_courses_query() -> bool:
            if not (
                r := self.session.get(
                    url="http://ehall.xjtu.edu.cn/jsonp/appIntroduction.json",
                    data={
                        "appId": 4766853624865322,
                        "_": get_timestamp()
                    }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 1 fail!")
                return False
            if not (
                r := self.session.get(
                    url="http://ehall.xjtu.edu.cn/jsonp/sendRecUseApp.json",
                    data={
                        "appId": 4766853624865322,
                        "_": get_timestamp()
                    }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 2 fail!")
                return False
            if not (
                r := self.session.get(
                    url="http://ehall.xjtu.edu.cn/jwapp/sys/funauthapp/api/getAppConfig/kccx-4766853624865322.do",
                    params={
                        "v": "07488889075885421"
                }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 3 fail!")
                return False
            if not (
                r := self.session.post(
                    url="http://ehall.xjtu.edu.cn/jwapp/sys/jwpubapp/modules/bb/cxjwggbbdqx.do",
                    params={
                        "SFQY": 1,
                        "APP": 4766853624865322
                    },
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 4 fail!")
                return False
            if not (
                r := self.session.get(
                    url="http://ehall.xjtu.edu.cn/jwapp/sys/emappagelog/config/kccx.do"
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 5 fail!")
                return False
            if not (
                r := self.session.post(
                    url="http://ehall.xjtu.edu.cn/jwapp/sys/kccx/modules/kccx.do",
                    data={
                        "*json": 1
                    }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 6 fail!")
                return False
            if not (
                r := self.session.post(
                    url="http://ehall.xjtu.edu.cn/jwapp/sys/kccx/modules/kccx/kcxxcx.do",
                    data={
                        "*searchMeta": 1
                    }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, enter course query 7 fail!")
                return False
            return True
        
        def _get_batch(pageSize: int, pageNumber: int) -> List[dict]:
            cc = []
            if not (
                r := self.session.post(
                    url="http://ehall.xjtu.edu.cn/jwapp/sys/kccx/modules/kccx/kcxxcx.do",
                    data={
                        "KCZTDM": 1,
                        "pageSize": pageSize,
                        "pageNumber": pageNumber
                    }
                )
            ).ok:
                red(f"{r.status_code}, {r.reason}, get_batch fail!")
                return False
            for row in r.json()["datas"]["kcxxcx"]["rows"]:
                cc.append(
                    {
                        "课程名": row["KCM"],
                        "英文课程名": row["YWKCM"],
                        "学分": row["XF"],
                        "学时": row["XS"],
                        "实验学时": row["SJXS"],
                        "课程号": row["KCH"],
                        "开课学院": row["KKDWDM_DISPLAY"],
                        "开课对象": row["KCCCDM_DISPLAY"],
                        "授课语种": row["SKYZDM_DISPLAY"],
                        "授课语种代码": row["SKYZDM"],
                        "课程版本": row["KCBBDM"],
                        "课程类型": row["KCSPDM_DISPLAY"]
                    }
                )
            return cc

        # 获取课程信息
        cache_path = Path(__file__).resolve().parent.joinpath("全校课程.xlsx") if not Path is None else Path
        if not cache_path.exists():
            assert self._login(), red("Ehall 登录失败!")
            assert _enter_courses_query(), red("进入课程查询界面失败!")
            couses = []
            for idx in (t_bar := tqdm(range(9936 // 96 + 1))):
                t_bar.set_description(f"Batch {idx:>3d}: ")
                couses.extend(
                    _get_batch(
                        pageSize=96,
                        pageNumber=idx + 1
                    )
                )
            couses = pd.DataFrame(couses)
            couses.to_excel(cache_path)
        else:
            couses = pd.read_excel(cache_path, index_col=0, header=0)
        return couses



if __name__ == "__main__":
    c = Ehall(
        id="2196113760", 
        pwd="222222222"
    ).get_course_info(None)
    print(c)