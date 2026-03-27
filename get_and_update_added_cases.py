import ast
import datetime
import json
import os
import re
import shutil
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Optional

import browser_cookie3
import requests
from bs4 import BeautifulSoup

sleep_sec = 2
atcoder_cookie_domain = "atcoder.jp"
atcoder_cookie_profile = os.environ.get("ATCODER_COOKIE_PROFILE", "Default")
atcoder_cookie_browsers = tuple(
    browser_name.strip().lower()
    for browser_name in os.environ.get(
        "ATCODER_COOKIE_BROWSER", "chrome,edge,firefox"
    ).split(",")
    if browser_name.strip() != ""
)
default_user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)
contest_archive_urls = (
    "https://atcoder.jp/contests/archive",
    "https://atcoder.jp/contests/archive?ratedType=0&category=20&keyword=",
)
target_contest_name_pattern = re.compile(r"(?:a[brg]c\d{3}|awc\d{4})")
testcases_json_path = Path("testcases.json")
legacy_testcases_txt_path = Path("testcases.txt")


class MaxRetriesExceededError(Exception):
    pass


class AtCoderLoginError(Exception):
    pass


def legacy_testcases_to_json_data(
    legacy_data: dict[tuple[str, str], list[str]],
) -> dict[str, dict[str, list[str]]]:
    """旧形式の tuple キー辞書を JSON 向けの入れ子辞書へ変換"""
    json_data: dict[str, dict[str, list[str]]] = {}
    for (contest_name, task_name), testcases in legacy_data.items():
        if contest_name not in json_data:
            json_data[contest_name] = {}
        json_data[contest_name][task_name] = testcases
    return json_data


def load_testcases_data() -> dict[str, dict[str, list[str]]]:
    """テストケース一覧を JSON から読み込む。旧 txt 形式があれば自動変換する"""
    if testcases_json_path.exists():
        with testcases_json_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    if legacy_testcases_txt_path.exists():
        with legacy_testcases_txt_path.open("r", encoding="utf-8") as f:
            legacy_data = ast.literal_eval(f.read().strip())
        json_data = legacy_testcases_to_json_data(legacy_data)
        save_testcases_data(json_data)
        return json_data

    return {}


def save_testcases_data(testcases_data: dict[str, dict[str, list[str]]]) -> None:
    """テストケース一覧を JSON 形式で保存"""
    with testcases_json_path.open("w", encoding="utf-8") as f:
        json.dump(testcases_data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_browser_cookie_config(browser_name: str) -> tuple[Path, object]:
    """通常ブラウザの cookie DB ルートと loader を取得"""
    browser_configs = {
        "chrome": (
            Path.home() / "AppData/Local/Google/Chrome/User Data",
            browser_cookie3.chrome,
        ),
        "edge": (
            Path.home() / "AppData/Local/Microsoft/Edge/User Data",
            browser_cookie3.edge,
        ),
        "firefox": (
            Path(),
            browser_cookie3.firefox,
        ),
    }

    if browser_name not in browser_configs:
        raise AtCoderLoginError(f"未対応のブラウザです: {browser_name}")

    return browser_configs[browser_name]


def copy_browser_cookie_file(browser_name: str, cookie_file: Path) -> Path:
    """cookie DB を一時ファイルへコピー"""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        shutil.copy2(cookie_file, temp_path)
    except PermissionError as e:
        temp_path.unlink(missing_ok=True)
        raise AtCoderLoginError(
            f"{browser_name} の cookie DB を読めませんでした。"
            f"{browser_name} を閉じてから再実行してください。"
        ) from e

    return temp_path


def filter_atcoder_cookies(
    cookie_jar: requests.cookies.RequestsCookieJar,
) -> requests.cookies.RequestsCookieJar:
    """AtCoder 用の cookie だけを抽出"""
    filtered_cookies = requests.cookies.RequestsCookieJar()
    for cookie in cookie_jar:
        if cookie.domain.lstrip(".").endswith(atcoder_cookie_domain):
            filtered_cookies.set_cookie(cookie)
    return filtered_cookies


def load_atcoder_cookies_from_browser(
    browser_name: str,
) -> requests.cookies.RequestsCookieJar:
    """指定ブラウザの通常プロファイルから AtCoder の cookie を読む"""
    browser_root, loader = get_browser_cookie_config(browser_name)

    if browser_name == "firefox":
        try:
            all_cookies = loader()
        except Exception as e:
            raise AtCoderLoginError(
                f"{browser_name} の cookie を読めませんでした。{e}"
            ) from e

        filtered_cookies = filter_atcoder_cookies(all_cookies)
        if len(filtered_cookies) == 0:
            raise AtCoderLoginError(
                f"{browser_name} の通常プロファイルに AtCoder の cookie が見つかりませんでした。"
                "通常ブラウザで AtCoder にログインしてから再実行してください。"
            )

        return filtered_cookies

    cookie_file = browser_root / atcoder_cookie_profile / "Network" / "Cookies"
    key_file = browser_root / "Local State"

    if not cookie_file.exists():
        raise AtCoderLoginError(
            f"{browser_name} の cookie DB が見つかりませんでした: {cookie_file}"
        )
    if not key_file.exists():
        raise AtCoderLoginError(
            f"{browser_name} の Local State が見つかりませんでした: {key_file}"
        )

    temp_cookie_file = copy_browser_cookie_file(browser_name, cookie_file)
    try:
        try:
            all_cookies = loader(
                cookie_file=str(temp_cookie_file), key_file=str(key_file)
            )
        except Exception as e:
            raise AtCoderLoginError(
                f"{browser_name} の cookie 復号に失敗しました。"
                "最近の Chrome / Edge では通常プロファイルを直接読めないことがあります。"
                "Firefox を使うか、対象ブラウザを閉じてから再実行してください。"
            ) from e
    finally:
        temp_cookie_file.unlink(missing_ok=True)

    filtered_cookies = filter_atcoder_cookies(all_cookies)
    if len(filtered_cookies) == 0:
        raise AtCoderLoginError(
            f"{browser_name} の通常プロファイルに AtCoder の cookie が見つかりませんでした。"
            "通常ブラウザで AtCoder にログインしてから再実行してください。"
        )

    return filtered_cookies


def load_atcoder_cookies() -> requests.cookies.RequestsCookieJar:
    """通常ブラウザのログイン済み cookie を読み込む"""
    errors = []
    for browser_name in atcoder_cookie_browsers:
        try:
            return load_atcoder_cookies_from_browser(browser_name)
        except AtCoderLoginError as e:
            errors.append(f"{browser_name}: {e}")

    error_message = "\n".join(errors)
    raise AtCoderLoginError(
        "AtCoder のログイン済み cookie を取得できませんでした。"
        "通常ブラウザで AtCoder にログインし、対象ブラウザを閉じてから再実行してください。\n"
        f"{error_message}"
    )


class AtCoderCookieSession:
    """通常ブラウザのログイン済み cookie を使って AtCoder を巡回するセッション"""

    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": default_user_agent})
        self.session.cookies.update(load_atcoder_cookies())

    def __enter__(self) -> "AtCoderCookieSession":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def get_bs(self, url: str, require_login: bool = False) -> BeautifulSoup:
        response = self.session.get(url, timeout=60)
        time.sleep(sleep_sec)
        response.raise_for_status()

        if require_login and response.url.startswith("https://atcoder.jp/login"):
            raise AtCoderLoginError(
                "AtCoder のログイン済み cookie が見つからないか、期限切れです。"
                "通常ブラウザで AtCoder にログインし、ブラウザを閉じてから再実行してください。"
            )

        return BeautifulSoup(response.text, "html.parser")

    def close(self) -> None:
        self.session.close()


def url_to_bs(url: str) -> BeautifulSoup:
    """URL から bs4.BeautifulSoup を取得"""
    with urllib.request.urlopen(url) as res:
        html_data = res.read().decode("utf-8")
    time.sleep(sleep_sec)
    return BeautifulSoup(html_data, "html.parser")


def time_text_to_datetime(time_text: str) -> datetime.datetime:
    """AtCoder の time 要素の文字列を datetime に変換"""
    match = re.search(
        r"(\d{4}-\d{2}-\d{2}).*?(\d{2}:\d{2})(?::(\d{2}))?(?:([+-]\d{4}))?", time_text
    )
    if match is None:
        raise ValueError(f"日時を解釈できませんでした: {time_text}")

    date_part = match.group(1)
    hour_minute = match.group(2)
    second = match.group(3)
    timezone = match.group(4)

    if second is None:
        second = "00"

    if timezone is None:
        return datetime.datetime.strptime(
            f"{date_part} {hour_minute}:{second}", "%Y-%m-%d %H:%M:%S"
        )

    return datetime.datetime.strptime(
        f"{date_part} {hour_minute}:{second}{timezone}", "%Y-%m-%d %H:%M:%S%z"
    ).replace(tzinfo=None)


def url_to_bs_login(
    password: str, url: str, browser_session: Optional[AtCoderCookieSession] = None
) -> BeautifulSoup:
    """AtCoder のログインが必要な URL から、通常ブラウザの cookie を使って bs4.BeautifulSoup を取得"""
    if browser_session is None:
        with AtCoderCookieSession() as new_browser_session:
            return new_browser_session.get_bs(url, require_login=True)

    return browser_session.get_bs(url, require_login=True)


def get_contest_names_and_start_times(
    browser_session: Optional[AtCoderCookieSession] = None,
) -> list[tuple[str, datetime.datetime]]:
    """「過去のコンテスト」の各ページから、14 日以内に開始された ABC, ARC, AGC, AWC の一覧を取得"""
    now_time = datetime.datetime.now()
    contest_name_to_start_time: dict[str, datetime.datetime] = {}

    for contest_archive_url in contest_archive_urls:
        if browser_session is None:
            bs = url_to_bs(contest_archive_url)
        else:
            bs = browser_session.get_bs(contest_archive_url)

        body_data = (
            bs.find("div", {"class": "table-responsive"})
            .find(
                "table",
                {
                    "class": "table table-default table-striped table-hover table-condensed table-bordered small"
                },
            )
            .find("tbody")
        )
        contest_blocks = body_data.find_all("tr")
        for block in contest_blocks:
            contest_name = (
                block.find_all("td")[1].find("a", href=True)["href"].split("/")[-1]
            )
            start_time = time_text_to_datetime(block.find("time").text)
            if start_time >= now_time - datetime.timedelta(
                days=14
            ) and target_contest_name_pattern.fullmatch(contest_name):
                contest_name_to_start_time[contest_name] = start_time

    contest_names_and_times = sorted(
        contest_name_to_start_time.items(),
        key=lambda contest_data: contest_data[1],
        reverse=True,
    )
    return contest_names_and_times


def get_task_names(
    contest_name: str, browser_session: Optional[AtCoderCookieSession] = None
) -> list[str]:
    """コンテスト名から問題名の一覧を取得"""
    task_names = []

    if browser_session is None:
        bs = url_to_bs(f"https://atcoder.jp/contests/{contest_name}/tasks")
    else:
        bs = browser_session.get_bs(f"https://atcoder.jp/contests/{contest_name}/tasks")

    body_data = (
        bs.find("div", {"class": "panel panel-default table-responsive"})
        .find("table", {"class": "table table-bordered table-striped"})
        .find("tbody")
    )
    task_blocks = body_data.find_all("tr")
    for block in task_blocks:
        task_name = block.find_all("td")[1].find("a", href=True)["href"].split("/")[-1]
        task_names.append(task_name)

    return task_names


def get_testcase_names(
    password: str,
    contest_name: str,
    task_name: str,
    start_time: Optional[datetime.datetime],
    browser_session: Optional[AtCoderCookieSession] = None,
) -> list[str]:
    """
    コンテスト名と問題名からテストケースを取得
    start_time が指定されたなら start_time 以降の最初の提出、そうでないなら最新の提出を見る
    password は後方互換性のため受け取るが、cookie 認証では使用しない
    """

    if browser_session is None:
        with AtCoderCookieSession() as new_browser_session:
            return get_testcase_names(
                password=password,
                contest_name=contest_name,
                task_name=task_name,
                start_time=start_time,
                browser_session=new_browser_session,
            )

    if start_time is None:
        url = (
            f"https://atcoder.jp/contests/{contest_name}/submissions"
            f"?desc=true&f.LanguageName=&f.Status=&f.Task={task_name}&f.User=&orderBy=created&page=1"
        )  # 提出日時の降順
    else:
        url = (
            f"https://atcoder.jp/contests/{contest_name}/submissions"
            f"?f.LanguageName=&f.Status=&f.Task={task_name}&f.User=&orderBy=created&page=1"
        )  # 提出日時の昇順

    max_retries = 5  # 取得を最大 5 回試す

    for t in range(max_retries):
        try:
            bs = url_to_bs_login(password, url, browser_session=browser_session)
            body_data = (
                bs.find("div", {"class": "table-responsive"})
                .find(
                    "table",
                    {"class": "table table-bordered table-striped small th-center"},
                )
                .find("tbody")
            )
            print(f"{task_name} succeeded (time: {t})")
            break
        except AttributeError as e:
            print(f"{task_name} failed (time: {t})")
            print(f"reason: {e}")
            time.sleep(sleep_sec)
    else:
        raise MaxRetriesExceededError()

    submission_blocks = body_data.find_all("tr")
    target_id = ""
    for block in submission_blocks:
        submit_time = time_text_to_datetime(block.find("time").text)
        submission_id = (
            block.find_all("td")[-1].find("a", href=True)["href"].split("/")[-1]
        )
        status = block.find_all("td")[
            6
        ].text  # 「AC」などのジャッジ結果。ジャッジ途中だと「15/20 TLE」とかになる。
        if (start_time is None or submit_time >= start_time) and status in [
            "AC",
            "WA",
            "TLE",
            "MLE",
            "RE",
        ]:  # CE の提出はテストケースが見られないので除外。他にも見られないものがありそうなので、安全のためよく出るものだけを指定。
            target_id = submission_id
            break
    testcases: list[str] = []
    if target_id != "":
        print("target_id:", target_id)
        testcases = id_to_cases(
            contest_name, target_id, browser_session=browser_session
        )
    return testcases


def id_to_cases(
    contest_name: str,
    submission_id: str,
    browser_session: Optional[AtCoderCookieSession] = None,
) -> list[str]:
    """提出 ID からテストケース一覧を取得"""
    testcases: list[str] = []

    if browser_session is None:
        bs = url_to_bs(
            f"https://atcoder.jp/contests/{contest_name}/submissions/{submission_id}"
        )
    else:
        bs = browser_session.get_bs(
            f"https://atcoder.jp/contests/{contest_name}/submissions/{submission_id}",
            require_login=True,
        )

    body_data = bs.find_all("div", {"class": "panel panel-default"})[3].find(
        "table", {"class": "table table-bordered table-striped th-center"}
    )

    body_data = body_data.find("tbody")
    testcase_blocks = body_data.find_all("tr")
    for block in testcase_blocks:
        testcase = block.find_all("td")[0].text
        testcases.append(testcase)

    return testcases


def get_and_update_added_cases(
    password: str, keep_testcases_txt: bool = False
) -> list[tuple[str, str, list[str]]]:
    """
    14 日以内に開始された ABC, ARC, AGC, AWC の各問題について、
    前回確認時点 (無い場合、コンテスト開始直後時点) から新たに追加されたテストケース一覧を取得し、
    testcases.json を更新 (keep_testcases_txt = True (デバッグ用) の場合は更新しない)
    password は後方互換性のため受け取るが、cookie 認証では使用しない
    """
    all_added_cases = []
    exist_data = load_testcases_data()

    with AtCoderCookieSession() as browser_session:
        contest_names_and_times = get_contest_names_and_start_times(
            browser_session=browser_session
        )
        new_data: dict[str, dict[str, list[str]]] = {}

        print("確認するコンテストと開始時刻の一覧", contest_names_and_times)
        for contest_name, start_time in contest_names_and_times:
            print(contest_name, start_time)
            task_names = get_task_names(contest_name, browser_session=browser_session)
            print("task_names:", task_names)

            for task_name in task_names:
                print(task_name, "start")
                if contest_name in exist_data and task_name in exist_data[contest_name]:
                    testcases_before = exist_data[contest_name][task_name]
                else:
                    testcases_before = get_testcase_names(
                        password,
                        contest_name,
                        task_name,
                        start_time,
                        browser_session=browser_session,
                    )
                testcases_after = get_testcase_names(
                    password,
                    contest_name,
                    task_name,
                    None,
                    browser_session=browser_session,
                )

                testcases_only_before = set(testcases_before) - set(testcases_after)
                testcases_only_after = set(testcases_after) - set(testcases_before)

                print("testcases_only_before:", testcases_only_before)
                print("testcases_only_after:", testcases_only_after)
                assert testcases_before == set() or testcases_only_before == set()

                if testcases_only_after != set():
                    added_cases = sorted(list(testcases_only_after))
                    all_added_cases.append((contest_name, task_name, added_cases))

                if contest_name not in new_data:
                    new_data[contest_name] = {}
                new_data[contest_name][task_name] = testcases_after

    if not keep_testcases_txt:
        print("update testcases.json")
        save_testcases_data(new_data)

    return all_added_cases


# ツイートをしない・testcases.json を更新しない手動テスト実行
if __name__ == "__main__":
    print("通常ブラウザの AtCoder ログイン済み cookie を使って確認します。")
    all_added_cases = get_and_update_added_cases("", keep_testcases_txt=True)
    print(all_added_cases)
